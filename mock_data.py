"""
mock_data.py
============
실제 라이선스 브랜드 쿠팡 채널 운영 구조를 모사한 시뮬레이션 데이터 생성 모듈.
모든 수치는 랜덤 생성이며, 실제 기업 데이터를 포함하지 않습니다.

생성하는 데이터:
  1. SKU 마스터 (OOS 리스트 구조: 시즌/SKU ID/바코드/COGS/납품수량/재고/소진율 등)
  2. 일별 판매 이력 (최근 14일 평균 판매량 산출용)
  3. 월별 매출/입고 추이 (담당 시작 후 12개월)
  4. ASP 가격 모니터링 (PI별 최저/최고/최종가 vs ASP)
  5. 브랜드별 운영 지표 (매출성장률 / OOS율개선 / 재고안전비율 / ASP준수율)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ── 공통 마스터 데이터 ────────────────────────────────────────────────────

BRANDS = ["르까프", "네파키즈"]
SEASONS = ["26SS", "25FW", "25SS"]
CATEGORIES = {
    "르까프": ["아쿠아슈즈", "운동화", "트레이닝웨어", "모자"],
    "네파키즈": ["패딩", "맨투맨", "조끼", "플리스"],
}
COLORS = ["블랙", "화이트", "네이비", "레드", "그레이", "베이지"]
SIZE_SETS = {
    "아쿠아슈즈": ["210", "220", "230", "240", "250"],
    "운동화":     ["220", "230", "240", "250", "260"],
    "트레이닝웨어": ["S", "M", "L", "XL"],
    "모자":       ["FREE"],
    "패딩":       ["100", "110", "120", "130", "140"],
    "맨투맨":     ["100", "110", "120", "130"],
    "조끼":       ["100", "110", "120", "130"],
    "플리스":     ["100", "110", "120", "130"],
}

ONBOARD_DATE = datetime(2025, 10, 1)   # 담당 시작 시점 가정
TODAY = datetime(2026, 9, 30)
N_MONTHS = 12                          # 담당 개월 수


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


# ── 1. SKU 마스터 (OOS 리스트 구조) ──────────────────────────────────────

def generate_sku_master(seed: int = 42, n_sku: int = 90) -> pd.DataFrame:
    rng = _rng(seed)
    rows = []

    for i in range(n_sku):
        brand = rng.choice(BRANDS)
        category = rng.choice(CATEGORIES[brand])
        color = rng.choice(COLORS)
        size = rng.choice(SIZE_SETS[category])
        season = rng.choice(SEASONS)

        sku_id = f"{brand[:2].upper()}{2600+i:04d}"
        barcode = f"880{rng.integers(1000000000, 9999999999)}"

        cogs = int(rng.choice([8000, 9500, 11000, 13500, 15000, 18000]))
        asp = int(cogs * rng.uniform(2.0, 2.8) // 100 * 100)   # COGS 대비 마진율 기반 ASP

        total_supplied = int(rng.integers(50, 600))             # 쿠팡 총 납품수량
        fc_stock = int(rng.integers(0, min(80, total_supplied)))  # 쿠팡 FC 현재고
        warehouse_stock = int(rng.integers(0, 500))              # 물류 직영 현재고

        lead_time = int(rng.choice([3, 5, 7, 10, 14]))

        # 최근 14일 일별 판매량 시뮬레이션 (계절성 약간 반영)
        base_daily = rng.gamma(2.0, 1.6)
        daily_sales_14d = np.maximum(
            rng.normal(base_daily, base_daily * 0.3, 14), 0
        ).round(0)
        avg_daily_sales = round(daily_sales_14d.mean(), 1)

        consumption_rate = round(
            (total_supplied - fc_stock) / total_supplied, 3
        ) if total_supplied > 0 else 0

        # 비고 (입고예정/체크제외 랜덤 부여)
        note_pool = ["", "", "", "", "입고예정", "체크제외", "단종예정"]
        note = rng.choice(note_pool)

        rows.append({
            "시즌구분": season,
            "SKU_ID": sku_id,
            "SKU명": f"{brand} {category} {color} {size}",
            "Barcode": barcode,
            "브랜드": brand,
            "카테고리": category,
            "색상": color,
            "사이즈": size,
            "COGS": cogs,
            "ASP": asp,
            "쿠팡총납품수량": total_supplied,
            "쿠팡FC현재고": fc_stock,
            "물류직영현재고": warehouse_stock,
            "일평균판매량_14일": avg_daily_sales,
            "소진율": consumption_rate,
            "리드타임": lead_time,
            "비고": note,
        })

    return pd.DataFrame(rows)


def calc_oos_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """OOS 위험도 계산: 품절예상일수 / 발주여유일수 / 위험도 등급"""
    df = df.copy()
    safe_sales = df["일평균판매량_14일"].replace(0, 0.1)

    df["품절예상일수"] = (df["쿠팡FC현재고"] / safe_sales).round(1)
    df["발주여유일수"] = (df["품절예상일수"] - df["리드타임"]).round(1)

    def classify(row):
        if row["비고"] in ("체크제외", "단종예정"):
            return "제외"
        if row["쿠팡FC현재고"] == 0:
            return "품절"
        if row["발주여유일수"] <= 0:
            return "긴급"
        if row["발주여유일수"] <= 3:
            return "주의"
        return "안전"

    df["위험도"] = df.apply(classify, axis=1)

    # 발주 가능 여부: 쿠팡FC 재고 부족 + 물류 재고 있음 → 발주가능
    def order_possible(row):
        if row["비고"] in ("체크제외", "단종예정"):
            return "-"
        if row["위험도"] in ("품절", "긴급", "주의"):
            if row["물류직영현재고"] > 0:
                return "✅ 발주가능"
            else:
                return "❌ 발주불가"
        return "-"

    df["발주가능여부"] = df.apply(order_possible, axis=1)

    risk_order = {"품절": 0, "긴급": 1, "주의": 2, "안전": 3, "제외": 4}
    df["_order"] = df["위험도"].map(risk_order)
    df = df.sort_values(["_order", "발주여유일수"]).drop(columns="_order")
    return df


# ── 2. 월별 매출/입고 추이 (담당 시작 후 12개월) ─────────────────────────

def generate_monthly_trend(seed: int = 7) -> pd.DataFrame:
    rng = _rng(seed)
    months = pd.date_range(ONBOARD_DATE, periods=N_MONTHS, freq="MS")

    rows = []
    for brand in BRANDS:
        base_revenue = rng.uniform(80_000_000, 120_000_000)
        base_inbound = rng.integers(3000, 6000)

        # 입사 후 시간이 지날수록 우상향 트렌드 + 약간의 계절 변동
        growth = np.linspace(1.0, 1.65, N_MONTHS) + rng.normal(0, 0.04, N_MONTHS)
        seasonal = 1 + 0.15 * np.sin(np.linspace(0, 3, N_MONTHS))

        for idx, month in enumerate(months):
            revenue = int(base_revenue * growth[idx] * seasonal[idx])
            inbound = int(base_inbound * growth[idx] * rng.uniform(0.9, 1.15))
            oos_rate = max(0.02, 0.22 - idx * 0.015 + rng.normal(0, 0.012))  # OOS율 점진 개선

            rows.append({
                "월": month.strftime("%Y-%m"),
                "브랜드": brand,
                "매출액": revenue,
                "입고수량": inbound,
                "OOS율": round(oos_rate, 3),
            })

    return pd.DataFrame(rows)


# ── 3. ASP 가격 모니터링 (PI 단위) ───────────────────────────────────────

def generate_asp_monitoring(seed: int = 21, n_pi: int = 35) -> pd.DataFrame:
    rng = _rng(seed)
    rows = []

    for i in range(n_pi):
        brand = rng.choice(BRANDS)
        category = rng.choice(CATEGORIES[brand])
        pi_name = f"{brand} {category} {chr(65+i%26)}{i:03d}"

        asp = int(rng.choice([19900, 25500, 29090, 35000, 49000, 59000]))

        # 70% 정상, 30% 가격 이탈 시뮬레이션
        is_error = rng.random() < 0.3

        if is_error:
            direction = rng.choice(["하락", "상승"])
            if direction == "하락":
                min_price = int(asp * rng.uniform(0.80, 0.97))
                max_price = int(asp * rng.uniform(0.97, 1.05))
            else:
                min_price = int(asp * rng.uniform(1.0, 1.02))
                max_price = int(asp * rng.uniform(1.05, 1.25))
        else:
            min_price = asp
            max_price = asp

        # 최종가 판정 로직
        if min_price < asp:
            final_price = min_price
        elif min_price == asp and max_price > asp:
            final_price = max_price
        else:
            final_price = max_price

        status = "정상" if final_price == asp else "오류"

        # 오류일 경우 오픈마켓 원인 여부 (네이버쇼핑 API 조사 결과 시뮬레이션)
        if status == "오류":
            openmarket_issue = rng.random() < 0.6
            if openmarket_issue:
                source = rng.choice(["네이버 스마트스토어", "옥션", "지식쇼핑", "쇼핑하우"])
                cause = f"{source} 저가 노출"
                action = "오픈마켓팀 가격수정 요청"
            else:
                cause = "쿠팡 자체 자동가격조정"
                action = "BM 가격수정 요청 (부장 경유)"
        else:
            cause = "-"
            action = "-"

        rows.append({
            "PI명": pi_name,
            "브랜드": brand,
            "ASP": asp,
            "최저가": min_price,
            "최고가": max_price,
            "최종가": final_price,
            "이탈액": final_price - asp,
            "상태": status,
            "원인": cause,
            "조치": action,
        })

    return pd.DataFrame(rows)


# ── 4. 브랜드별 운영 지표 ────────────────────────────────────────────────

def generate_brand_summary(monthly_df: pd.DataFrame, oos_df: pd.DataFrame, asp_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for brand in BRANDS:
        m = monthly_df[monthly_df["브랜드"] == brand].sort_values("월")
        first_rev, last_rev = m["매출액"].iloc[0], m["매출액"].iloc[-1]
        growth_rate = round((last_rev / first_rev - 1) * 100, 1)

        first_oos, last_oos = m["OOS율"].iloc[0], m["OOS율"].iloc[-1]
        oos_improve = round((first_oos - last_oos) * 100, 1)

        o = oos_df[oos_df["브랜드"] == brand]
        safe_ratio = round((o["위험도"] == "안전").sum() / max(len(o), 1) * 100, 1)

        a = asp_df[asp_df["브랜드"] == brand]
        asp_compliance = round((a["상태"] == "정상").sum() / max(len(a), 1) * 100, 1)

        rows.append({
            "브랜드": brand,
            "매출성장률": growth_rate,
            "OOS율개선": oos_improve,
            "재고안전비율": safe_ratio,
            "ASP준수율": asp_compliance,
            "최근월매출": last_rev,
        })

    return pd.DataFrame(rows)
