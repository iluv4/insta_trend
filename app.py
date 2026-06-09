"""Streamlit web app for exploring trending Instagram-style hashtags.

Run locally with::

    streamlit run app.py

Users paste (or use the sample) posts, tune how much engagement matters, and
see the ranked hashtags as a table and a bar chart. The scoring itself lives in
the dependency-free :mod:`insta_trend` core; this module is only the UI layer.
"""

from __future__ import annotations

import streamlit as st

from insta_trend import Post, rank_trends

SAMPLE_POSTS = """\
#sunset over the bay, golden hour | 1200
late night #coffee and code #devlife | 340
another #sunset, this time from the rooftop | 880
#coffee tastes better outdoors | 95
weekend #hiking with friends #outdoors | 540
chasing the #sunset again #photography | 760
morning #coffee ritual #devlife | 210
#hiking the ridge trail #outdoors #photography | 430
"""


def parse_posts(raw: str) -> list[Post]:
    """Turn the text box content into :class:`Post` objects.

    Each non-empty line is one post. An optional ``| <likes>`` suffix sets the
    like count; anything that isn't a valid integer is treated as zero so a
    stray line never breaks the whole run.
    """

    posts: list[Post] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        caption, sep, likes_part = line.rpartition("|")
        if sep:
            try:
                likes = int(likes_part.strip())
            except ValueError:
                caption, likes = line, 0
        else:
            caption, likes = line, 0
        posts.append(Post(caption.strip(), likes=max(likes, 0)))
    return posts


st.set_page_config(page_title="insta_trend", page_icon="📈", layout="wide")

st.title("📈 insta_trend")
st.caption(
    "Rank trending hashtags from Instagram-style posts. "
    "Score = count + like_weight × total likes."
)

with st.sidebar:
    st.header("Settings")
    like_weight = st.slider(
        "Like weight",
        min_value=0.0,
        max_value=0.1,
        value=0.01,
        step=0.001,
        format="%.3f",
        help="How much each like contributes to a hashtag's score. "
        "0 ranks purely by frequency.",
    )
    top_n = st.number_input(
        "Show top N", min_value=1, max_value=100, value=10, step=1
    )
    st.markdown(
        "**Input format**\n\n"
        "One post per line. Add `| <likes>` at the end to include engagement, "
        "e.g.\n\n`great #sunset today | 320`"
    )

left, right = st.columns([2, 3])

with left:
    st.subheader("Posts")
    raw = st.text_area(
        "Paste posts (one per line)",
        value=SAMPLE_POSTS,
        height=320,
        label_visibility="collapsed",
    )

posts = parse_posts(raw)
search = st.sidebar.text_input(
    "Filter hashtag", help="Show only hashtags containing this text."
)

with right:
    st.subheader("Trending hashtags")

    if not posts:
        st.info("Add some posts on the left to see trends.")
    else:
        ranked = rank_trends(posts, like_weight=like_weight)
        if search:
            needle = search.lstrip("#").lower()
            ranked = [t for t in ranked if needle in t.hashtag]

        ranked = ranked[: int(top_n)]

        if not ranked:
            st.warning("No hashtags match the current filter.")
        else:
            rows = {
                "hashtag": [f"#{t.hashtag}" for t in ranked],
                "count": [t.count for t in ranked],
                "total_likes": [t.total_likes for t in ranked],
                "score": [round(t.score, 3) for t in ranked],
            }
            metric_cols = st.columns(3)
            metric_cols[0].metric("Posts analyzed", len(posts))
            metric_cols[1].metric("Unique hashtags", len({t.hashtag for t in ranked}))
            metric_cols[2].metric("Top tag", rows["hashtag"][0])

            st.bar_chart(rows, x="hashtag", y="score", horizontal=True)
            st.dataframe(rows, use_container_width=True, hide_index=True)
