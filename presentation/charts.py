"""시계열 분석 + 차트 렌더링 (실데이터: 네이버 데이터랩).

모든 그림은 ``presentation/assets/`` 에 PNG로 저장되고 슬라이드 빌더가
임베드합니다. 차트 한글은 나눔고딕(fonts-nanum)으로 렌더링합니다.

분석 기법 (CS 시계열 수업 범위)
  * 이동평균 평활화 (rolling mean)
  * 가법 분해: 관측 = 추세 + 계절 + 잔차
  * 정상성: 원계열 vs 1차 차분, 롤링 평균/분산
  * 자기상관함수(ACF)와 백색잡음 검정 밴드
  * 선형추세 + 요일 더미 계절성의 14일 외삽 예측
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from naver_data import load_panel, wide_ratio  # noqa: E402

ASSETS = Path(__file__).resolve().parent / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

# ---- 한글 폰트 ------------------------------------------------------------ #
for cand in ("NanumGothic", "NanumSquareRound", "WenQuanYi Zen Hei"):
    if any(f.name == cand for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False

PALETTE = {
    "러닝": "#405DE6",
    "캠핑": "#2E8B57",
    "등산": "#E1306C",
    "카페": "#8a5a44",
    "국내여행": "#F77737",
    "다이어트": "#833AB4",
    "피크닉": "#F5A623",
    "클라이밍": "#16A0A0",
    "빵지순례": "#C13584",
}
GRID = "#E6E6E6"
INK = "#222222"

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "axes.edgecolor": "#CCCCCC",
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "font.size": 11,
    }
)

FIGSIZE = (10.2, 5.2)
FOCUS = "등산"  # 분석 포커스 태그 (6월 현재 모멘텀 1위)


def _save(fig: plt.Figure, name: str) -> Path:
    path = ASSETS / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _style_dates(ax) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m월"))
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


# --------------------------------------------------------------------------- #
# 1 — 원시 시계열 (전체 태그)
# --------------------------------------------------------------------------- #
def chart_overview(wide: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tag in wide.columns:
        ax.plot(wide.index, wide[tag], color=PALETTE[tag], lw=1.4, label=f"#{tag}")
    ax.set_title("일별 검색 관심도 — 2026.01 ~ 06 (네이버 데이터랩, 원계열)", fontweight="bold")
    ax.set_ylabel("관심도 (요청 내 상대값)")
    ax.legend(ncol=3, frameon=False, fontsize=9, loc="upper right")
    _style_dates(ax)
    return _save(fig, "01_overview.png")


# --------------------------------------------------------------------------- #
# 2 — 이동평균 평활화 (포커스 태그)
# --------------------------------------------------------------------------- #
def chart_moving_average(wide: pd.DataFrame, tag: str = FOCUS) -> Path:
    s = wide[tag]
    ma7 = s.rolling(7, center=True).mean()
    ma28 = s.rolling(28, center=True).mean()

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(s.index, s, color="#BBBBBB", lw=1.2, label="원계열")
    ax.plot(ma7.index, ma7, color=PALETTE[tag], lw=2.6, label="7일 이동평균")
    ax.plot(ma28.index, ma28, color=INK, lw=2.0, ls="--", label="28일 이동평균")
    ax.set_title(f"#{tag} 평활화 — 이동평균으로 노이즈 제거", fontweight="bold")
    ax.set_ylabel("관심도")
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    _style_dates(ax)
    return _save(fig, "02_moving_average.png")


# --------------------------------------------------------------------------- #
# 3 — 정상성: 원계열 vs 1차 차분 + 롤링 통계
# --------------------------------------------------------------------------- #
def chart_stationarity(wide: pd.DataFrame, tag: str = FOCUS) -> Path:
    s = wide[tag]
    diff = s.diff()

    fig, axes = plt.subplots(2, 1, figsize=(10.2, 6.2), sharex=True)
    axes[0].plot(s.index, s, color=PALETTE[tag], lw=1.5, label=r"원계열 $X_t$")
    axes[0].plot(s.rolling(28).mean(), color=INK, lw=2.0, label="롤링 평균(28일)")
    axes[0].plot(s.rolling(28).std(), color="#F77737", lw=1.6, ls="--", label="롤링 표준편차(28일)")
    axes[0].set_title(f"#{tag}: 원계열은 비정상 — 평균이 시간에 따라 이동", fontweight="bold")
    axes[0].legend(frameon=False, fontsize=9, ncol=3)

    axes[1].plot(diff.index, diff, color="#888888", lw=1.0, label=r"1차 차분 $\nabla X_t = X_t - X_{t-1}$")
    axes[1].plot(diff.rolling(28).mean(), color=INK, lw=2.0, label="롤링 평균(28일)")
    axes[1].axhline(0, color="#CCCCCC", lw=0.8)
    axes[1].set_title("1차 차분 후: 평균이 0 주변에 고정 → (약)정상성 확보", fontweight="bold")
    axes[1].legend(frameon=False, fontsize=9, ncol=2)
    for ax in axes:
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    _style_dates(axes[-1])
    return _save(fig, "03_stationarity.png")


# --------------------------------------------------------------------------- #
# 4 — 자기상관함수(ACF): 원계열 vs 차분
# --------------------------------------------------------------------------- #
def _acf(x: np.ndarray, nlags: int) -> np.ndarray:
    """표본 ACF: ρ̂(k) = γ̂(k)/γ̂(0),  γ̂(k) = (1/n)Σ(xₜ−x̄)(xₜ₊ₖ−x̄)."""

    x = x - x.mean()
    n = len(x)
    denom = np.dot(x, x)
    return np.array([np.dot(x[: n - k], x[k:]) / denom for k in range(nlags + 1)])


def chart_acf(wide: pd.DataFrame, tag: str = FOCUS, nlags: int = 28) -> Path:
    s = wide[tag].dropna()
    d = s.diff().dropna()
    band = 1.96 / np.sqrt(len(s))  # 백색잡음 95% 한계

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.6))
    for ax, series, title in (
        (axes[0], s.values, "원계열 ACF — 느린 감쇠 = 추세(비정상)"),
        (axes[1], d.values, "차분 계열 ACF — lag 7 스파이크 = 주간 계절성"),
    ):
        rho = _acf(np.asarray(series, dtype=float), nlags)
        lags = np.arange(nlags + 1)
        ax.bar(lags, rho, width=0.5, color=PALETTE[tag])
        ax.axhline(0, color="#888888", lw=0.8)
        ax.axhline(band, color="#999999", lw=1.0, ls="--")
        ax.axhline(-band, color="#999999", lw=1.0, ls="--")
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlabel("시차 k (일)")
        ax.set_ylabel(r"$\hat{\rho}(k)$")
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    fig.suptitle(f"#{tag} 자기상관함수 (점선 = 백색잡음 95% 한계 ±1.96/√n)", fontweight="bold")
    return _save(fig, "04_acf.png")


# --------------------------------------------------------------------------- #
# 5 — 가법 분해 (추세 / 주간 계절성 / 잔차)
# --------------------------------------------------------------------------- #
def _decompose(s: pd.Series, period: int = 7):
    trend = s.rolling(period, center=True).mean()
    detrended = s - trend
    seasonal = detrended.groupby(s.index.weekday).transform("mean")
    residual = s - trend - seasonal
    return trend, seasonal, residual


def chart_decomposition(wide: pd.DataFrame, tag: str = FOCUS) -> Path:
    s = wide[tag]
    trend, seasonal, residual = _decompose(s)

    fig, axes = plt.subplots(4, 1, figsize=(10.2, 6.6), sharex=True)
    axes[0].plot(s.index, s, color=PALETTE[tag], lw=1.4)
    axes[0].set_ylabel(r"관측 $X_t$")
    axes[1].plot(trend.index, trend, color=INK, lw=2.0)
    axes[1].set_ylabel(r"추세 $T_t$")
    axes[2].plot(seasonal.index, seasonal, color="#F77737", lw=1.2)
    axes[2].set_ylabel(r"계절 $S_t$")
    axes[3].plot(residual.index, residual, color="#999999", lw=0.9)
    axes[3].axhline(0, color="#CCCCCC", lw=0.8)
    axes[3].set_ylabel(r"잔차 $R_t$")
    for ax in axes:
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    _style_dates(axes[-1])
    axes[0].set_title(rf"#{tag} 가법 분해:  $X_t = T_t + S_t + R_t$", fontweight="bold")
    return _save(fig, "05_decomposition.png")


# --------------------------------------------------------------------------- #
# 6 — 주간 계절성 프로파일 (요일 효과)
# --------------------------------------------------------------------------- #
def chart_weekly_profile(wide: pd.DataFrame) -> Path:
    days = ["월", "화", "수", "목", "금", "토", "일"]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for tag in wide.columns:
        s = wide[tag]
        by_wd = s.groupby(s.index.weekday).mean()
        norm = by_wd / by_wd.mean() * 100
        ax.plot(range(7), norm.values, marker="o", color=PALETTE[tag], lw=1.7, label=f"#{tag}")
    ax.axhline(100, color="#CCCCCC", lw=1.0, ls=":")
    ax.set_xticks(range(7))
    ax.set_xticklabels(days)
    ax.set_ylabel("요일 평균 / 전체 평균 (%)")
    ax.set_title("주간 계절성 — 태그별 요일 프로파일 (자기 평균=100)", fontweight="bold")
    ax.legend(ncol=3, frameon=False, fontsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    return _save(fig, "06_weekly_profile.png")


# --------------------------------------------------------------------------- #
# 7 — 모멘텀: 연초=100 지수화 (7일 MA 기반)
# --------------------------------------------------------------------------- #
def chart_growth(wide: pd.DataFrame) -> dict[str, float]:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    growth: dict[str, float] = {}
    for tag in wide.columns:
        ma = wide[tag].rolling(7, center=True).mean().dropna()
        indexed = ma / ma.iloc[0] * 100
        ax.plot(indexed.index, indexed, color=PALETTE[tag], lw=1.9, label=f"#{tag}")
        growth[tag] = float(indexed.iloc[-1] - 100)
    ax.axhline(100, color="#CCCCCC", lw=1.0, ls=":")
    ax.set_ylabel("지수 (1월 첫 주 = 100)")
    ax.set_title("성장 모멘텀 — 연초 대비 상대 성장 (7일 MA 지수화)", fontweight="bold")
    ax.legend(ncol=3, frameon=False, fontsize=9, loc="upper left")
    _style_dates(ax)
    _save(fig, "07_growth.png")
    return growth


# --------------------------------------------------------------------------- #
# 8 — 예측: 선형추세 + 요일 계절성, +14일 외삽
# --------------------------------------------------------------------------- #
def _fit_forecast(s: pd.Series, horizon: int = 14, fit_window: int = 56):
    """최근 ``fit_window`` 일에 적합 — 계절 전환(봄→여름)을 반영."""

    s = s.dropna().iloc[-fit_window:]
    t = np.arange(len(s))
    coef = np.polyfit(t, s.values, 1)  # 최소제곱 선형추세
    trend_fit = np.polyval(coef, t)
    detrended = s.values - trend_fit
    weekday = s.index.weekday.to_numpy()
    seasonal_by_wd = pd.Series(detrended).groupby(weekday).mean()

    future_t = np.arange(len(s), len(s) + horizon)
    future_idx = pd.date_range(s.index[-1] + pd.Timedelta(days=1), periods=horizon)
    future_wd = future_idx.weekday.to_numpy()
    future = np.polyval(coef, future_t) + seasonal_by_wd.reindex(future_wd).to_numpy()

    resid_std = float(np.std(detrended - seasonal_by_wd.reindex(weekday).to_numpy()))
    return future_idx, np.clip(future, 0, None), resid_std, float(coef[0])


def chart_forecast(wide: pd.DataFrame, tag: str = FOCUS, horizon: int = 14) -> float:
    s = wide[tag]
    fidx, fvals, resid_std, slope = _fit_forecast(s, horizon)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(s.index, s, color="#BBBBBB", lw=1.2, label="관측")
    ax.plot(s.rolling(7, center=True).mean(), color=PALETTE[tag], lw=2.2, label="7일 MA")
    ax.plot(fidx, fvals, color=INK, lw=2.4, ls="--", label="예측 (+14일)")
    ax.fill_between(fidx, fvals - 1.96 * resid_std, fvals + 1.96 * resid_std,
                    color=PALETTE[tag], alpha=0.15, label="95% 예측구간")
    ax.set_ylabel("관심도")
    ax.set_title(f"#{tag} 14일 예측 — 선형추세 + 요일 계절성 (최근 8주 적합)", fontweight="bold")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    _style_dates(ax)
    _save(fig, "08_forecast.png")
    return slope


def render_all() -> dict:
    """모든 차트를 렌더링하고 슬라이드 내러티브용 수치를 반환."""

    panel = load_panel()
    wide = wide_ratio(panel)

    chart_overview(wide)
    chart_moving_average(wide)
    chart_stationarity(wide)
    chart_acf(wide)
    chart_decomposition(wide)
    chart_weekly_profile(wide)
    growth = chart_growth(wide)
    slope = chart_forecast(wide)

    # 연초(첫 2주) 대비 최근 2주 성장률
    first2 = wide.iloc[:14].mean()
    last2 = wide.iloc[-14:].mean()
    growth_ytd = ((last2 - first2) / first2 * 100).sort_values(ascending=False)
    # 최근 30일 vs 직전 30일 모멘텀 (지금 무엇이 뜨는가)
    mom_30 = ((wide.iloc[-30:].mean() - wide.iloc[-60:-30].mean())
              / wide.iloc[-60:-30].mean() * 100).sort_values(ascending=False)

    return {
        "n_days": len(wide),
        "n_tags": wide.shape[1],
        "date_start": wide.index.min().date().isoformat(),
        "date_end": wide.index.max().date().isoformat(),
        "growth_ytd": growth_ytd,
        "mom_30": mom_30,
        "focus": FOCUS,
        "focus_slope": slope,
    }


if __name__ == "__main__":
    stats = render_all()
    print("charts ->", ASSETS)
    print("\n연초 대비 성장률(%):")
    print(stats["growth_ytd"].round(1).to_string())
    print("\n최근 30일 모멘텀(%):")
    print(stats["mom_30"].round(1).to_string())
    print(f"\n#{stats['focus']} 최근 8주 추세 기울기: {stats['focus_slope']:+.2f}/일")
