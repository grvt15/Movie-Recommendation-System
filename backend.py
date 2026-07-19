"""
FastAPI backend for the Streamlit Movie Recommender.

Two data sources are combined:
  1. Local TF-IDF artifacts (built in movies.ipynb from movies_metadata.csv):
       dataframe.pkl     - pandas DataFrame with columns:
                            ['title','genres','overview','tagline',
                             'vote_average','vote_count','popularity','tags']
       indices.pkl       - pd.Series mapping title -> row index in `dataframe`
                            (duplicates dropped, first occurrence kept)
       tfidf.pkl         - fitted TfidfVectorizer
       tfidf_matrix.pkl  - TF-IDF matrix over dataframe['tags']
     These have NO tmdb id, so they're used purely for the "similar titles"
     ranking (via rapidfuzz fuzzy title match + cosine similarity), exactly
     as in movies.ipynb.
  2. TMDB API (https://developer.themoviedb.org/docs) for everything that
     needs a tmdb_id / poster / backdrop / genre metadata: search, the home
     feed, movie details, genre-based recommendations, and resolving a
     poster/tmdb_id for each locally-recommended title.

Environment variables:
  TMDB_API_KEY   (required) - your TMDB v3 API key
  DATA_DIR       (optional) - folder containing the four .pkl files
                               (defaults to the current directory)

Run locally:
  uvicorn backend:app --reload --port 8000

Endpoints:
  GET /health
  GET /tmdb/search?query=...
  GET /home?category=trending|popular|top_rated|now_playing|upcoming&limit=24
  GET /movie/id/{tmdb_id}
  GET /movie/search?query=...&tfidf_top_n=12&genre_limit=12
  GET /recommend/genre?tmdb_id=...&limit=18
"""

import os
import time
import pickle
import logging
from typing import Optional

import requests
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from rapidfuzz import process
from requests.adapters import HTTPAdapter
from sklearn.metrics.pairwise import cosine_similarity
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("movie-backend")

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_W500 = "https://image.tmdb.org/t/p/w500"
TMDB_IMG_ORIGINAL = "https://image.tmdb.org/t/p/original"

# Some networks (antivirus HTTPS scanning, flaky wifi, corporate proxies) drop
# outbound connections mid-request with a plain ConnectionResetError. Retry
# transient failures a few times with backoff before surfacing a 502, instead
# of failing on the first hiccup.
_tmdb_session = requests.Session()
_retry_strategy = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
_tmdb_session.mount("https://", HTTPAdapter(max_retries=_retry_strategy))
_tmdb_session.mount("http://", HTTPAdapter(max_retries=_retry_strategy))

DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))

if not TMDB_API_KEY:
    logger.warning(
        "TMDB_API_KEY is not set. Set it as an environment variable before "
        "starting the server, e.g. `export TMDB_API_KEY=your_key_here`."
    )

app = FastAPI(title="Movie Recommender API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Load local TF-IDF artifacts at startup
# ---------------------------------------------------------------------------
dataframe: Optional[pd.DataFrame] = None
indices: Optional[pd.Series] = None
tfidf = None
tfidf_matrix = None


def _load_pickle(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "rb") as f:
        return pickle.load(f)


@app.on_event("startup")
def load_artifacts():
    global dataframe, indices, tfidf, tfidf_matrix
    try:
        dataframe = pd.read_pickle(os.path.join(DATA_DIR, "dataframe.pkl"))
        indices = _load_pickle("indices.pkl")
        tfidf = _load_pickle("tfidf.pkl")
        tfidf_matrix = _load_pickle("tfidf_matrix.pkl")
        logger.info("Loaded TF-IDF artifacts: %d movies in local dataset.", len(dataframe))
    except FileNotFoundError as e:
        logger.error(
            "Could not load local TF-IDF artifacts (%s). "
            "Place dataframe.pkl, indices.pkl, tfidf.pkl, tfidf_matrix.pkl "
            "in DATA_DIR (currently '%s'). TF-IDF recommendations will be "
            "unavailable until this is fixed.",
            e,
            DATA_DIR,
        )


# ---------------------------------------------------------------------------
# Simple in-memory TTL cache to reduce repeated TMDB calls
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, object]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def cache_get(key: str):
    entry = _cache.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        _cache.pop(key, None)
        return None
    return value


def cache_set(key: str, value, ttl: int = CACHE_TTL_SECONDS):
    _cache[key] = (time.time() + ttl, value)


# ---------------------------------------------------------------------------
# TMDB helpers
# ---------------------------------------------------------------------------
def tmdb_get(path: str, params: Optional[dict] = None):
    if not TMDB_API_KEY:
        raise HTTPException(status_code=500, detail="TMDB_API_KEY not configured on server")

    params = dict(params or {})
    params["api_key"] = TMDB_API_KEY

    cache_key = f"{path}::{sorted(params.items())}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = _tmdb_session.get(f"{TMDB_BASE}{path}", params=params, timeout=15)
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=(
                f"TMDB request failed after retries: {e}. "
                "This usually means a network/firewall/antivirus issue on this "
                "machine rather than TMDB itself — see the troubleshooting steps."
            ),
        )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=f"TMDB error: {resp.text[:300]}")

    data = resp.json()
    cache_set(cache_key, data)
    return data


def poster_url(path: Optional[str]) -> Optional[str]:
    return f"{TMDB_IMG_W500}{path}" if path else None


def backdrop_url(path: Optional[str]) -> Optional[str]:
    return f"{TMDB_IMG_ORIGINAL}{path}" if path else None


def movie_to_card(m: dict) -> dict:
    return {
        "tmdb_id": m.get("id"),
        "title": m.get("title") or m.get("name") or "Untitled",
        "poster_url": poster_url(m.get("poster_path")),
        "release_date": m.get("release_date", ""),
        "vote_average": m.get("vote_average"),
    }


CATEGORY_ENDPOINTS = {
    "trending": "/trending/movie/week",
    "popular": "/movie/popular",
    "top_rated": "/movie/top_rated",
    "now_playing": "/movie/now_playing",
    "upcoming": "/movie/upcoming",
}


def _lookup_tmdb_card_by_title(title: str) -> Optional[dict]:
    """Resolve a bare title (from the local dataset) to a TMDB card with poster."""
    try:
        data = tmdb_get("/search/movie", {"query": title, "include_adult": "false"})
    except HTTPException:
        return None
    results = data.get("results") or []
    if not results:
        return None
    return movie_to_card(results[0])


# ---------------------------------------------------------------------------
# Local TF-IDF recommendation (mirrors movies.ipynb's recommend())
# ---------------------------------------------------------------------------
def local_tfidf_recommend(title: str, n: int = 10) -> list[str]:
    if dataframe is None or indices is None or tfidf_matrix is None:
        raise HTTPException(
            status_code=503,
            detail="Local TF-IDF artifacts not loaded on the server (see startup logs).",
        )

    match = process.extractOne(title, indices.index)
    if match is None or match[1] < 60:
        return []

    movie_title = match[0]
    idx = indices[movie_title]

    # Handle duplicate titles (indices[...] could return a Series)
    if isinstance(idx, pd.Series):
        idx = idx.iloc[0]

    sim_scores = cosine_similarity(tfidf_matrix[idx], tfidf_matrix).flatten()
    similar_idx = sim_scores.argsort()[::-1][1 : n + 1]

    return dataframe.iloc[similar_idx]["title"].tolist()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "tmdb_key_configured": bool(TMDB_API_KEY),
        "local_dataset_loaded": dataframe is not None,
        "local_dataset_size": None if dataframe is None else len(dataframe),
    }


@app.get("/tmdb/search")
def tmdb_search(query: str = Query(..., min_length=1)):
    """Raw TMDB passthrough shape: {"results": [...]}"""
    data = tmdb_get("/search/movie", {"query": query, "include_adult": "false"})
    return data


@app.get("/home")
def home_feed(
    category: str = Query("trending"),
    limit: int = Query(24, ge=1, le=100),
):
    endpoint = CATEGORY_ENDPOINTS.get(category)
    if not endpoint:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown category '{category}'. Valid options: {list(CATEGORY_ENDPOINTS)}",
        )

    data = tmdb_get(endpoint, {"language": "en-US", "page": 1})
    results = data.get("results", [])[:limit]
    return [movie_to_card(m) for m in results]


@app.get("/movie/id/{tmdb_id}")
def movie_details(tmdb_id: int):
    data = tmdb_get(f"/movie/{tmdb_id}", {"language": "en-US"})
    return {
        "tmdb_id": data.get("id"),
        "title": data.get("title"),
        "overview": data.get("overview"),
        "release_date": data.get("release_date"),
        "genres": data.get("genres", []),
        "poster_url": poster_url(data.get("poster_path")),
        "backdrop_url": backdrop_url(data.get("backdrop_path")),
        "runtime": data.get("runtime"),
        "vote_average": data.get("vote_average"),
    }


def _first_search_match(query: str) -> Optional[dict]:
    data = tmdb_get("/search/movie", {"query": query, "include_adult": "false"})
    results = data.get("results", [])
    return results[0] if results else None


def _genre_recommendations(base_movie: dict, limit: int) -> list[dict]:
    genre_ids = [g["id"] for g in base_movie.get("genres", [])][:3]
    if not genre_ids:
        return []

    discover = tmdb_get(
        "/discover/movie",
        {
            "with_genres": ",".join(str(g) for g in genre_ids),
            "sort_by": "vote_average.desc",
            "vote_count.gte": 100,
            "page": 1,
        },
    )
    candidates = [m for m in discover.get("results", []) if m.get("id") != base_movie.get("id")]
    return [movie_to_card(m) for m in candidates[:limit]]


@app.get("/movie/search")
def movie_search_bundle(
    query: str = Query(...),
    tfidf_top_n: int = Query(12, ge=1, le=50),
    genre_limit: int = Query(12, ge=1, le=50),
):
    """
    Bundle used by the movie details page:
      - tfidf_recommendations: ranked via the LOCAL TF-IDF dataset
        (rapidfuzz title match + cosine similarity), then each title is
        resolved against TMDB to attach a tmdb_id/poster for display.
      - genre_recommendations: TMDB discover, filtered by the searched
        movie's genres.
    """
    # Local TF-IDF ranking, independent of whether TMDB has this exact title
    similar_titles = local_tfidf_recommend(query, n=tfidf_top_n)

    tfidf_recs = []
    for t in similar_titles:
        card = _lookup_tmdb_card_by_title(t)
        if card and card.get("tmdb_id"):
            tfidf_recs.append({"tmdb": card})

    # Genre recommendations still need a TMDB match for genre ids
    match = _first_search_match(query)
    genre_recs: list[dict] = []
    base_movie_out = None
    if match:
        base_movie = tmdb_get(f"/movie/{match['id']}", {"language": "en-US"})
        base_movie_out = {"tmdb_id": base_movie.get("id"), "title": base_movie.get("title")}
        genre_recs = _genre_recommendations(base_movie, genre_limit)

    if not similar_titles and not match:
        raise HTTPException(status_code=404, detail=f"No movie found for query '{query}'")

    return {
        "base_movie": base_movie_out,
        "tfidf_recommendations": tfidf_recs,
        "genre_recommendations": genre_recs,
    }


@app.get("/recommend/genre")
def recommend_genre(tmdb_id: int, limit: int = Query(18, ge=1, le=50)):
    """Genre-only recommendations — used by the frontend as a fallback."""
    base_movie = tmdb_get(f"/movie/{tmdb_id}", {"language": "en-US"})
    return _genre_recommendations(base_movie, limit)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)