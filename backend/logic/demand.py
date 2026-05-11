import math
import datetime
import pandas as pd


def parse_lead_time_days(lead_str) -> int:
    """Parse '15 days', '2 months', '1 week' → integer days."""
    if pd.isna(lead_str):
        return 30
    import re
    s = str(lead_str).strip().lower()
    match = re.search(r"(\d+)\s*(day|days|month|months|week|weeks)?", s)
    if match:
        n = int(match.group(1))
        unit = match.group(2) or "days"
        if "month" in unit:
            return n * 30
        if "week" in unit:
            return n * 7
        return n
    return 30


def _is_valid(val) -> bool:
    """Check if a vendor name/value is usable."""
    return bool(val and not pd.isna(val) and str(val).strip().lower() not in ("", "nan", "none"))


def _pick_vendor(row, vendor_strategy: str):
    """
    Return (vendor_name, vendor_sku, lead_days, unit_price) based on strategy.
    Supports L1–L6. All tiers now have individual lead times.
    """
    l1_days = row.get("lead_time_days_l1", 30)
    l2_days = row.get("lead_time_days_l2", l1_days)
    l3_days = row.get("lead_time_days_l3", l1_days)
    l4_days = row.get("lead_time_days_l4", l1_days)
    l5_days = row.get("lead_time_days_l5", l1_days)
    l6_days = row.get("lead_time_days_l6", l1_days)

    # Build candidate list: (name, sku, lead_days, price)
    candidates = []
    for lvl, ld in [
        ("l1", l1_days), ("l2", l2_days),
        ("l3", l3_days), ("l4", l4_days), ("l5", l5_days), ("l6", l6_days),
    ]:
        name  = row.get(f"{lvl}_vendor", "")
        sku   = row.get(f"{lvl}_sku", "")
        price = float(row.get(f"{lvl}_price", 0) or 0)
        if _is_valid(name) and price > 0:
            candidates.append((str(name).strip(), str(sku).strip(), ld, price))

    if not candidates:
        return ("", "", l1_days, 0.0)

    if vendor_strategy == "Cheapest Price":
        return min(candidates, key=lambda c: c[3])
    elif vendor_strategy == "Fastest Delivery":
        # All tiers now have lead times — compare all candidates
        return min(candidates, key=lambda c: c[2])
    else:  # Prefer L1 — always use first valid candidate (L1)
        return candidates[0]


def _round_qty(row):
    """Round net_required up to nearest pack size, respecting MOQ."""
    raw = row["net_required"]
    if raw <= 0:
        return 0
    ps = max(row.get("pack_size_val", 1), 1)
    mq = max(row.get("moq_val", 1), 1)
    return max(math.ceil(raw / ps) * ps, mq)


def compute_demand(
    df: pd.DataFrame,
    num_machines: int,
    horizon_days: int,
    safety_buffer_pct: float,
    vendor_strategy: str = "Prefer L1",
) -> pd.DataFrame:
    """
    Period 1 — machines already onboarded (Day 0).
    Accounts for current stock and incoming stock.
    horizon_days is always 30 for period 1.
    """
    df = df.copy()

    df["monthly_demand"] = df["consumption_per_month"] * num_machines
    df["horizon_demand"] = df["monthly_demand"] * (horizon_days / 30.0)

    df["lead_time_days_l1"] = df["l1_lead"].apply(parse_lead_time_days)
    df["lead_time_days_l2"] = df["l2_lead"].apply(parse_lead_time_days) if "l2_lead" in df.columns else df["lead_time_days_l1"]
    df["lead_time_days_l3"] = df["l3_lead"].apply(parse_lead_time_days) if "l3_lead" in df.columns else df["lead_time_days_l1"]
    df["lead_time_days_l4"] = df["l4_lead"].apply(parse_lead_time_days) if "l4_lead" in df.columns else df["lead_time_days_l1"]
    df["lead_time_days_l5"] = df["l5_lead"].apply(parse_lead_time_days) if "l5_lead" in df.columns else df["lead_time_days_l1"]
    df["lead_time_days_l6"] = df["l6_lead"].apply(parse_lead_time_days) if "l6_lead" in df.columns else df["lead_time_days_l1"]

    vendor_info = df.apply(lambda r: _pick_vendor(r, vendor_strategy), axis=1)
    df["recommended_vendor"]     = [v[0] for v in vendor_info]
    df["recommended_vendor_sku"] = [v[1] if v[1] and v[1] != "nan" else "" for v in vendor_info]
    df["recommended_lead_days"]  = [v[2] for v in vendor_info]
    df["recommended_unit_price"] = [v[3] for v in vendor_info]

    # Safety stock = simple percentage of horizon demand
    df["safety_stock"] = df["horizon_demand"] * (safety_buffer_pct / 100.0)

    current_stock  = df.get("current_stock",  pd.Series(0, index=df.index)).fillna(0)
    incoming_stock = df.get("incoming_stock", pd.Series(0, index=df.index)).fillna(0)
    df["net_required"] = df["horizon_demand"] + df["safety_stock"] - current_stock - incoming_stock

    moq       = df.get("moq",       pd.Series(1, index=df.index)).fillna(1).astype(float)
    pack_size = df.get("pack_size", pd.Series(1, index=df.index)).fillna(1).astype(float)
    df["pack_size_val"] = pack_size
    df["moq_val"]       = moq
    df["recommended_order_qty"] = df.apply(_round_qty, axis=1)

    df["estimated_cost"] = df["recommended_order_qty"] * df["recommended_unit_price"]

    # Stock cover days
    daily_demand = df["monthly_demand"] / 30.0
    df["stock_cover_days"] = (
        current_stock
        .where(daily_demand > 0, other=999)
        .div(daily_demand.replace(0, float("nan")))
        .fillna(999)
        .round(0)
        .astype(int)
    )

    # Order by date (latest day to place order before stock runs out)
    today = datetime.date.today()

    def calc_order_date(row):
        if row.get("recommended_order_qty", 0) <= 0:
            return "—"
        stock_cover = row.get("stock_cover_days", 0)
        lead_days   = row.get("recommended_lead_days", 0)
        if stock_cover <= lead_days:
            return today.strftime("%d-%b-%Y")
        return (today + datetime.timedelta(days=int(stock_cover - lead_days))).strftime("%d-%b-%Y")

    df["order_by_date"] = df.apply(calc_order_date, axis=1)

    return df


def compute_period_demand(
    df: pd.DataFrame,
    machines: int,
    onboard_day: int,
    safety_buffer_pct: float,
    vendor_strategy: str = "Prefer L1",
    remaining_stock: float = 0.0,
) -> pd.DataFrame:
    """
    Periods 2 & 3 — new machines onboarding at `onboard_day` (30 or 60).
    No existing stock offset; calculates 30-day demand for this batch only.
    Returns a single-row df with: order_qty_period, order_by_period, est_cost_period.
    """
    df = df.copy()

    # If no machines in this period, return zeros
    if machines <= 0:
        df["order_qty_period"] = 0
        df["order_by_period"]  = "—"
        df["est_cost_period"]  = 0.0
        return df[["order_qty_period", "order_by_period", "est_cost_period"]]

    df["lead_time_days_l1"] = df["l1_lead"].apply(parse_lead_time_days)
    df["lead_time_days_l2"] = df["l2_lead"].apply(parse_lead_time_days) if "l2_lead" in df.columns else df["lead_time_days_l1"]
    df["lead_time_days_l3"] = df["l3_lead"].apply(parse_lead_time_days) if "l3_lead" in df.columns else df["lead_time_days_l1"]
    df["lead_time_days_l4"] = df["l4_lead"].apply(parse_lead_time_days) if "l4_lead" in df.columns else df["lead_time_days_l1"]
    df["lead_time_days_l5"] = df["l5_lead"].apply(parse_lead_time_days) if "l5_lead" in df.columns else df["lead_time_days_l1"]
    df["lead_time_days_l6"] = df["l6_lead"].apply(parse_lead_time_days) if "l6_lead" in df.columns else df["lead_time_days_l1"]

    vendor_info = df.apply(lambda r: _pick_vendor(r, vendor_strategy), axis=1)
    df["recommended_vendor"]     = [v[0] for v in vendor_info]
    df["recommended_vendor_sku"] = [v[1] if v[1] and v[1] != "nan" else "" for v in vendor_info]
    df["recommended_lead_days"]  = [v[2] for v in vendor_info]
    df["recommended_unit_price"] = [v[3] for v in vendor_info]

    # 30-day demand for this new batch
    monthly = df["consumption_per_month"] * machines
    safety  = monthly * (safety_buffer_pct / 100.0)  # simple % of demand

    df["net_required"] = monthly + safety - remaining_stock  # use leftover stock from previous period

    moq       = df.get("moq",       pd.Series(1, index=df.index)).fillna(1).astype(float)
    pack_size = df.get("pack_size", pd.Series(1, index=df.index)).fillna(1).astype(float)
    df["pack_size_val"] = pack_size
    df["moq_val"]       = moq
    df["order_qty_period"] = df.apply(_round_qty, axis=1)

    df["est_cost_period"] = df["order_qty_period"] * df["recommended_unit_price"]

    # Order by date: need parts by `onboard_day`, so order (onboard_day - lead_time) days from today
    today = datetime.date.today()

    def calc_period_order_date(row):
        if row["order_qty_period"] <= 0:
            return "—"
        lead          = row["recommended_lead_days"]
        days_to_order = max(0, onboard_day - lead)
        return (today + datetime.timedelta(days=days_to_order)).strftime("%d-%b-%Y")

    df["order_by_period"] = df.apply(calc_period_order_date, axis=1)

    return df[["order_qty_period", "order_by_period", "est_cost_period"]]
