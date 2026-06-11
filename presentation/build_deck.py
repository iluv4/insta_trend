"""Build the insta_trend time-series analysis PowerPoint (.pptx).

Run::

    python presentation/build_deck.py

It (re)renders the charts, then assembles ``insta_trend_timeseries.pptx`` in
this folder. The narrative is Korean; chart labels are English. Fonts are not
embedded — slides ask for Malgun Gothic, which exists on Korean PowerPoint.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from charts import render_all

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
OUT = HERE / "insta_trend_timeseries.pptx"

KO_FONT = "맑은 고딕"
EN_FONT = "Segoe UI"

# Brand palette
PINK = RGBColor(0xE1, 0x30, 0x6C)
PURPLE = RGBColor(0x83, 0x3A, 0xB4)
INK = RGBColor(0x22, 0x22, 0x22)
GREY = RGBColor(0x6B, 0x6B, 0x6B)
LIGHT = RGBColor(0xF2, 0xF2, 0xF4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# 16:9
SW, SH = Inches(13.333), Inches(7.5)


def _set_font(run, size, *, bold=False, color=INK, font=KO_FONT):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font


def _box(slide, left, top, width, height):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    return tb, tf


def _rect(slide, left, top, width, height, color):
    from pptx.enum.shapes import MSO_SHAPE

    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def _blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _footer(slide, page):
    _rect(slide, 0, SH - Inches(0.32), SW, Inches(0.32), LIGHT)
    _, tf = _box(slide, Inches(0.4), SH - Inches(0.34), Inches(8), Inches(0.3))
    r = tf.paragraphs[0].add_run()
    r.text = "insta_trend · 시계열 데이터 분석"
    _set_font(r, 9, color=GREY)
    _, tf2 = _box(slide, SW - Inches(1.2), SH - Inches(0.34), Inches(0.9), Inches(0.3))
    p = tf2.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    r2 = p.add_run()
    r2.text = str(page)
    _set_font(r2, 9, color=GREY)


# --------------------------------------------------------------------------- #
def title_slide(prs, stats):
    s = _blank(prs)
    _rect(s, 0, 0, SW, SH, WHITE)
    # accent band
    _rect(s, 0, 0, Inches(0.35), SH, PINK)
    _rect(s, Inches(0.35), 0, Inches(0.12), SH, PURPLE)

    _, tf = _box(s, Inches(1.0), Inches(2.1), Inches(11.5), Inches(2.2))
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = "인스타그램 해시태그"
    _set_font(r, 30, color=GREY)
    p2 = tf.add_paragraph()
    r2 = p2.add_run()
    r2.text = "시계열 데이터 분석"
    _set_font(r2, 54, bold=True, color=INK)

    _, tf2 = _box(s, Inches(1.0), Inches(4.4), Inches(11), Inches(1))
    r3 = tf2.paragraphs[0].add_run()
    r3.text = "12주간의 해시태그 게시량을 추세·계절성·예측 관점에서 분석합니다"
    _set_font(r3, 18, color=GREY)

    _, tf3 = _box(s, Inches(1.0), Inches(6.2), Inches(11), Inches(0.6))
    r4 = tf3.paragraphs[0].add_run()
    r4.text = f"데이터 기간 {stats['date_start']} ~ {stats['date_end']}  ·  {stats['n_tags']}개 해시태그  ·  총 {stats['n_posts']:,}건 게시"
    _set_font(r4, 13, color=PINK, bold=True)
    return s


def agenda_slide(prs, page):
    s = _blank(prs)
    header(s, "목차", "Agenda")
    items = [
        ("01", "분석 배경과 목표", "왜 정적 랭킹을 넘어 시계열로 보는가"),
        ("02", "데이터셋 구성", "일별 게시량 패널 데이터 설계"),
        ("03", "원시 시계열 관찰", "6개 해시태그의 12주 추이"),
        ("04", "이동평균 평활화", "단기 노이즈 제거와 신호 분리"),
        ("05", "시계열 분해", "추세 · 주간 계절성 · 잔차"),
        ("06", "계절성 & 모멘텀", "요일 패턴과 성장률 랭킹"),
        ("07", "예측", "추세+계절성 기반 14일 전망"),
        ("08", "인사이트 & 결론", "운영 액션 제안"),
    ]
    top = Inches(1.7)
    for i, (num, t, sub) in enumerate(items):
        row = top + Inches(0.62) * i
        _, tf = _box(s, Inches(0.9), row, Inches(0.9), Inches(0.55))
        r = tf.paragraphs[0].add_run()
        r.text = num
        _set_font(r, 18, bold=True, color=PINK)
        _, tf2 = _box(s, Inches(1.8), row, Inches(5.0), Inches(0.55))
        r2 = tf2.paragraphs[0].add_run()
        r2.text = t
        _set_font(r2, 16, bold=True, color=INK)
        _, tf3 = _box(s, Inches(6.9), row, Inches(5.8), Inches(0.55))
        r3 = tf3.paragraphs[0].add_run()
        r3.text = sub
        _set_font(r3, 13, color=GREY)
    _footer(s, page)
    return s


def header(slide, title, eyebrow=None):
    _rect(slide, 0, 0, SW, Inches(1.15), WHITE)
    _rect(slide, Inches(0.4), Inches(0.42), Inches(0.18), Inches(0.55), PINK)
    if eyebrow:
        _, tfe = _box(slide, Inches(0.75), Inches(0.28), Inches(11), Inches(0.35))
        re_ = tfe.paragraphs[0].add_run()
        re_.text = eyebrow.upper()
        _set_font(re_, 11, bold=True, color=PURPLE, font=EN_FONT)
    _, tf = _box(slide, Inches(0.72), Inches(0.5), Inches(11.5), Inches(0.7))
    r = tf.paragraphs[0].add_run()
    r.text = title
    _set_font(r, 28, bold=True, color=INK)


def bullets_slide(prs, page, title, eyebrow, bullets, lead=None):
    s = _blank(prs)
    header(s, title, eyebrow)
    top = Inches(1.5)
    if lead:
        _rect(s, Inches(0.75), top, Inches(11.8), Inches(0.9), LIGHT)
        _, tf = _box(s, Inches(1.0), top + Inches(0.12), Inches(11.3), Inches(0.7))
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        r = tf.paragraphs[0].add_run()
        r.text = lead
        _set_font(r, 15, bold=True, color=INK)
        top = top + Inches(1.25)
    _, tf = _box(s, Inches(0.9), top, Inches(11.6), Inches(4.5))
    for i, (head, body) in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(12)
        r = p.add_run()
        r.text = f"●  {head}"
        _set_font(r, 17, bold=True, color=PINK)
        if body:
            p2 = tf.add_paragraph()
            p2.space_after = Pt(14)
            r2 = p2.add_run()
            r2.text = f"     {body}"
            _set_font(r2, 14, color=GREY)
    _footer(s, page)
    return s


def chart_slide(prs, page, title, eyebrow, image, notes):
    s = _blank(prs)
    header(s, title, eyebrow)
    # image on the left ~ 8.3in, notes panel on right
    img = ASSETS / image
    pic_w = Inches(8.5)
    s.shapes.add_picture(str(img), Inches(0.55), Inches(1.45), width=pic_w)
    # notes panel
    panel_left = Inches(9.25)
    _rect(s, panel_left, Inches(1.45), Inches(3.55), Inches(5.4), LIGHT)
    _, tf = _box(s, panel_left + Inches(0.22), Inches(1.65), Inches(3.15), Inches(5.1))
    p0 = tf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = "읽는 법"
    _set_font(r0, 13, bold=True, color=PURPLE)
    p0.space_after = Pt(8)
    for note in notes:
        p = tf.add_paragraph()
        p.space_after = Pt(10)
        r = p.add_run()
        r.text = f"• {note}"
        _set_font(r, 12.5, color=INK)
    _footer(s, page)
    return s


def section_slide(prs, kicker, title):
    s = _blank(prs)
    _rect(s, 0, 0, SW, SH, INK)
    _rect(s, Inches(0.9), Inches(3.0), Inches(1.4), Inches(0.12), PINK)
    _, tf = _box(s, Inches(0.9), Inches(2.2), Inches(11), Inches(0.6))
    r = tf.paragraphs[0].add_run()
    r.text = kicker.upper()
    _set_font(r, 14, bold=True, color=PINK, font=EN_FONT)
    _, tf2 = _box(s, Inches(0.9), Inches(3.3), Inches(11.5), Inches(1.5))
    r2 = tf2.paragraphs[0].add_run()
    r2.text = title
    _set_font(r2, 40, bold=True, color=WHITE)
    return s


def insights_slide(prs, page, stats):
    s = _blank(prs)
    header(s, "인사이트 & 결론", "Insights")
    g = stats["growth_pct"]
    top_tag = g.index[0]
    fade_tag = g.index[-1]
    cards = [
        ("📈 급상승", f"#{top_tag}", f"첫 주 대비 +{g.iloc[0]:.0f}% — 주말 피크 + 우상향 추세", PINK),
        ("📉 쇠퇴", f"#{fade_tag}", f"{g.iloc[-1]:.0f}% — 지속 하락, 콘텐츠 재정비 필요", PURPLE),
        ("🗓 주간 패턴", "요일 효과 뚜렷", "야외 태그는 주말, #coffee/#devlife는 평일 집중", INK),
        ("🔮 예측", "+14일 전망", "추세+계절성 모델로 게시량 선제 대응 가능", GREY),
    ]
    cw, ch = Inches(5.9), Inches(2.1)
    gap = Inches(0.3)
    lefts = [Inches(0.75), Inches(0.75) + cw + gap]
    tops = [Inches(1.55), Inches(1.55) + ch + gap]
    for i, (tag, big, body, color) in enumerate(cards):
        left = lefts[i % 2]
        top = tops[i // 2]
        _rect(s, left, top, cw, ch, LIGHT)
        _rect(s, left, top, Inches(0.14), ch, color)
        _, tf = _box(s, left + Inches(0.35), top + Inches(0.2), cw - Inches(0.6), ch - Inches(0.4))
        r = tf.paragraphs[0].add_run()
        r.text = tag
        _set_font(r, 13, bold=True, color=color)
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = big
        _set_font(r2, 24, bold=True, color=INK)
        p3 = tf.add_paragraph()
        p3.space_before = Pt(4)
        r3 = p3.add_run()
        r3.text = body
        _set_font(r3, 13, color=GREY)
    _footer(s, page)
    return s


def method_slide(prs, page):
    s = _blank(prs)
    header(s, "방법론 & 재현", "Appendix")
    bullets = [
        ("데이터 생성", "value(t) = level + trend·t + seasonal(요일) + noise 구조로 시드 고정 합성 (timeseries_data.py)"),
        ("이동평균", "7일·14일 중심 이동평균으로 단기 변동 제거 (pandas rolling)"),
        ("시계열 분해", "가법 모형: 관측 = 추세 + 주간 계절성 + 잔차"),
        ("모멘텀", "7일 이동평균을 1주차=100으로 지수화해 성장률 비교"),
        ("예측", "최소제곱 선형추세 + 요일별 평균 계절성을 14일 외삽, 95% 잔차 밴드"),
        ("재현", "python presentation/build_deck.py — 차트와 .pptx를 결정론적으로 재생성"),
    ]
    _, tf = _box(s, Inches(0.9), Inches(1.6), Inches(11.6), Inches(5.0))
    for i, (head, body) in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(4)
        r = p.add_run()
        r.text = f"●  {head}"
        _set_font(r, 16, bold=True, color=PINK)
        p2 = tf.add_paragraph()
        p2.space_after = Pt(12)
        r2 = p2.add_run()
        r2.text = f"     {body}"
        _set_font(r2, 13.5, color=GREY)
    _footer(s, page)
    return s


def build():
    stats = render_all()
    prs = Presentation()
    prs.slide_width = Emu(int(SW))
    prs.slide_height = Emu(int(SH))

    title_slide(prs, stats)
    agenda_slide(prs, 1)

    g = stats["growth_pct"]
    bullets_slide(
        prs, 2, "분석 배경과 목표", "01 · Background",
        lead="정적 해시태그 랭킹은 '지금 무엇이 크다'만 말해준다. 시계열은 '어디로 가는가'를 말해준다.",
        bullets=[
            ("기존 insta_trend 코어", "게시 묶음 한 번을 점수화해 순위만 산출 — 시간 축이 없음"),
            ("시계열 관점의 가치", "추세·계절성·모멘텀을 분리해 떠오르는 태그와 식는 태그를 조기 식별"),
            ("핵심 질문", "무엇이 성장 중인가? 언제(요일) 터지는가? 다음 2주는?"),
            ("산출물", "재현 가능한 일별 패널 → 분석 차트 → 운영 액션"),
        ],
    )

    bullets_slide(
        prs, 3, "데이터셋 구성", "02 · Dataset",
        lead=f"{stats['date_start']} ~ {stats['date_end']} · {stats['n_days']}일 · {stats['n_tags']}개 태그 · 총 {stats['n_posts']:,}건",
        bullets=[
            ("형태", "tidy 패널: (날짜, 해시태그) 당 한 행 — posts, likes 컬럼"),
            ("구성 요소", "기준 수준(level) + 선형 추세 + 요일 계절성 + 곱셈 노이즈"),
            ("대상 태그", "#sunset #coffee #hiking #devlife #outdoors #photography"),
            ("재현성", "난수 시드 고정 — 매 실행마다 동일한 데이터·차트 생성"),
        ],
    )

    section_slide(prs, "Part 1", "원시 신호에서 구조를 찾다")
    chart_slide(
        prs, 4, "원시 시계열 관찰", "03 · Raw signal", "01_overview.png",
        ["6개 태그의 일별 게시량 원본", "톱니 모양 = 요일 주기성", "#hiking·#sunset은 우상향", "#devlife는 완만한 하락"],
    )
    chart_slide(
        prs, 5, "이동평균 평활화", "04 · Smoothing", "02_moving_average.png",
        ["회색 = 원본(노이즈 큼)", "굵은 선 = 7일 이동평균", "점선 = 14일 이동평균", "평활화로 추세 방향이 또렷해짐"],
    )
    chart_slide(
        prs, 6, "시계열 분해", "05 · Decomposition", "03_decomposition.png",
        ["관측 = 추세 + 주간 + 잔차", "추세: 꾸준한 상승", "주간: ±20 규칙적 진동", "잔차: 패턴 없는 무작위 → 모형 적합"],
    )

    section_slide(prs, "Part 2", "계절성, 모멘텀, 그리고 예측")
    chart_slide(
        prs, 7, "주간 계절성", "06 · Seasonality", "04_weekly_profile.png",
        ["각 태그 평균=100% 기준 정규화", "야외 태그(#hiking·#outdoors)는 주말 급등", "#coffee는 월요일, #devlife는 주중", "게시·광고 타이밍 설계 근거"],
    )
    chart_slide(
        prs, 8, "성장 모멘텀", "06 · Momentum", "05_growth.png",
        [f"1주차=100 지수화", f"#{g.index[0]}: +{g.iloc[0]:.0f}% 최고 모멘텀", f"#{g.index[-1]}: {g.iloc[-1]:.0f}% 쇠퇴", "절대량이 아닌 '변화 속도'로 비교"],
    )
    chart_slide(
        prs, 9, "예측 (+14일)", "07 · Forecast", "06_forecast.png",
        ["선형추세+요일 계절성 외삽", "점선 = 향후 14일 예측", "음영 = 95% 신뢰 밴드", "재고·운영 캠페인 선제 대응"],
    )

    insights_slide(prs, 10, stats)
    method_slide(prs, 11)

    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print("Saved:", path)
