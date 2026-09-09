"""
app.py — 패션 이커머스 MD 운영 대시보드 (포트폴리오)
====================================================
라이선스 브랜드(르까프/네파키즈) 쿠팡 채널 운영 경험을 바탕으로
실제 업무 로직(OOS 관리, ASP 모니터링, 매출 추이 분석)을
시뮬레이션 데이터로 재구현한 의사결정 지원 대시보드입니다.

⚠️ 모든 데이터는 시뮬레이션이며, 실제 기업 정보를 포함하지 않습니다.

실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from mock_data import (
    generate_sku_master, calc_oos_metrics,
    generate_monthly_trend, generate_asp_monitoring,
    generate_brand_summary,
)

# ── 페이지 설정 ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MD Operations Dashboard",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 디자인 토큰 ────────────────────────────────────────────────────────────
# 컬러: 딥네이비 베이스 + 시그널 컬러(레드/엠버/그린)로 위험도 직관화
# 타이포: Pretendard(본문) + JetBrains Mono(수치/코드성 데이터)
PRIMARY   = "#5B8DEF"
DANGER    = "#FF4D4D"
WARNING   = "#FFA940"
CAUTION   = "#FFD666"
SAFE      = "#52C97A"
BRAND_A   = "#5B8DEF"   # 르까프
BRAND_B   = "#B084F0"   # 네파키즈

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Pretendard', -apple-system, sans-serif; }

    .main { background-color: #0B0E14; }
    section[data-testid="stSidebar"] { background-color: #11151D; border-right: 1px solid #232838; }

    .hero-title { font-size: 2.1rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 0.2rem; }
    .hero-sub   { color: #8B93A7; font-size: 0.95rem; line-height: 1.6; }

    .stat-label { color: #8B93A7; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }

    div[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; font-weight: 700; }
    div[data-testid="stMetricLabel"] { color: #8B93A7 !important; }

    .badge { display:inline-block; padding:3px 11px; border-radius:20px; font-size:11.5px; font-weight:700; font-family:'JetBrains Mono', monospace; }
    .badge-critical { background: rgba(255,77,77,0.14); color:#FF4D4D; border:1px solid rgba(255,77,77,0.4); }
    .badge-warning  { background: rgba(255,169,64,0.14); color:#FFA940; border:1px solid rgba(255,169,64,0.4); }
    .badge-caution  { background: rgba(255,214,102,0.14); color:#FFD666; border:1px solid rgba(255,214,102,0.4); }
    .badge-safe     { background: rgba(82,201,122,0.14); color:#52C97A; border:1px solid rgba(82,201,122,0.4); }
    .badge-neutral  { background: rgba(139,147,167,0.14); color:#8B93A7; border:1px solid rgba(139,147,167,0.3); }

    .section-card {
        background: linear-gradient(180deg, #131826 0%, #10141F 100%);
        border: 1px solid #232838;
        border-radius: 14px;
        padding: 22px 24px;
    }

    .pipeline-step {
        background: #131826; border:1px solid #232838; border-radius:10px;
        padding: 14px 16px; text-align:center; font-size:0.82rem; color:#C5CAD9;
    }
    .pipeline-arrow { color:#3A4256; font-size:1.4rem; text-align:center; }

    [data-testid="stTabs"] button { font-weight:600; }

    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

RISK_BADGE = {
    "품절": '<span class="badge badge-critical">🔴 품절</span>',
    "긴급": '<span class="badge badge-critical">🟠 긴급</span>',
    "주의": '<span class="badge badge-warning">🟡 주의</span>',
    "안전": '<span class="badge badge-safe">🟢 안전</span>',
    "제외": '<span class="badge badge-neutral">⚪ 제외</span>',
}
RISK_COLOR = {"품절": DANGER, "긴급": "#FF7A45", "주의": CAUTION, "안전": SAFE, "제외": "#4A5268"}
BRAND_COLOR = {"르까프": BRAND_A, "네파키즈": BRAND_B}


# ── 데이터 로드 (캐시) ────────────────────────────────────────────────────

@st.cache_data
def load_all_data(seed: int, n_sku: int, n_pi: int):
    sku = calc_oos_metrics(generate_sku_master(seed=seed, n_sku=n_sku))
    monthly = generate_monthly_trend(seed=seed + 1)
    asp = generate_asp_monitoring(seed=seed + 2, n_pi=n_pi)
    summary = generate_brand_summary(monthly, sku, asp)
    return sku, monthly, asp, summary


# ── 사이드바 ──────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🧭 MD Operations")
    st.caption("패션 이커머스 채널 운영 대시보드")
    st.divider()

    with st.expander("⚙️ 시뮬레이션 설정", expanded=False):
        seed = st.number_input("랜덤 시드", 1, 999, 42)
        n_sku = st.slider("SKU 개수", 30, 200, 90, step=10)
        n_pi = st.slider("PI 개수 (ASP)", 15, 60, 35, step=5)

    sku_df, monthly_df, asp_df, summary_df = load_all_data(seed, n_sku, n_pi)

    st.divider()
    st.markdown("##### 🏷️ 브랜드 필터")
    brand_filter = st.multiselect(
        "브랜드 선택", options=["르까프", "네파키즈"],
        default=["르까프", "네파키즈"], label_visibility="collapsed"
    )

    st.divider()
    st.caption(
        "⚠️ 본 대시보드는 실제 라이선스 브랜드 쿠팡 채널 운영 경험을 바탕으로 "
        "업무 로직을 재구현한 포트폴리오입니다. 표시되는 모든 데이터는 "
        "시뮬레이션이며 실제 기업 정보를 포함하지 않습니다."
    )


sku_f = sku_df[sku_df["브랜드"].isin(brand_filter)]
monthly_f = monthly_df[monthly_df["브랜드"].isin(brand_filter)]
asp_f = asp_df[asp_df["브랜드"].isin(brand_filter)]
summary_f = summary_df[summary_df["브랜드"].isin(brand_filter)]


# ── 헤더 ──────────────────────────────────────────────────────────────────

st.markdown('<div class="hero-title">라이선스 브랜드 쿠팡 채널 운영 대시보드</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">수기로 진행하던 OOS 관리·가격 모니터링 프로세스를 '
    '정량 지표 기반 자동화 시스템으로 재설계했습니다. '
    '아래 4개 영역은 실제 담당 업무를 1:1로 매핑한 구성입니다.</div>',
    unsafe_allow_html=True
)
st.write("")

# 파이프라인 시각화 (업무 흐름 한눈에)
pc1, pa1, pc2, pa2, pc3, pa3, pc4 = st.columns([3, 0.6, 3, 0.6, 3, 0.6, 3])
steps = [
    "📥 애널리틱스 물류·성과지표<br>다운로드 (재고/판매량)",
    "📦 OOS 위험도 자동 분류<br>(품절예상일·발주여유일)",
    "💰 ASP 가격 이탈 탐지<br>(쿠팡 크롤링 + 네이버 API)",
    "🏆 브랜드별 성과 종합<br>(매출·재고·가격 통합)",
]
for col, step in zip([pc1, pc2, pc3, pc4], steps):
    col.markdown(f'<div class="pipeline-step">{step}</div>', unsafe_allow_html=True)
for col in [pa1, pa2, pa3]:
    col.markdown('<div class="pipeline-arrow">→</div>', unsafe_allow_html=True)

st.write("")
st.divider()


# ── 전체 KPI 요약 (최상단) ────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)

total_sku = len(sku_f[sku_f["위험도"] != "제외"])
critical_sku = len(sku_f[sku_f["위험도"].isin(["품절", "긴급"])])
asp_error = len(asp_f[asp_f["상태"] == "오류"])
asp_total = len(asp_f)
latest_revenue = monthly_f.groupby("월")["매출액"].sum().iloc[-1] if not monthly_f.empty else 0
first_revenue = monthly_f.groupby("월")["매출액"].sum().iloc[0] if not monthly_f.empty else 1
revenue_growth = round((latest_revenue / first_revenue - 1) * 100, 1) if first_revenue else 0
avg_oos_improve = round(summary_f["OOS율개선"].mean(), 1) if not summary_f.empty else 0

with k1:
    st.metric("관리 대상 SKU", f"{total_sku:,}개")
with k2:
    st.metric("발주 대응 필요", f"{critical_sku}개", delta=f"-{critical_sku}", delta_color="inverse")
with k3:
    st.metric("ASP 가격 오류", f"{asp_error}/{asp_total}건", delta=f"-{asp_error}", delta_color="inverse")
with k4:
    st.metric("매출 성장", f"+{revenue_growth}%", delta=f"{revenue_growth}%")
with k5:
    st.metric("OOS율 개선폭", f"{avg_oos_improve}%p", delta=f"{avg_oos_improve}%p")

st.divider()


# ── 탭 구성 ───────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📦  OOS 발주관리", "📈  매출·입고 추이", "💰  ASP 가격 모니터링", "🏆  브랜드별 종합성과"
])


# ════════════════════════════════════════════════════════════════════════
# TAB 1 — OOS 발주관리
# ════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("#### 발주 타이밍 자동 판정")
    st.caption(
        "쿠팡 FC 재고와 최근 14일 평균 판매량을 기반으로 품절 예상일을 계산하고, "
        "SKU별 리드타임을 고려해 발주 여유일수와 위험도 등급을 자동 산출합니다."
    )

    with st.expander("📖 산출 로직 보기"):
        st.code(
            "소진율       = (쿠팡총납품수량 − 쿠팡FC현재고) ÷ 쿠팡총납품수량\n"
            "일평균판매량 = 최근 14일 판매량 평균 (애널리틱스 성과지표)\n"
            "품절예상일수 = 쿠팡FC현재고 ÷ 일평균판매량\n"
            "발주여유일수 = 품절예상일수 − 리드타임\n\n"
            "발주여유일수 ≤ 0   → 🔴 긴급 (즉시 발주 요청)\n"
            "발주여유일수 ≤ 3   → 🟡 주의 (발주 검토)\n"
            "발주여유일수 > 3   → 🟢 안전\n"
            "쿠팡FC현재고 = 0    → 🔴 품절 (발생 완료)\n"
            "비고에 '체크제외/단종예정' → ⚪ 제외",
            language="text"
        )

    oc1, oc2, oc3, oc4 = st.columns(4)
    active = sku_f[sku_f["위험도"] != "제외"]
    with oc1: st.metric("긴급/품절", f"{len(active[active['위험도'].isin(['긴급','품절'])])}개")
    with oc2: st.metric("주의", f"{len(active[active['위험도']=='주의'])}개")
    with oc3: st.metric("안전", f"{len(active[active['위험도']=='안전'])}개")
    with oc4: st.metric("평균 소진율", f"{active['소진율'].mean()*100:.1f}%")

    st.write("")
    left, right = st.columns([1.5, 1])

    with left:
        st.markdown("##### 🚨 발주 우선순위 리스트")
        risk_pick = st.multiselect(
            "위험도 필터", ["품절", "긴급", "주의", "안전", "제외"],
            default=["품절", "긴급", "주의"]
        )
        display_cols = [
            "시즌구분", "SKU_ID", "SKU명", "쿠팡총납품수량", "쿠팡FC현재고",
            "물류직영현재고", "소진율", "일평균판매량_14일",
            "품절예상일수", "리드타임", "발주여유일수", "위험도", "발주가능여부", "비고"
        ]
        view = sku_f[sku_f["위험도"].isin(risk_pick)][display_cols].copy()
        view["소진율"] = (view["소진율"] * 100).round(1).astype(str) + "%"

        def style_risk(val):
            m = {
                "품절": "background-color: rgba(255,77,77,0.18); color:#FF4D4D; font-weight:700;",
                "긴급": "background-color: rgba(255,122,69,0.18); color:#FF7A45; font-weight:700;",
                "주의": "background-color: rgba(255,214,102,0.14); color:#FFD666; font-weight:600;",
                "안전": "background-color: rgba(82,201,122,0.14); color:#52C97A;",
                "제외": "color:#4A5268;",
            }
            return m.get(val, "")

        def style_order(val):
            if "발주가능" in str(val):
                return "color:#52C97A; font-weight:700;"
            if "발주불가" in str(val):
                return "color:#FF4D4D; font-weight:700;"
            return "color:#4A5268;"

        st.dataframe(
            view.style.map(style_risk, subset=["위험도"])
                      .map(style_order, subset=["발주가능여부"]),
            use_container_width=True, height=460, hide_index=True
        )
        csv = view.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 발주 리스트 CSV 다운로드", csv,
                            f"OOS_발주리스트_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv", use_container_width=True)

    with right:
        st.markdown("##### 위험도 분포")
        rc = active["위험도"].value_counts().reindex(["품절","긴급","주의","안전"]).fillna(0).astype(int)
        fig = go.Figure(data=[go.Pie(
            labels=rc.index, values=rc.values, hole=0.62,
            marker=dict(colors=[RISK_COLOR[r] for r in rc.index]),
            textinfo="label+value", textfont=dict(size=12.5, color="white"),
        )])
        fig.update_layout(showlegend=False, height=260, margin=dict(t=10,b=10,l=10,r=10),
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### SKU 상세 — 재고 소진 예측")
        opts = active["SKU_ID"].tolist()
        if opts:
            pick = st.selectbox("SKU 선택", opts, label_visibility="collapsed")
            row = sku_f[sku_f["SKU_ID"] == pick].iloc[0]
            st.markdown(f"**{row['SKU명']}**  {RISK_BADGE[row['위험도']]}", unsafe_allow_html=True)

            days = np.arange(0, 31)
            proj = np.maximum(row["쿠팡FC현재고"] - row["일평균판매량_14일"] * days, 0)
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=days, y=proj, mode="lines", line=dict(color=PRIMARY, width=3),
                                       fill="tozeroy", fillcolor="rgba(91,141,239,0.15)"))
            fig2.add_vline(x=max(row["품절예상일수"], 0), line_dash="dash", line_color=DANGER,
                            annotation_text="품절예상", annotation_font_color=DANGER)
            fig2.update_layout(height=200, margin=dict(t=10,b=10,l=10,r=10),
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(color="white", size=11), xaxis_title="경과일", yaxis_title="재고")
            st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
# TAB 2 — 매출·입고 추이
# ════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("#### 입사 후 매출·입고 추이")
    st.caption("브랜드별 월별 매출액·입고수량·OOS율 변화를 추적합니다.")

    mc1, mc2 = st.columns(2)

    with mc1:
        st.markdown("##### 💰 브랜드별 월별 매출액")
        fig3 = px.line(monthly_f, x="월", y="매출액", color="브랜드", markers=True,
                        color_discrete_map=BRAND_COLOR)
        fig3.update_traces(line=dict(width=3), marker=dict(size=7))
        fig3.update_layout(height=320, margin=dict(t=10,b=10,l=10,r=10),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="white"), legend=dict(orientation="h", y=1.1),
                            yaxis_tickformat=",")
        st.plotly_chart(fig3, use_container_width=True)

    with mc2:
        st.markdown("##### 📦 브랜드별 월별 입고수량")
        fig4 = px.bar(monthly_f, x="월", y="입고수량", color="브랜드", barmode="group",
                       color_discrete_map=BRAND_COLOR)
        fig4.update_layout(height=320, margin=dict(t=10,b=10,l=10,r=10),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="white"), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("##### 📉 OOS율 개선 추이")
    st.caption("OOS 관리 시스템 도입 이후 품절 발생률이 점진적으로 감소한 추세입니다.")
    fig5 = px.line(monthly_f, x="월", y="OOS율", color="브랜드", markers=True,
                    color_discrete_map=BRAND_COLOR)
    fig5.update_traces(line=dict(width=3), marker=dict(size=7))
    fig5.update_layout(height=280, margin=dict(t=10,b=10,l=10,r=10),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="white"), yaxis_tickformat=".0%",
                        legend=dict(orientation="h", y=1.15))
    st.plotly_chart(fig5, use_container_width=True)

    with st.expander("📊 월별 데이터 테이블 보기"):
        view2 = monthly_f.copy()
        view2["매출액"] = view2["매출액"].apply(lambda x: f"{x:,}원")
        view2["OOS율"] = (view2["OOS율"] * 100).round(1).astype(str) + "%"
        st.dataframe(view2, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════
# TAB 3 — ASP 가격 모니터링
# ════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("#### ASP 가격 이탈 자동 탐지")
    st.caption(
        "쿠팡 Ads Center에서 PI별 전 옵션(SKU) 가격을 자동 수집해 최저가/최고가를 산출하고, "
        "최초 등록 ASP와 비교하여 가격 이탈 여부를 판정합니다. "
        "이탈 발생 시 네이버 쇼핑 전 채널을 전수조사하여 타 채널 저가 노출 여부를 확인하고 원인을 자동 분류합니다."
    )

    with st.expander("📖 최종가 판정 로직 + 원인 진단 흐름 보기"):
        st.code(
            "[1] 쿠팡 Ads Center 크롤링 → PI별 전 옵션 가격 수집\n"
            "    최저가 = PI 내 옵션 중 최저 판매가\n"
            "    최고가 = PI 내 옵션 중 최고 판매가\n\n"
            "[2] 최종가 판정\n"
            "    최저가 < ASP                  → 최종가 = 최저가\n"
            "    최저가 = ASP, 최고가 > ASP    → 최종가 = 최고가\n"
            "    최저가 > ASP, 최고가 > ASP    → 최종가 = 최고가\n\n"
            "[3] 최종가 ≠ ASP → 오류 판정\n"
            "    → 네이버 쇼핑 전수조사 (상품명 + 기준가 비교)\n"
            "    → 오픈마켓 저가 노출 발견 시 → 오픈마켓팀 가격수정 요청\n"
            "    → 발견 안 될 시 → 쿠팡 자체 자동가격조정 → BM 가격수정 요청",
            language="text"
        )

    ac1, ac2, ac3, ac4 = st.columns(4)
    error_cnt = len(asp_f[asp_f["상태"] == "오류"])
    total_cnt = len(asp_f)
    compliance = round((total_cnt - error_cnt) / max(total_cnt,1) * 100, 1)
    openmarket_cnt = len(asp_f[asp_f["원인"].str.contains("노출", na=False)])
    avg_drop = asp_f[asp_f["이탈액"] < 0]["이탈액"].mean()

    with ac1: st.metric("ASP 준수율", f"{compliance}%")
    with ac2: st.metric("가격 오류 PI", f"{error_cnt}/{total_cnt}건")
    with ac3: st.metric("오픈마켓 원인", f"{openmarket_cnt}건")
    with ac4: st.metric("평균 하락액", f"{avg_drop:,.0f}원" if not np.isnan(avg_drop) else "-")

    st.write("")
    al, ar = st.columns([1.6, 1])

    with al:
        st.markdown("##### 💸 PI별 가격 현황")
        status_pick = st.radio("상태 필터", ["전체", "오류만"], horizontal=True, label_visibility="collapsed")
        view3 = asp_f if status_pick == "전체" else asp_f[asp_f["상태"] == "오류"]
        view3 = view3[["PI명","브랜드","ASP","최저가","최고가","최종가","이탈액","상태","원인","조치"]].copy()

        def style_status(val):
            return "background-color: rgba(255,77,77,0.16); color:#FF4D4D; font-weight:700;" if val == "오류" \
                else "background-color: rgba(82,201,122,0.12); color:#52C97A;"

        st.dataframe(
            view3.style.map(style_status, subset=["상태"]),
            use_container_width=True, height=420, hide_index=True
        )
        csv2 = view3.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 ASP 모니터링 결과 CSV 다운로드", csv2,
                            f"ASP_모니터링_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv", use_container_width=True)

    with ar:
        st.markdown("##### 오류 원인 분포")
        err_df = asp_f[asp_f["상태"] == "오류"]
        if not err_df.empty:
            cause_counts = err_df["원인"].apply(
                lambda x: "오픈마켓 저가노출" if "노출" in x else "쿠팡 자동가격조정"
            ).value_counts()
            fig6 = go.Figure(data=[go.Pie(
                labels=cause_counts.index, values=cause_counts.values, hole=0.55,
                marker=dict(colors=[WARNING, PRIMARY]),
                textinfo="label+percent", textfont=dict(size=11.5, color="white"),
            )])
            fig6.update_layout(showlegend=False, height=240, margin=dict(t=10,b=10,l=10,r=10),
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig6, use_container_width=True)

            st.markdown("##### 브랜드별 오류 건수")
            brand_err = err_df.groupby("브랜드").size().reset_index(name="오류건수")
            fig7 = px.bar(brand_err, x="브랜드", y="오류건수", color="브랜드",
                           color_discrete_map=BRAND_COLOR, text="오류건수")
            fig7.update_traces(textposition="outside")
            fig7.update_layout(height=200, margin=dict(t=10,b=10,l=10,r=10), showlegend=False,
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig7, use_container_width=True)
        else:
            st.success("✅ 현재 가격 이탈 PI가 없습니다.")


# ════════════════════════════════════════════════════════════════════════
# TAB 4 — 브랜드별 운영 지표
# ════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("#### 브랜드별 운영 지표 비교")
    st.caption(
        "매출 성장률, OOS율 개선, 재고 안전 비율, ASP 준수율 4개 지표로 브랜드별 운영 현황을 비교합니다. "
        "지표별 단위와 척도가 달라 하나의 종합 점수로 합산하지 않고 개별 지표로 제시합니다."
    )

    cols = st.columns(len(summary_f)) if len(summary_f) > 0 else [st]
    for col, (_, row) in zip(cols, summary_f.iterrows()):
        with col:
            st.markdown(f"""
            <div class="section-card">
                <div style="font-size:1.2rem; font-weight:800; color:{BRAND_COLOR[row['브랜드']]}; margin-bottom:10px;">
                    {row['브랜드']}
                </div>
                <div style="color:#8B93A7; font-size:0.9rem; line-height:1.9;">
                    매출 성장률 <b style="color:#52C97A; float:right;">+{row['매출성장률']}%</b><br>
                    OOS율 개선 <b style="color:#52C97A; float:right;">{row['OOS율개선']}%p</b><br>
                    재고 안전비율 <b style="color:#E8EBF2; float:right;">{row['재고안전비율']}%</b><br>
                    ASP 준수율 <b style="color:#E8EBF2; float:right;">{row['ASP준수율']}%</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown("##### 📊 브랜드별 지표 비교")
        fig8 = go.Figure()
        for _, row in summary_f.iterrows():
            fig8.add_trace(go.Scatterpolar(
                r=[row["매출성장률"], row["OOS율개선"], row["재고안전비율"], row["ASP준수율"]],
                theta=["매출성장률", "OOS율개선", "재고안전비율", "ASP준수율"],
                fill="toself", name=row["브랜드"],
                line=dict(color=BRAND_COLOR[row["브랜드"]])
            ))
        fig8.update_layout(
            polar=dict(radialaxis=dict(visible=True, color="#8B93A7"), bgcolor="rgba(0,0,0,0)"),
            height=340, margin=dict(t=30,b=10,l=40,r=40),
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
            legend=dict(orientation="h", y=-0.1)
        )
        st.plotly_chart(fig8, use_container_width=True)

    with rc2:
        st.markdown("##### 💰 최근월 매출 비교")
        fig9 = px.bar(summary_f, x="브랜드", y="최근월매출", color="브랜드",
                       color_discrete_map=BRAND_COLOR, text="최근월매출")
        fig9.update_traces(texttemplate="%{text:,.0f}원", textposition="outside")
        fig9.update_layout(height=340, margin=dict(t=30,b=10,l=10,r=10), showlegend=False,
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="white"), yaxis_tickformat=",")
        st.plotly_chart(fig9, use_container_width=True)

    st.divider()
    st.markdown("##### 📋 핵심 운영 성과 요약")
    summary_view = summary_f.copy()
    summary_view["최근월매출"] = summary_view["최근월매출"].apply(lambda x: f"{x:,}원")
    summary_view["매출성장률"] = summary_view["매출성장률"].astype(str) + "%"
    summary_view["OOS율개선"] = summary_view["OOS율개선"].astype(str) + "%p"
    summary_view["재고안전비율"] = summary_view["재고안전비율"].astype(str) + "%"
    summary_view["ASP준수율"] = summary_view["ASP준수율"].astype(str) + "%"
    st.dataframe(summary_view, use_container_width=True, hide_index=True)


# ── 푸터 ──────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "💡 본 대시보드는 라이선스 브랜드(르까프/네파키즈) 쿠팡 채널 운영 실무 경험을 바탕으로, "
    "수기로 진행하던 OOS 관리 및 ASP 모니터링 프로세스의 의사결정 로직을 "
    "자동화 시스템으로 재구성한 포트폴리오 프로젝트입니다. "
    "실제 업무에서는 VBA 매크로와 Python 기반 데이터 수집 자동화를 통해 "
    "재고 리스트 갱신(2시간→20분), 가격 체크(4시간→1시간) 등 반복 업무를 자동화했습니다. "
    "표시된 모든 수치는 시뮬레이션이며 실제 기업 데이터를 포함하지 않습니다."
)
