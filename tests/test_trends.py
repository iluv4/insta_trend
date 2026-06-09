import pytest

from insta_trend import Post, extract_hashtags, rank_trends


def test_extract_hashtags_lowercases_and_strips_hash():
    assert extract_hashtags("Morning #Coffee and #coffee #Sunrise") == [
        "coffee",
        "coffee",
        "sunrise",
    ]


def test_extract_hashtags_empty_when_none_present():
    assert extract_hashtags("no tags here") == []


def test_rank_trends_orders_by_frequency():
    posts = [
        Post("#sunset vibes"),
        Post("another #sunset"),
        Post("just #coffee"),
    ]
    ranked = rank_trends(posts)
    assert [t.hashtag for t in ranked] == ["sunset", "coffee"]
    assert ranked[0].count == 2


def test_rank_trends_uses_likes_as_tiebreaker():
    posts = [
        Post("#a", likes=10),
        Post("#b", likes=500),
    ]
    ranked = rank_trends(posts)
    # Equal counts (1 each); #b wins on engagement.
    assert [t.hashtag for t in ranked] == ["b", "a"]


def test_rank_trends_counts_a_tag_once_per_post():
    posts = [Post("#loop #loop #loop")]
    ranked = rank_trends(posts)
    assert ranked[0].count == 1


def test_rank_trends_breaks_exact_ties_alphabetically():
    posts = [Post("#zeta"), Post("#alpha")]
    ranked = rank_trends(posts)
    assert [t.hashtag for t in ranked] == ["alpha", "zeta"]


def test_rank_trends_rejects_negative_like_weight():
    with pytest.raises(ValueError):
        rank_trends([Post("#x")], like_weight=-1)
