"""가상 인스타그램 계정의 일별 '도달(reach)' 시뮬레이션.

문제 정의에서 던진 질문 — *"우리 계정은 어떻게 될까?"* — 에 직접 답하기
위한 합성 데이터입니다. 실데이터(네이버 데이터랩)와 달리, 계정 인사이트는
공개 API가 없으므로 **교육용 시뮬레이션**임을 명확히 합니다.

시계열을 구성하는 성분을 일부러 모두 심어 두어, 분해(decomposition)가
각 성분을 어떻게 되찾는지 보여줍니다::

    reach(t) = 기저 + 추세(팔로워 성장)
             + 주간 계절성(주말 피크)
             + 바이럴 이벤트(릴스 1건의 스파이크와 감쇠)
             + 노이즈

시드를 고정하므로 매 실행 결과가 동일합니다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from naver_data import wide_ratio

# 실데이터와 동일한 달력 축을 사용해 발표 맥락을 맞춘다.
_IDX = wide_ratio().index

# 바이럴 릴스: 분석 구간 중반에 1건 터뜨린다.
VIRAL_DAY = 96          # 시작 후 며칠째
VIRAL_PEAK = 9000.0     # 스파이크 추가 도달
VIRAL_DECAY = 6.0       # 감쇠 시간상수(일)


def build_account(seed: int = 11) -> pd.Series:
    """가상 계정의 일별 도달 시계열(Series, 날짜 인덱스)을 반환."""

    rng = np.random.default_rng(seed)
    n = len(_IDX)
    t = np.arange(n)

    base = 3200.0
    trend = 22.0 * t                       # 팔로워 성장 → 기저 도달 우상향
    weekday = _IDX.weekday.to_numpy()
    seasonal = 0.16 * np.cos(2 * np.pi * (weekday - 6) / 7)  # 일요일 피크

    # 바이럴 스파이크: 시작일 이후 지수 감쇠
    days_since = t - VIRAL_DAY
    viral = np.where(days_since >= 0, VIRAL_PEAK * np.exp(-days_since / VIRAL_DECAY), 0.0)

    level = (base + trend) * (1 + seasonal) + viral
    noise = rng.normal(1.0, 0.06, size=n)
    reach = np.clip(np.round(level * noise), 0, None)

    return pd.Series(reach, index=_IDX, name="reach")


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    s = build_account()
    print(s.head())
    print("\n첫 주 평균:", round(s.iloc[:7].mean()))
    print("막주 평균:", round(s.iloc[-7:].mean()))
    print("바이럴 피크일 도달:", round(s.iloc[VIRAL_DAY]))
