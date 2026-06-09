"""insta_trend — analyze and rank trending hashtags from Instagram-style posts."""

from insta_trend.trends import Post, TrendScore, extract_hashtags, rank_trends

__all__ = ["Post", "TrendScore", "extract_hashtags", "rank_trends"]
__version__ = "0.1.0"
