"""실데이터 로더 — 네이버 데이터랩 검색어 트렌드 (한국, 2026-01-01 ~ 2026-06-10).

``naver_datalab_panel.csv`` 는 네이버 데이터랩 검색어트렌드 API
(PlayMCP ``NaverSearch-datalab_search``)로 2026-06-11 (KST) 에 수집한
**실제 일별 검색 관심도**입니다. 각 행은 (날짜, 키워드그룹, ratio).

주의 사항
---------
* ``ratio`` 는 요청 단위로 최대값=100 으로 정규화된 **상대값**입니다.
  두 번에 나눠 수집했으므로 시리즈 *간* 절대 비교는 무효이고,
  시리즈 *내* 추세·계절성·모멘텀 분석은 유효합니다.
* 인스타그램은 해시태그 시계열 공개 API가 없으므로, 한국 사용자의
  관심도를 측정하는 프록시로 네이버 검색량을 사용합니다.

키워드 그룹 (검색어 묶음)
-------------------------
러닝(러닝+러닝크루), 캠핑(캠핑+차박), 등산(등산+등산코스),
카페(카페추천+감성카페), 국내여행(국내여행+주말여행),
다이어트(다이어트+바디프로필), 피크닉(피크닉+한강피크닉),
클라이밍(클라이밍+암벽장), 빵지순례(빵지순례+빵집투어)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CSV = Path(__file__).resolve().parent / "naver_datalab_panel.csv"

COLLECTED_AT = "2026-06-11 (KST)"
SOURCE = "네이버 데이터랩 검색어트렌드 (Naver DataLab)"

# 수집 시 키워드 오타('호캕스')로 무의미해진 시리즈 — 제외.
_DROP = {"호캕스"}


def load_panel() -> pd.DataFrame:
    """tidy 패널 반환: 컬럼 ``date``, ``hashtag``, ``ratio``."""

    panel = pd.read_csv(CSV, parse_dates=["date"])
    panel = panel[~panel["hashtag"].isin(_DROP)]
    return panel.sort_values(["hashtag", "date"]).reset_index(drop=True)


def wide_ratio(panel: pd.DataFrame | None = None) -> pd.DataFrame:
    """날짜 인덱스 × 해시태그 컬럼의 wide 프레임."""

    if panel is None:
        panel = load_panel()
    wide = panel.pivot(index="date", columns="hashtag", values="ratio")
    return wide.sort_index()


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    w = wide_ratio()
    print(w.describe().round(1).T)
    print("\n기간:", w.index.min().date(), "->", w.index.max().date(), f"({len(w)}일)")
