# insta_trend

Analyze and rank trending hashtags from Instagram-style posts.

This repository starts as a small, dependency-free **functional core** plus a
working development harness (tests + lint + a Claude Code web SessionStart
hook). A real Instagram data source can be plugged in later without changing
the scoring logic.

## Quick start

```bash
# install dev dependencies
uv pip install -e ".[dev]"   # or: pip install -e ".[dev]"

# run the harness
ruff check .
pytest
```

## Library usage

```python
from insta_trend import Post, rank_trends

posts = [
    Post("#sunset over the bay", likes=120),
    Post("late night #coffee", likes=30),
    Post("another #sunset", likes=8),
]

for trend in rank_trends(posts):
    print(trend.hashtag, trend.count, trend.total_likes)
```

`rank_trends` scores each hashtag as `count + like_weight * total_likes`, so
frequency is the primary signal and engagement is a tunable tie-breaker.

## Web app (visualization)

An interactive [Streamlit](https://streamlit.io) app (`app.py`) lets anyone
paste posts, tune the like weight, and see ranked hashtags as a table and bar
chart — no Node.js required.

```bash
pip install -e ".[app]"   # or: pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501. Input format is one post per line, with an
optional `| <likes>` suffix:

```
great #sunset today | 320
late night #coffee #devlife | 95
```

### Deploy

The app is pure Python, so the simplest free hosting is **Streamlit Community
Cloud**:

1. Push this repo to GitHub (already the case here).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **New app**, pick this repo/branch, and set the main file to `app.py`.
4. Deploy — Streamlit installs from `requirements.txt` and gives you a public
   `*.streamlit.app` URL anyone can use.

Other options (same `streamlit run app.py` entrypoint) include Hugging Face
Spaces (Streamlit SDK), Render, or any container host.

## Project layout

```
src/insta_trend/   # package source
  trends.py        # functional core: extract_hashtags, rank_trends
app.py             # Streamlit web app (visualization layer)
requirements.txt   # runtime deps for deployment
tests/             # pytest suite
```
