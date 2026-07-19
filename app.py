import os

import requests
import streamlit as st

# =============================
# CONFIG
# =============================
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="Movie Finder", page_icon="🎞️", layout="wide")

# =============================
# STYLE SYSTEM — "Film Programme"
# Palette: void black / raised surface / marquee gold / velvet crimson
# Type: Bebas Neue (display) · Fraunces (titles) · Inter (body) · IBM Plex Mono (meta)
# =============================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,500&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg: #0B0B10;
    --surface: #16151C;
    --surface-hover: #1D1C25;
    --gold: #E4B34A;
    --crimson: #B23A2E;
    --ink: #F1ECE3;
    --mute: #948FA0;
    --hairline: rgba(228, 179, 74, 0.16);
}

/* ---------- base ---------- */
.stApp {
    background: var(--bg);
    color: var(--ink);
}
[data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background: transparent;
}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
    font-family: 'Inter', sans-serif;
    color: var(--ink);
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}
::selection { background: var(--gold); color: #0B0B10; }

/* ---------- sprocket strip (signature element) ---------- */
.sprocket-strip {
    height: 14px;
    margin: 0 0 28px 0;
    background-image: radial-gradient(circle, var(--hairline) 3px, transparent 3.2px);
    background-size: 22px 14px;
    background-repeat: repeat-x;
    border-top: 1px solid var(--hairline);
    border-bottom: 1px solid var(--hairline);
}
.sprocket-strip.tight { margin: 26px 0; }

/* ---------- hero ---------- */
.hero-eyebrow {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.28em;
    color: var(--gold);
    text-transform: uppercase;
    margin-bottom: 6px;
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 4.2rem;
    line-height: 0.95;
    letter-spacing: 0.02em;
    color: var(--ink);
    margin: 0;
}
.hero-tagline {
    font-family: 'Fraunces', serif;
    font-style: italic;
    font-weight: 400;
    font-size: 1.05rem;
    color: var(--mute);
    margin-top: 10px;
}

/* ---------- eyebrow section labels ---------- */
.section-eyebrow {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--gold);
    margin: 4px 0 2px 0;
}
.section-caption {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: var(--mute);
    margin-bottom: 14px;
}

/* ---------- sidebar : ticket booth ---------- */
[data-testid="stSidebar"] {
    background: var(--surface);
    border-right: 1px solid var(--hairline);
}
[data-testid="stSidebar"] .hero-eyebrow { margin-top: 4px; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: var(--mute);
    text-transform: uppercase;
    letter-spacing: 0.12em;
}

/* ---------- inputs ---------- */
[data-testid="stTextInput"] input {
    background: var(--surface);
    border: 1px solid var(--hairline);
    color: var(--ink);
    border-radius: 2px;
    font-family: 'Inter', sans-serif;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 1px var(--gold);
}
[data-testid="stTextInput"] label, [data-testid="stSelectbox"] label, [data-testid="stSlider"] label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--mute) !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: var(--surface);
    border-color: var(--hairline);
    color: var(--ink);
    border-radius: 2px;
}
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background: var(--gold);
    border-color: var(--gold);
}

/* ---------- buttons ---------- */
[data-testid="stButton"] button {
    background: transparent;
    border: 1px solid var(--hairline);
    color: var(--ink);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    border-radius: 2px;
    padding: 0.35rem 0.9rem;
    transition: all 0.15s ease;
}
[data-testid="stButton"] button:hover {
    border-color: var(--gold);
    color: var(--gold);
    background: rgba(228, 179, 74, 0.06);
}
[data-testid="stButton"] button:active { color: var(--bg); background: var(--gold); }

/* ---------- movie cards (bordered containers) ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--surface);
    border: 1px solid var(--hairline) !important;
    border-radius: 3px;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-3px);
    border-color: var(--gold) !important;
    box-shadow: 0 10px 24px rgba(228, 179, 74, 0.14);
}
[data-testid="stImage"] img {
    border-radius: 2px 2px 0 0;
    display: block;
}
.card-title {
    font-family: 'Fraunces', serif;
    font-size: 0.92rem;
    line-height: 1.25rem;
    height: 2.5rem;
    overflow: hidden;
    color: var(--ink);
    padding: 10px 2px 2px 2px;
}
.no-poster {
    aspect-ratio: 2 / 3;
    display: flex;
    align-items: center;
    justify-content: center;
    background: repeating-linear-gradient(45deg, #1a1920, #1a1920 10px, #1c1b23 10px, #1c1b23 20px);
    color: var(--mute);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    text-align: center;
    border-radius: 2px 2px 0 0;
}

/* ---------- details page ---------- */
.detail-card {
    background: var(--surface);
    border: 1px solid var(--hairline);
    border-radius: 3px;
    padding: 20px;
}
.detail-title {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 2.1rem;
    color: var(--ink);
    margin: 0 0 10px 0;
}
.meta-row {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: var(--mute);
    margin-bottom: 4px;
}
.pill-row { margin: 14px 0 6px 0; }
.pill {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink);
    border: 1px solid var(--crimson);
    background: rgba(178, 58, 46, 0.12);
    border-radius: 20px;
    padding: 3px 12px;
    margin: 0 6px 6px 0;
}
.overview-text {
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    line-height: 1.6rem;
    color: var(--ink);
}
[data-testid="stImage"] { border-radius: 2px; overflow: hidden; }

/* ---------- alerts, kept legible on dark ---------- */
[data-testid="stAlert"] {
    background: var(--surface);
    border: 1px solid var(--hairline);
    color: var(--ink);
    font-family: 'Inter', sans-serif;
}

hr { border-color: var(--hairline) !important; }
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# STATE + ROUTING (single-file pages)
# =============================
if "view" not in st.session_state:
    st.session_state.view = "home"  # home | details
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

qp_view = st.query_params.get("view")
qp_id = st.query_params.get("id")
if qp_view in ("home", "details"):
    st.session_state.view = qp_view
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except ValueError:
        pass


def goto_home():
    st.session_state.view = "home"
    st.query_params["view"] = "home"
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()


def goto_details(tmdb_id: int):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params["view"] = "details"
    st.query_params["id"] = str(int(tmdb_id))
    st.rerun()


# =============================
# API HELPERS
# =============================
@st.cache_data(ttl=30)  # short cache for autocomplete
def api_get_json(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=35)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"


def sprocket_strip(tight: bool = False):
    cls = "sprocket-strip tight" if tight else "sprocket-strip"
    st.markdown(f"<div class='{cls}'></div>", unsafe_allow_html=True)


def section_header(eyebrow: str, caption: str | None = None):
    st.markdown(f"<div class='section-eyebrow'>{eyebrow}</div>", unsafe_allow_html=True)
    if caption:
        st.markdown(f"<div class='section-caption'>{caption}</div>", unsafe_allow_html=True)


def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.markdown(
            "<div class='section-caption'>Nothing here yet. Try a different title or category.</div>",
            unsafe_allow_html=True,
        )
        return

    rows = (len(cards) + cols - 1) // cols
    idx = 0
    for r in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break
            m = cards[idx]
            idx += 1

            tmdb_id = m.get("tmdb_id")
            title = m.get("title", "Untitled")
            poster = m.get("poster_url")

            with colset[c]:
                with st.container(border=True):
                    if poster:
                        st.image(poster, use_container_width=True)
                    else:
                        st.markdown(
                            "<div class='no-poster'>No&nbsp;Still<br/>Available</div>",
                            unsafe_allow_html=True,
                        )
                    st.markdown(f"<div class='card-title'>{title}</div>", unsafe_allow_html=True)
                    if st.button("View", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}", use_container_width=True):
                        if tmdb_id:
                            goto_details(tmdb_id)


def to_cards_from_tfidf_items(tfidf_items):
    cards = []
    for x in tfidf_items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append(
                {
                    "tmdb_id": tmdb["tmdb_id"],
                    "title": tmdb.get("title") or x.get("title") or "Untitled",
                    "poster_url": tmdb.get("poster_url"),
                }
            )
    return cards


# =============================
# Robust TMDB search parsing
# Supports BOTH API shapes:
# 1) raw TMDB: {"results":[{id,title,poster_path,...}]}
# 2) list cards: [{tmdb_id,title,poster_url,...}]
# =============================
def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    """
    Returns:
      suggestions: list[(label, tmdb_id)]
      cards: list[{tmdb_id,title,poster_url}]
    """
    keyword_l = keyword.strip().lower()

    if isinstance(data, dict) and "results" in data:
        raw = data.get("results") or []
        raw_items = []
        for m in raw:
            title = (m.get("title") or "").strip()
            tmdb_id = m.get("id")
            poster_path = m.get("poster_path")
            if not title or not tmdb_id:
                continue
            raw_items.append(
                {
                    "tmdb_id": int(tmdb_id),
                    "title": title,
                    "poster_url": f"{TMDB_IMG}{poster_path}" if poster_path else None,
                    "release_date": m.get("release_date", ""),
                }
            )

    elif isinstance(data, list):
        raw_items = []
        for m in data:
            tmdb_id = m.get("tmdb_id") or m.get("id")
            title = (m.get("title") or "").strip()
            poster_url = m.get("poster_url")
            if not title or not tmdb_id:
                continue
            raw_items.append(
                {
                    "tmdb_id": int(tmdb_id),
                    "title": title,
                    "poster_url": poster_url,
                    "release_date": m.get("release_date", ""),
                }
            )
    else:
        return [], []

    matched = [x for x in raw_items if keyword_l in x["title"].lower()]
    final_list = matched if matched else raw_items

    suggestions = []
    for x in final_list[:10]:
        year = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["tmdb_id"]))

    cards = [
        {"tmdb_id": x["tmdb_id"], "title": x["title"], "poster_url": x["poster_url"]}
        for x in final_list[:limit]
    ]
    return suggestions, cards


# =============================
# SIDEBAR — ticket booth
# =============================
with st.sidebar:
    st.markdown("<div class='hero-eyebrow'>Ticket Booth</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='hero-title' style='font-size:2rem;'>Browse</div>",
        unsafe_allow_html=True,
    )
    if st.button("All Films", use_container_width=True):
        goto_home()

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-eyebrow' style='font-size:0.65rem;'>Feed</div>", unsafe_allow_html=True)
    home_category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
        index=0,
        format_func=lambda x: x.replace("_", " ").title(),
        label_visibility="collapsed",
    )
    grid_cols = st.slider("Columns", 4, 8, 6)

# =============================
# HERO
# =============================
sprocket_strip()
st.markdown("<div class='hero-eyebrow'>Now Screening</div>", unsafe_allow_html=True)
st.markdown("<h1 class='hero-title'>MOVIE FINDER</h1>", unsafe_allow_html=True)
st.markdown(
    "<div class='hero-tagline'>Search a title, walk out with a shortlist.</div>",
    unsafe_allow_html=True,
)
sprocket_strip()

# ==========================================================
# VIEW: HOME
# ==========================================================
if st.session_state.view == "home":
    typed = st.text_input(
        "Search",
        placeholder="Search a title — avenger, batman, love...",
        label_visibility="collapsed",
    )

    if typed.strip():
        if len(typed.strip()) < 2:
            st.markdown(
                "<div class='section-caption'>Two characters gets you a result.</div>",
                unsafe_allow_html=True,
            )
        else:
            data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})

            if err or data is None:
                st.error(f"Search didn't go through: {err}")
            else:
                suggestions, cards = parse_tmdb_search_to_cards(
                    data, typed.strip(), limit=24
                )

                if suggestions:
                    labels = ["Pick a title..."] + [s[0] for s in suggestions]
                    selected = st.selectbox("Suggestions", labels, index=0, label_visibility="collapsed")

                    if selected != "Pick a title...":
                        label_to_id = {s[0]: s[1] for s in suggestions}
                        goto_details(label_to_id[selected])
                else:
                    st.markdown(
                        "<div class='section-caption'>No matches. Try a different spelling.</div>",
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
                section_header("Results")
                poster_grid(cards, cols=grid_cols, key_prefix="search_results")

        st.stop()

    section_header(home_category.replace("_", " ").title())

    home_cards, err = api_get_json(
        "/home", params={"category": home_category, "limit": 24}
    )
    if err or not home_cards:
        st.error(f"Couldn't load this feed: {err or 'Unknown error'}")
        st.stop()

    poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")

# ==========================================================
# VIEW: DETAILS
# ==========================================================
elif st.session_state.view == "details":
    tmdb_id = st.session_state.selected_tmdb_id
    if not tmdb_id:
        st.markdown(
            "<div class='section-caption'>No title selected.</div>", unsafe_allow_html=True
        )
        if st.button("Back to All Films"):
            goto_home()
        st.stop()

    a, b = st.columns([4, 1])
    with a:
        st.markdown("<div class='section-eyebrow'>Now Showing</div>", unsafe_allow_html=True)
    with b:
        if st.button("← Back", use_container_width=True):
            goto_home()

    data, err = api_get_json(f"/movie/id/{tmdb_id}")
    if err or not data:
        st.error(f"Couldn't load this title: {err or 'Unknown error'}")
        st.stop()

    left, right = st.columns([1, 2.4], gap="large")

    with left:
        if data.get("poster_url"):
            st.image(data["poster_url"], use_container_width=True)
        else:
            st.markdown("<div class='no-poster' style='border-radius:2px;'>No Still Available</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='detail-card'>", unsafe_allow_html=True)
        st.markdown(f"<h2 class='detail-title'>{data.get('title','')}</h2>", unsafe_allow_html=True)
        release = data.get("release_date") or "—"
        rating = data.get("vote_average")
        rating_str = f"{rating:.1f}/10" if isinstance(rating, (int, float)) else "—"
        st.markdown(
            f"<div class='meta-row'>RELEASED &nbsp;{release} &nbsp;·&nbsp; RATING &nbsp;{rating_str}</div>",
            unsafe_allow_html=True,
        )
        genres = data.get("genres", [])
        if genres:
            pills = "".join(f"<span class='pill'>{g['name']}</span>" for g in genres)
            st.markdown(f"<div class='pill-row'>{pills}</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='overview-text'>{data.get('overview') or 'No synopsis available.'}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if data.get("backdrop_url"):
        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
        st.image(data["backdrop_url"], use_container_width=True)

    sprocket_strip(tight=True)
    section_header("Recommendations")

    title = (data.get("title") or "").strip()
    if title:
        bundle, err2 = api_get_json(
            "/movie/search",
            params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
        )

        if not err2 and bundle:
            section_header("Similar Titles", "Ranked by how closely the plot summary matches.")
            poster_grid(
                to_cards_from_tfidf_items(bundle.get("tfidf_recommendations")),
                cols=grid_cols,
                key_prefix="details_tfidf",
            )

            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            section_header("More Like This", "Same genres, sorted by rating.")
            poster_grid(
                bundle.get("genre_recommendations", []),
                cols=grid_cols,
                key_prefix="details_genre",
            )
        else:
            section_header("More Like This", "Same genres, sorted by rating.")
            genre_only, err3 = api_get_json(
                "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
            )
            if not err3 and genre_only:
                poster_grid(
                    genre_only, cols=grid_cols, key_prefix="details_genre_fallback"
                )
            else:
                st.markdown(
                    "<div class='section-caption'>No recommendations available right now.</div>",
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            "<div class='section-caption'>No title to base recommendations on.</div>",
            unsafe_allow_html=True,
        )