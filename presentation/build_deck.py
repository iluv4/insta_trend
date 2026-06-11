"""insta_trend 시계열 분석 PPT 빌더 (실데이터판).

실행::

    python presentation/build_deck.py

네이버 데이터랩 실데이터(``naver_datalab_panel.csv``)로 차트를 다시 그리고
``insta_trend_timeseries.pptx`` 를 조립합니다.

구성: 문제 정의 → 시계열 직관(겹친 신호·추세 제거·자기상관) → 실데이터
분석 → 모델 비교 → 트렌딩 결론 + 우리 계정 시뮬레이션 + 핵심 코드.
모던·미니멀 스타일(둥근 카드·헤어라인·단일 액센트). 폰트는 임베드하지
않으며 한글 본문은 맑은 고딕을 요청합니다.
"""

from __future__ import annotations

from itertools import count
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from charts import FOCUS, render_all

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
OUT = HERE / "insta_trend_timeseries.pptx"

KO_FONT = "맑은 고딕"
EN_FONT = "Segoe UI"
CODE_FONT = "Consolas"

PINK = RGBColor(0xE1, 0x30, 0x6C)       # 단일 액센트
PURPLE = RGBColor(0x6A, 0x3D, 0xB8)     # 보조 (드물게)
INK = RGBColor(0x1A, 0x1A, 0x1E)        # 본문 제목
GREY = RGBColor(0x66, 0x66, 0x70)       # 본문 muted
FAINT = RGBColor(0x9A, 0x9A, 0xA2)      # 캡션·푸터
BORDER = RGBColor(0xE6, 0xE6, 0xEA)     # 카드 외곽선·헤어라인
LIGHT = RGBColor(0xF6, 0xF6, 0xF9)      # 패널 배경
PINK_TINT = RGBColor(0xFB, 0xE9, 0xF1)  # 액센트 8% 틴트
CODE_BG = RGBColor(0x1E, 0x1E, 0x26)
CODE_FG = RGBColor(0xE8, 0xE8, 0xEE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

SW, SH = Inches(13.333), Inches(7.5)

ASOF = "2026년 6월 11일 (KST)"


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


def _rect(slide, left, top, width, height, color, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp


def _round_rect(slide, left, top, width, height, color, line=None, radius=0.06):
    """둥근 모서리 패널 — 모던한 카드 느낌."""

    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    try:
        shp.adjustments[0] = radius
    except (IndexError, KeyError):
        pass
    return shp


def _hairline(slide, left, top, width, color=BORDER):
    _rect(slide, left, top, width, Pt(1), color)


def _blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _footer(slide, page):
    _, tf = _box(slide, Inches(0.7), SH - Inches(0.46), Inches(9), Inches(0.3))
    r = tf.paragraphs[0].add_run()
    r.text = "시계열 데이터 분석  ·  한국 해시태그 트렌드"
    _set_font(r, 9, color=FAINT)
    _, tf2 = _box(slide, SW - Inches(1.3), SH - Inches(0.46), Inches(0.9), Inches(0.3))
    p = tf2.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    r2 = p.add_run()
    r2.text = f"{page:02d}"
    _set_font(r2, 9, bold=True, color=PINK)


def header(slide, title, eyebrow=None):
    """모던 헤더 — 작은 액센트 점 + 이브로우 + 제목 + 풀폭 헤어라인."""

    if eyebrow:
        _, tfe = _box(slide, Inches(0.72), Inches(0.42), Inches(11.8), Inches(0.32))
        re_ = tfe.paragraphs[0].add_run()
        re_.text = eyebrow.upper()
        _set_font(re_, 10.5, bold=True, color=PINK, font=EN_FONT)
    _, tf = _box(slide, Inches(0.7), Inches(0.72), Inches(11.9), Inches(0.7))
    r = tf.paragraphs[0].add_run()
    r.text = title
    _set_font(r, 27, bold=True, color=INK)
    _hairline(slide, Inches(0.72), Inches(1.42), Inches(11.9))


# --------------------------------------------------------------------------- #
# 슬라이드 타입
# --------------------------------------------------------------------------- #
def title_slide(prs, stats):
    s = _blank(prs)
    _rect(s, 0, 0, SW, SH, WHITE)
    # 좌측 가는 액센트 스트라이프
    _rect(s, 0, 0, Inches(0.16), SH, PINK)

    # 이브로우 칩
    _round_rect(s, Inches(1.1), Inches(1.75), Inches(3.0), Inches(0.46), PINK_TINT, radius=0.5)
    _, tfk = _box(s, Inches(1.1), Inches(1.81), Inches(3.0), Inches(0.36))
    pk = tfk.paragraphs[0]
    pk.alignment = PP_ALIGN.CENTER
    rk = pk.add_run()
    rk.text = "TIME-SERIES ANALYSIS"
    _set_font(rk, 11, bold=True, color=PINK, font=EN_FONT)

    _, tf = _box(s, Inches(1.05), Inches(2.5), Inches(11.5), Inches(2.4))
    r = tf.paragraphs[0].add_run()
    r.text = "한국 인스타그램 해시태그"
    _set_font(r, 26, color=GREY)
    p2 = tf.add_paragraph()
    p2.space_before = Pt(4)
    r2 = p2.add_run()
    r2.text = "시계열 데이터 분석"
    _set_font(r2, 56, bold=True, color=INK)

    _, tf2 = _box(s, Inches(1.1), Inches(4.95), Inches(11.3), Inches(0.7))
    r3 = tf2.paragraphs[0].add_run()
    r3.text = "네이버 데이터랩 실데이터로 본 2026년 상반기 트렌드 — 무엇이 뜨고, 어디로 가는가"
    _set_font(r3, 17, color=GREY)

    _hairline(s, Inches(1.1), Inches(6.0), Inches(6.5))
    _, tf3 = _box(s, Inches(1.1), Inches(6.2), Inches(11.3), Inches(0.6))
    r5 = tf3.paragraphs[0].add_run()
    r5.text = (
        f"기준일 {ASOF}    분석 기간 {stats['date_start']} ~ {stats['date_end']}"
        f" ({stats['n_days']}일)    해시태그 {stats['n_tags']}개"
    )
    _set_font(r5, 12.5, bold=True, color=FAINT)
    return s


def agenda_slide(prs, page):
    s = _blank(prs)
    header(s, "목차", "Agenda")
    items = [
        ("01", "문제 정의와 데이터", "마케터의 고민 · 네이버 데이터랩 실데이터"),
        ("02", "시계열, 직관으로 이해하기", "겹친 신호 · 추세 걷어내기 · 반복 패턴 찾기"),
        ("03", "실데이터로 분석하기", "평활화 · 정상성 · 분해 · 계절성 · 예측"),
        ("04", "모델 비교", "선형 베이스라인 vs SARIMA"),
        ("05", "결론: 지금 뜨는 태그", "2026-06-11 트렌딩 태그와 활용 전략"),
        ("06", "우리 계정은 어떻게 될까", "도달 분해 · 14일 예측으로 답하기"),
        ("07", "부록: 코드 · 한계", "구현 요약과 데이터 캐비앗"),
    ]
    top = Inches(1.78)
    row_h = Inches(0.7)
    for i, (num, t, sub) in enumerate(items):
        row = top + row_h * i
        # 번호 칩
        _round_rect(s, Inches(0.85), row, Inches(0.5), Inches(0.5), PINK_TINT, radius=0.25)
        _, tf = _box(s, Inches(0.85), row + Inches(0.07), Inches(0.5), Inches(0.4))
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = num
        _set_font(r, 14, bold=True, color=PINK, font=EN_FONT)
        # 제목
        _, tf2 = _box(s, Inches(1.6), row + Inches(0.02), Inches(5.4), Inches(0.5))
        r2 = tf2.paragraphs[0].add_run()
        r2.text = t
        _set_font(r2, 16, bold=True, color=INK)
        # 부제
        _, tf3 = _box(s, Inches(7.1), row + Inches(0.05), Inches(5.7), Inches(0.5))
        r3 = tf3.paragraphs[0].add_run()
        r3.text = sub
        _set_font(r3, 12.5, color=GREY)
        if i < len(items) - 1:
            _hairline(s, Inches(1.6), row + row_h - Inches(0.1), Inches(11.0))
    _footer(s, page)
    return s


def bullets_slide(prs, page, title, eyebrow, bullets, lead=None):
    s = _blank(prs)
    header(s, title, eyebrow)
    top = Inches(1.68)
    if lead:
        lh = Inches(0.92)
        _round_rect(s, Inches(0.72), top, Inches(11.9), lh, PINK_TINT, radius=0.08)
        _rect(s, Inches(0.72), top, Inches(0.1), lh, PINK)
        _, tf = _box(s, Inches(1.05), top + Inches(0.1), Inches(11.3), lh - Inches(0.2))
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        r = tf.paragraphs[0].add_run()
        r.text = lead
        _set_font(r, 15, bold=True, color=INK)
        top = top + lh + Inches(0.28)
    _, tf = _box(s, Inches(0.85), top, Inches(11.7), Inches(4.6))
    for i, (head, body) in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(3)
        r = p.add_run()
        r.text = head
        _set_font(r, 16, bold=True, color=INK)
        if body:
            p2 = tf.add_paragraph()
            p2.space_after = Pt(15)
            r2 = p2.add_run()
            r2.text = body
            _set_font(r2, 13.5, color=GREY)
    # 좌측 액센트 점들은 텍스트 박스 정렬을 깨므로 생략 — 굵기/색 대비로 위계 표현
    _footer(s, page)
    return s


def intuition_slide(prs, page, title, eyebrow, question, analogy, cards, formula=None):
    """직관 슬라이드: 한 줄 질문 + 비유 박스 + 개념 카드 3장 + (선택) 수식 칩.

    수식 대신 생활 비유와 그림 같은 카드로 개념을 쉽게 전달한다.
    """

    s = _blank(prs)
    header(s, title, eyebrow)

    # 한 줄 핵심 질문
    _, tfq = _box(s, Inches(0.72), Inches(1.58), Inches(11.9), Inches(0.5))
    rq = tfq.paragraphs[0].add_run()
    rq.text = question
    _set_font(rq, 17, bold=True, color=INK)

    # 비유 박스
    ay, ah = Inches(2.2), Inches(0.82)
    _round_rect(s, Inches(0.72), ay, Inches(11.9), ah, PINK_TINT, radius=0.12)
    _, tfa = _box(s, Inches(1.0), ay, Inches(11.4), ah)
    tfa.vertical_anchor = MSO_ANCHOR.MIDDLE
    pa = tfa.paragraphs[0]
    r1 = pa.add_run()
    r1.text = "💡 비유   "
    _set_font(r1, 13.5, bold=True, color=PINK)
    r2 = pa.add_run()
    r2.text = analogy
    _set_font(r2, 13.5, color=INK)

    # 개념 카드 3장
    n = len(cards)
    gap = Inches(0.3)
    total = Inches(11.9)
    cw = (total - gap * (n - 1)) / n
    cy = Inches(3.35)
    ch = Inches(2.75)
    for i, (icon, term, body) in enumerate(cards):
        cx = Inches(0.72) + (cw + gap) * i
        _round_rect(s, cx, cy, cw, ch, LIGHT, line=BORDER, radius=0.07)
        _, tfi = _box(s, cx + Inches(0.28), cy + Inches(0.24), cw - Inches(0.56), Inches(0.7))
        ri = tfi.paragraphs[0].add_run()
        ri.text = icon
        _set_font(ri, 30, color=INK)
        _, tft = _box(s, cx + Inches(0.28), cy + Inches(1.02), cw - Inches(0.56), Inches(0.5))
        rt = tft.paragraphs[0].add_run()
        rt.text = term
        _set_font(rt, 15.5, bold=True, color=PINK)
        _, tfb = _box(s, cx + Inches(0.28), cy + Inches(1.5), cw - Inches(0.56), Inches(1.15))
        rb = tfb.paragraphs[0].add_run()
        rb.text = body
        _set_font(rb, 12.5, color=GREY)

    # 수식 칩 (선택) — 작게, 부담 없이
    if formula:
        fy = Inches(6.35)
        _round_rect(s, Inches(0.72), fy, Inches(11.9), Inches(0.5), INK, radius=0.3)
        _, tff = _box(s, Inches(1.0), fy, Inches(11.4), Inches(0.5))
        tff.vertical_anchor = MSO_ANCHOR.MIDDLE
        pf = tff.paragraphs[0]
        rfl = pf.add_run()
        rfl.text = "수식  "
        _set_font(rfl, 11, bold=True, color=PINK, font=EN_FONT)
        rf = pf.add_run()
        rf.text = formula
        _set_font(rf, 13, color=WHITE, font=CODE_FONT)
    _footer(s, page)
    return s


def chart_slide(prs, page, title, eyebrow, image, notes):
    s = _blank(prs)
    header(s, title, eyebrow)
    s.shapes.add_picture(str(ASSETS / image), Inches(0.5), Inches(1.7), width=Inches(8.55))
    panel_left = Inches(9.3)
    py, ph = Inches(1.7), Inches(5.15)
    _round_rect(s, panel_left, py, Inches(3.55), ph, LIGHT, line=BORDER, radius=0.05)
    # 패널 헤더
    _, tfh = _box(s, panel_left + Inches(0.28), py + Inches(0.22), Inches(3.1), Inches(0.4))
    rh = tfh.paragraphs[0].add_run()
    rh.text = "📖  읽는 법"
    _set_font(rh, 13, bold=True, color=PINK)
    _hairline(s, panel_left + Inches(0.28), py + Inches(0.72), Inches(3.0))
    _, tf = _box(s, panel_left + Inches(0.28), py + Inches(0.88), Inches(3.05), ph - Inches(1.1))
    for i, note in enumerate(notes):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(11)
        rn = p.add_run()
        rn.text = "— "
        _set_font(rn, 12.5, bold=True, color=PINK)
        r = p.add_run()
        r.text = note
        _set_font(r, 12.5, color=INK)
    _footer(s, page)
    return s


def section_slide(prs, kicker, title, big_no):
    s = _blank(prs)
    _rect(s, 0, 0, SW, SH, INK)
    # 거대한 흐린 번호 (배경 장식)
    _, tfn = _box(s, Inches(8.5), Inches(0.2), Inches(4.6), Inches(4.0))
    pn = tfn.paragraphs[0]
    pn.alignment = PP_ALIGN.RIGHT
    rn = pn.add_run()
    rn.text = big_no
    _set_font(rn, 200, bold=True, color=RGBColor(0x2B, 0x2B, 0x33), font=EN_FONT)
    # 키커 + 제목
    _, tf = _box(s, Inches(0.95), Inches(2.95), Inches(11), Inches(0.6))
    r = tf.paragraphs[0].add_run()
    r.text = kicker.upper()
    _set_font(r, 14, bold=True, color=PINK, font=EN_FONT)
    _, tf2 = _box(s, Inches(0.92), Inches(3.5), Inches(11.5), Inches(1.5))
    r2 = tf2.paragraphs[0].add_run()
    r2.text = title
    _set_font(r2, 40, bold=True, color=WHITE)
    _rect(s, Inches(0.95), Inches(5.05), Inches(1.5), Pt(3), PINK)
    return s


def cards_slide(prs, page, title, eyebrow, cards, lead=None):
    s = _blank(prs)
    header(s, title, eyebrow)
    top = Inches(1.62)
    if lead:
        _, tfl = _box(s, Inches(0.75), top, Inches(11.8), Inches(0.4))
        rl = tfl.paragraphs[0].add_run()
        rl.text = lead
        _set_font(rl, 14, bold=True, color=GREY)
        top = Inches(2.15)
    cw, ch = Inches(5.85), Inches(2.12)
    gap = Inches(0.3)
    lefts = [Inches(0.75), Inches(0.75) + cw + gap]
    tops = [top, top + ch + Inches(0.28)]
    for i, (tag, big, body, color) in enumerate(cards[:4]):
        left = lefts[i % 2]
        top_i = tops[i // 2]
        _round_rect(s, left, top_i, cw, ch, LIGHT, line=BORDER, radius=0.06)
        _rect(s, left, top_i + Inches(0.18), Inches(0.1), ch - Inches(0.36), color)
        _, tf = _box(s, left + Inches(0.38), top_i + Inches(0.2), cw - Inches(0.65), ch - Inches(0.4))
        r = tf.paragraphs[0].add_run()
        r.text = tag
        _set_font(r, 12.5, bold=True, color=color)
        p2 = tf.add_paragraph()
        p2.space_before = Pt(2)
        r2 = p2.add_run()
        r2.text = big
        _set_font(r2, 22, bold=True, color=INK)
        p3 = tf.add_paragraph()
        p3.space_before = Pt(5)
        r3 = p3.add_run()
        r3.text = body
        _set_font(r3, 12.5, color=GREY)
    _footer(s, page)
    return s


def code_slide(prs, page, title, eyebrow, blocks):
    """핵심 코드 슬라이드: (설명, 코드) 블록 목록."""

    s = _blank(prs)
    header(s, title, eyebrow)
    top = Inches(1.5)
    for desc, code in blocks:
        _, tfd = _box(s, Inches(0.8), top, Inches(11.8), Inches(0.35))
        rd = tfd.paragraphs[0].add_run()
        rd.text = f"●  {desc}"
        _set_font(rd, 13.5, bold=True, color=PINK)
        top += Inches(0.42)
        lines = code.strip("\n").split("\n")
        bh = Inches(0.28) * len(lines) + Inches(0.22)
        _rect(s, Inches(1.0), top, Inches(11.4), bh, CODE_BG)
        _, tfc = _box(s, Inches(1.25), top + Inches(0.1), Inches(11.0), bh - Inches(0.16))
        for j, line in enumerate(lines):
            p = tfc.paragraphs[0] if j == 0 else tfc.add_paragraph()
            r = p.add_run()
            r.text = line
            _set_font(r, 12, color=CODE_FG, font=CODE_FONT)
        top += bh + Inches(0.18)
    _footer(s, page)
    return s


# --------------------------------------------------------------------------- #
def build():
    stats = render_all()
    pg = count(1)
    g = stats["growth_ytd"]
    m = stats["mom_30"]

    prs = Presentation()
    prs.slide_width = Emu(int(SW))
    prs.slide_height = Emu(int(SH))

    title_slide(prs, stats)
    agenda_slide(prs, next(pg))

    bullets_slide(
        prs, next(pg), "문제 정의 — 마케터의 고민", "01 · Problem",
        lead="“다음 달에 어떤 해시태그가 떡상할까? 우리 계정 도달은 오를까, 꺾일까?” — 감으로는 답할 수 없는 질문들",
        bullets=[
            ("“어떤 태그가 떡상할까?”", "인기 순위는 '이미 큰 것'만 보여줌 — 순위에 올라온 시점은 대개 피크 직전이라 따라 들어가면 늦음"),
            ("“우리 계정은 어떻게 될까?”", "도달·팔로워 그래프가 오르는 중인지, 꺾이는 중인지, 그냥 요일 출렁임인지 눈으로는 구분 불가"),
            ("“왜 예측이 어렵나?”", "관심도 = 추세 + 계절성 + 이벤트 + 노이즈가 섞인 신호 — 분리하지 않으면 노이즈를 트렌드로 오독"),
            ("이 발표의 제안", "시계열 분해로 신호를 성분별로 나누면 '진짜 상승'·'피크 통과'·'단순 요일 효과'를 데이터로 구분할 수 있다"),
        ],
    )

    bullets_slide(
        prs, next(pg), "분석 접근", "01 · Approach",
        lead="질문: 2026년 6월 11일 현재, 한국에서 어떤 해시태그가 뜨고 있고 — 어디로 가는가?",
        bullets=[
            ("왜 시계열인가", "한 시점의 인기 순위는 '지금 큰 것'만 보여줌 — 추세·계절성·모멘텀을 분리해야 '뜨는 것'과 '식는 것'을 구분"),
            ("데이터", "네이버 데이터랩 검색어트렌드 실데이터 — 한국 사용자의 일별 검색 관심도 (2026-06-11 수집)"),
            ("프록시 가정", "인스타그램은 해시태그 시계열 공개 API가 없음 → 같은 주제의 네이버 검색량을 한국 관심도의 대리지표로 사용"),
            ("분석 절차", "EDA → 평활화 → 정상성 진단 → ACF → 분해 → 계절성/모멘텀 → 예측 → 액션"),
        ],
    )

    bullets_slide(
        prs, next(pg), "데이터셋", "01 · Dataset",
        lead=f"{stats['date_start']} ~ {stats['date_end']} · {stats['n_days']}일 · 일 단위 · 라이프스타일 해시태그 {stats['n_tags']}개",
        bullets=[
            ("수집", "네이버 데이터랩 검색어트렌드 API — 키워드그룹별 일별 ratio (그룹 예: 러닝=러닝+러닝크루)"),
            ("대상 태그", "#러닝 #캠핑 #등산 #카페 #국내여행 #다이어트 #피크닉 #클라이밍 #빵지순례"),
            ("ratio의 의미", "요청 내 최대값=100인 상대값 → 시리즈 간 절대 비교는 불가, 시리즈 내 시간 변화 분석은 유효"),
            ("형태", "tidy 패널 (date, hashtag, ratio) → pivot하여 날짜×태그 행렬로 분석"),
        ],
    )

    # ---------------- Part 1: 직관 ---------------- #
    section_slide(prs, "Part 1 · Intuition", "시계열, 직관으로 이해하기", "01")

    intuition_slide(
        prs, next(pg), "① 시계열은 '겹쳐진 신호'다", "02 · Intuition",
        question="하나의 그래프처럼 보이지만, 사실은 여러 신호가 포개진 결과다.",
        analogy="노래 한 곡 = 멜로디 + 비트 + 잡음. 시계열도 추세 + 주기 + 우연이 합쳐진 소리다.",
        cards=[
            ("📈", "추세 (장기 방향)", "팔로워가 늘듯 천천히 오르내리는 큰 흐름. '이 태그가 뜨는가, 식는가'를 결정."),
            ("🔁", "계절성 (반복 리듬)", "매주 주말마다 솟는 규칙적 패턴. 달력만 봐도 예상되는 출렁임."),
            ("🎲", "불규칙 (우연·이벤트)", "연휴·바이럴처럼 설명 안 되는 잡음과 깜짝 사건. 예측이 어려운 부분."),
        ],
        formula="관측 = 추세(T) + 계절(S) + 불규칙(R)",
    )

    intuition_slide(
        prs, next(pg), "② 비교하려면 '추세를 걷어내라'", "02 · Intuition",
        question="값이 계속 커지면 어제와 오늘을 그대로 비교할 수 없다 — 기준선이 움직이니까.",
        analogy="키 자체가 아니라 '어제보다 몇 cm 자랐나'를 보면, 성장 속도를 공정하게 비교할 수 있다.",
        cards=[
            ("🪜", "비정상 (기준선이 이동)", "평균이 시간에 따라 움직이는 상태. 추세 때문에 '가짜 상관'에 속기 쉽다."),
            ("➖", "차분 = 어제와의 차이", "Xₜ − Xₜ₋₁ 로 바꾸면 추세가 사라지고 변화량만 남는다."),
            ("⚖️", "정상성 (안정된 신호)", "평균·변동이 일정해진 상태. 그래야 패턴 분석과 예측이 신뢰성을 가진다."),
        ],
        formula="차분  ∇Xₜ = Xₜ − Xₜ₋₁    (추세 제거)",
    )

    intuition_slide(
        prs, next(pg), "③ '같은 패턴이 반복되나?' — 자기상관", "02 · Intuition",
        question="오늘 값이 7일 전과 닮았는가? 닮은 정도를 시차별로 재면 숨은 리듬이 드러난다.",
        analogy="요일 장사 같다 — 이번 주 토요일 매출은 지난 토요일과 닮는다. 그 '닮음'이 자기상관.",
        cards=[
            ("📊", "자기상관 (ACF)", "며칠 전 값과 얼마나 닮았는지 시차별로 측정. lag 7에서 튀면 '주간 리듬' 존재."),
            ("🔇", "백색잡음", "아무 패턴 없는 순수 잡음. 분석 후 남은 찌꺼기가 여기에 가까우면 잘 설명한 것."),
            ("🤖", "예측 모델", "추세+요일 패턴을 학습해 미래로 연장. 더 정교한 버전이 ARIMA·SARIMA."),
        ],
        formula="자기상관  ρ(k) = corr(Xₜ, Xₜ₋ₖ)",
    )

    # ---------------- Part 2: 분석 ---------------- #
    section_slide(prs, "Part 2 · Analysis", "실데이터로 분석하기", "02")

    chart_slide(
        prs, next(pg), "원시 시계열 관찰", "03 · Raw signal", "01_overview.png",
        ["9개 태그의 일별 관심도 원계열", "톱니 모양 = 주 7일 계절성", "#캠핑·#피크닉: 봄에 큰 산(계절 추세)", "#카페: 1월 고점 후 하락", "5월 중순 #등산 스파이크 = 연휴 외생 이벤트"],
    )
    chart_slide(
        prs, next(pg), "이동평균 평활화", "03 · Smoothing", "02_moving_average.png",
        [f"포커스: #{FOCUS} (6월 모멘텀 1위)", "회색 = 원계열(노이즈)", "7일 MA = 주간 주기 상쇄", "28일 MA = 장기 추세만", "1~5월 꾸준한 우상향 확인"],
    )
    chart_slide(
        prs, next(pg), "정상성 진단과 차분", "03 · Stationarity", "03_stationarity.png",
        ["위: 롤링 평균이 계속 상승 → 평균 비불변 = 비정상", "롤링 표준편차도 5월에 점프", "아래: 1차 차분 후 평균이 0에 고정", "차분으로 (약)정상성 확보 → ARIMA의 d=1에 해당"],
    )
    chart_slide(
        prs, next(pg), "자기상관함수(ACF)", "03 · ACF", "04_acf.png",
        ["왼쪽(원계열): 천천히 감쇠 → 추세 지배 = 비정상 신호", "오른쪽(차분): lag 7·14·21 스파이크 → 주간 계절성", "점선 = ±1.96/√n 백색잡음 한계", "이론 그대로: 차분이 추세를 지우자 주기가 드러남"],
    )
    chart_slide(
        prs, next(pg), "가법 분해", "03 · Decomposition", "05_decomposition.png",
        ["X = 추세 + 계절 + 잔차로 분리", "추세: 1월~5월 +60% 수준 상승", "계절: 주말 양(+), 주중 음(−) 규칙 진동", "잔차: 5월 연휴 스파이크 외엔 백색잡음에 가까움"],
    )
    chart_slide(
        prs, next(pg), "주간 계절성 프로파일", "03 · Seasonality", "06_weekly_profile.png",
        ["요일 평균을 자기 평균=100으로 정규화", "#등산·#피크닉·#캠핑: 주말(토) 피크", "#다이어트: 월요일 피크 — '월요일 결심' 효과", "게시 타이밍 설계의 직접 근거"],
    )
    chart_slide(
        prs, next(pg), "성장 모멘텀", "03 · Momentum", "07_growth.png",
        [f"1월 첫 주=100 지수화", f"연초 대비: #피크닉 +{g['피크닉']:.0f}% · #캠핑 +{g['캠핑']:.0f}% · #등산 +{g['등산']:.0f}%",
         f"최근 30일: #등산 +{m['등산']:.1f}% · #클라이밍 +{m['클라이밍']:.1f}% 만 상승", "봄 태그(피크닉·캠핑)는 5월 피크 통과 후 하락 전환"],
    )
    chart_slide(
        prs, next(pg), "14일 예측", "03 · Forecast", "08_forecast.png",
        ["모형: 선형추세 + 요일 계절성 (최근 8주 적합)", "점선 = 6/11~6/24 예측 경로", "음영 = 95% 예측구간 (잔차 분산 기반)", "주말마다 솟는 요일 패턴까지 재현"],
    )
    chart_slide(
        prs, next(pg), "모델 비교 — 베이스라인 vs SARIMA", "04 · Model comparison", "09_sarima_compare.png",
        [
            "분홍 = 선형추세+요일더미(수업용 기본형)",
            "검정 = SARIMA(1,1,1)(1,1,1)₇ — 차분·AR·MA·계절을 모두 추정",
            f"홀드아웃 백테스트(마지막 14일): 평균절대오차 SARIMA {stats['sar_mae']:.2f} < 베이스라인 {stats['base_mae']:.2f}",
            "SARIMA가 ~14% 더 정확 — 다만 해석은 베이스라인이 더 투명(추세·요일 분리)",
            "교훈: 단순 모델로 '구조 이해', SARIMA로 '정확도' — 목적에 따라 선택",
        ],
    )

    # ---------------- 결론 ---------------- #
    section_slide(prs, "Conclusion", "그래서, 지금 뭘 써야 하나", "03")

    cards_slide(
        prs, next(pg), "2026-06-11 기준 트렌딩 해시태그", "05 · Now trending",
        cards=[
            ("📈 지금 상승 중 (최근 30일 모멘텀 +)", "#등산  #클라이밍",
             f"등산 +{m['등산']:.1f}%, 클라이밍 +{m['클라이밍']:.1f}% — 초여름에도 모멘텀 유지, 지금 올라탈 태그", PINK),
            ("🌊 피크 통과 (계절성 하락 전환)", "#피크닉  #캠핑",
             f"연초 대비 +{g['피크닉']:.0f}%/+{g['캠핑']:.0f}%로 컸지만 최근 30일 {m['피크닉']:.0f}%/{m['캠핑']:.0f}% — 봄 수요 종료", PURPLE),
            ("💪 안정 수요 (시즌 진입)", "#다이어트",
             f"최근 30일 {m['다이어트']:+.1f}%로 하락 멈춤 — 여름 직전 수요 재점화 구간, 월요일 피크 활용", INK),
            ("📉 약세 지속", "#카페  #국내여행",
             f"연초 대비 {g['카페']:.0f}%/{g['국내여행']:.0f}% — 단독 태그보다 상승 태그와 조합 권장", GREY),
        ],
    )

    bullets_slide(
        prs, next(pg), "콘텐츠 활용 전략", "05 · Action",
        lead="시계열 인사이트 → 게시물 전략: 무엇을(태그), 언제(요일), 어떻게(조합)",
        bullets=[
            ("주력 태그", "#등산 #클라이밍 중심 콘텐츠 — 상승 모멘텀 구간에 게시해 노출 탄력 확보"),
            ("게시 타이밍", "아웃도어 태그는 금~토 오전(주말 피크 직전), #다이어트는 일 저녁~월 오전('월요일 결심' 수요 선점)"),
            ("태그 조합", "상승 태그 + 안정 태그 묶기: #등산 × #다이어트(여름 준비), #클라이밍 × #카페(실내 연계)"),
            ("리스크 관리", "#피크닉·#캠핑은 하락 전환 — 신규 기획 보류, 기존 콘텐츠는 내년 3~4월 재활용 예약"),
            ("운영 루프", "데이터랩 재수집(주 1회) → 모멘텀 갱신 → 태그 포트폴리오 리밸런싱"),
        ],
    )

    # 문제 정의로 되돌아가기: "우리 계정은 어떻게 될까?"
    chart_slide(
        prs, next(pg), "되돌아온 질문: 우리 계정은 어떻게 될까", "06 · Our account", "10_account_decomp.png",
        [
            "가상 계정의 일별 도달을 분해 (※ 교육용 시뮬레이션)",
            "추세: 팔로워 성장에 따른 꾸준한 우상향",
            "계절: 주말(일) 피크 — 요일 효과",
            "바이럴 릴스 1건 = 추세가 아니라 잔차로 포착",
            "→ '한 번 터진 것'과 '꾸준한 성장'은 다른 성분, 분리해야 보임",
        ],
    )
    chart_slide(
        prs, next(pg), "우리 계정 14일 예측", "06 · Our account", "11_account_forecast.png",
        [
            f"분석 기간 도달 +{stats['acct_growth']:.0f}% 성장",
            f"추세 기울기 +{stats['acct_slope']:.0f}/일 (양수=성장 지속)",
            "바이럴 스파이크가 가라앉아도 기저 추세는 우상향",
            "예측: 완만한 상승 + 주말 피크 반복",
            "답: 단발 바이럴에 일희일비 말고 추세 기울기를 보라",
        ],
    )

    # ---------------- 부록 ---------------- #
    code_slide(
        prs, next(pg), "핵심 코드 ①  데이터 → 평활화 → 차분", "07 · Code",
        blocks=[
            ("tidy 패널을 날짜×태그 행렬로 (pandas pivot)",
             'wide = panel.pivot(index="date", columns="hashtag", values="ratio")'),
            ("이동평균 평활화 — 7일 중심 윈도우가 주간 주기를 상쇄",
             "ma7 = s.rolling(7, center=True).mean()   # 추세 + 노이즈 제거"),
            ("1차 차분으로 정상화 (ARIMA의 d=1)",
             "diff = s.diff()                          # X_t - X_{t-1}\n"
             "diff.rolling(28).mean()                  # 평균이 0에 붙는지 진단"),
            ("가법 분해 — 추세는 이동평균, 계절은 '같은 요일끼리 평균'",
             "trend    = s.rolling(7, center=True).mean()\n"
             'seasonal = (s - trend).groupby(s.index.weekday).transform("mean")\n'
             "residual = s - trend - seasonal          # 백색잡음이면 성공"),
        ],
    )

    code_slide(
        prs, next(pg), "핵심 코드 ②  ACF → 예측", "07 · Code",
        blocks=[
            ("표본 ACF 직접 구현 — ρ(k) = γ(k)/γ(0)",
             "x = x - x.mean()\n"
             "rho_k = np.dot(x[:n-k], x[k:]) / np.dot(x, x)\n"
             "band  = 1.96 / np.sqrt(n)                # 백색잡음 95% 한계"),
            ("선형추세 적합 (최소제곱) + 요일 더미 계절성",
             "coef = np.polyfit(t, s.values, 1)        # 기울기·절편\n"
             "seasonal = pd.Series(s.values - np.polyval(coef, t)) \\\n"
             "             .groupby(s.index.weekday).mean()"),
            ("14일 외삽 + 95% 예측구간 (잔차 표준편차 기반)",
             "future = np.polyval(coef, future_t) + seasonal[future_weekday]\n"
             "lo, hi = future - 1.96*resid_std, future + 1.96*resid_std"),
        ],
    )

    bullets_slide(
        prs, next(pg), "한계와 재현", "07 · Limitations",
        lead="정직한 캐비앗: 이 분석이 말할 수 있는 것과 없는 것",
        bullets=[
            ("프록시 한계", "네이버 검색량 ≠ 인스타그램 게시량 — '한국 사용자의 주제 관심도'의 대리지표로 해석해야 함"),
            ("상대값 한계", "데이터랩 ratio는 요청 내 정규화 — 태그 간 절대 규모 비교 불가, 시간 변화·모멘텀 비교만 유효"),
            ("실시간성", "2026-06-11 수집 스냅샷 — '실시간 스트림'이 아니라 주기 재수집으로 갱신하는 구조 (전일까지 일별 제공)"),
            ("계정 시뮬레이션", "'우리 계정' 도달은 계정 인사이트 공개 API가 없어 합성한 교육용 데이터 — 분해/예측 방법론 시연용이며 실측 아님"),
            ("모형 한계", "선형 베이스라인은 외생 이벤트·추세 전환을 늦게 반영(백테스트 MAE에서 SARIMA에 열세) — 단순성/해석력과 정확도의 트레이드오프"),
            ("재현", "pip install -r presentation/requirements.txt && python presentation/build_deck.py — CSV·시드 고정으로 결정론적 재생성"),
        ],
    )

    prs.save(OUT)
    return OUT, len(prs.slides._sldIdLst)


if __name__ == "__main__":
    path, n = build()
    print(f"Saved: {path} ({n} slides)")
