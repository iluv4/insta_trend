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

## Project layout

```
src/insta_trend/   # package source
  trends.py        # functional core: extract_hashtags, rank_trends
tests/             # pytest suite
```
