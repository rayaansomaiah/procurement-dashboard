import pandas as pd
import math
import datetime


def parse_lead_time_days(lead_str) -> int:
    """Parse lead time strings like '15 days', '60 days' into integer days."""
    if pd.isna(lead_str):
        return 30  # default
    s = str(lead_str).strip().lower()
    import re
    match = re.search(r"(\d+)", s)
    if match:
        return int(match.group(1))
    return 30


def compute_demand(
    df: pd.DataFrame,
    num_machines: int,
    horizon_days: int,
    safety_buffer_pct: float,
    vendor_strategy: str = "Prefer L1",
) -> pd.DataFrame:
    """
    Core calculation for each SKU row.

    vendor_strategy options:
      - "Prefer L1"       : Always use L1; use L2 only if L2 lead time is faster
      - "Fastest Delivery": Pick whichever vendor has the shortest lead time
      - "Cheapest Price"  : Pick whichever vendor has the lowest unit price
    """
    horizon_months = horizon_days / 30.0

    df = df.copy()

    # Monthly demand = consumption factor × machines
    df["monthly_demand"] = df["consumption_per_month"] * num_machines
    df["horizon_demand"] = df["monthly_demand"] * horizon_months

    # Parse lead times
    df["lead_time_days_l1"] = df["l1_lead"].apply(parse_lead_time_days)
    df["lead_time_days_l2"] = df["l2_lead"].apply(parse_lead_time_days)

    # Pick vendor based on strategy
    def pick_vendor(row):
        l1_name  = row.get("l1_vendor", "")
        l2_name  = row.get("l2_vendor", "")
        l1_days  = row["lead_time_days_l1"]
        l2_days  = row["lead_time_days_l2"]
        l1_price = row.get("l1_price", 0) or 0
        l2_price = row.get("l2_price", 0) or 0

        # No L2 available → always L1
        l2_available = (
            not pd.isna(l2_name)
            and str(l2_name).strip() not in ("", "nan")
        )
        if not l2_available:
            return l1_name, l1_days, l1_price

        if vendor_strategy == "Fastest Delivery":
            if l2_days < l1_days:
                return l2_name, l2_days, l2_price
            return l1_name, l1_days, l1_price

        elif vendor_strategy == "Cheapest Price":
            if l2_price < l1_price:
                return l2_name, l2_days, l2_price
            return l1_name, l1_days, l1_price

        else:  # "Prefer L1" — default: L1 unless L2 is strictly faster
            if l2_days < l1_days:
                return l2_name, l2_days, l2_price
            return l1_name, l1_days, l1_price

    vendor_info = df.apply(pick_vendor, axis=1)
    df["recommended_vendor"]    = [v[0] for v in vendor_info]
    df["recommended_lead_days"] = [v[1] for v in vendor_info]
    df["recommended_unit_price"]= [v[2] for v in vendor_info]

    # Safety stock using recommended vendor's lead time
    rec_lead_months = df["recommended_lead_days"] / 30.0
    df["safety_stock"] = df["monthly_demand"] * rec_lead_months * (safety_buffer_pct / 100.0)

    # Net required and MOQ rounding
    current_stock  = df.get("current_stock",  pd.Series(0, index=df.index)).fillna(0)
    incoming_stock = df.get("incoming_stock", pd.Series(0, index=df.index)).fillna(0)
    df["net_required"] = df["horizon_demand"] + df["safety_stock"] - current_stock - incoming_stock

    moq       = df.get("moq",       pd.Series(1, index=df.index)).fillna(1).astype(float)
    pack_size = df.get("pack_size", pd.Series(1, index=df.index)).fillna(1).astype(float)

    def round_qty(row):
        raw = row["net_required"]
        if raw <= 0:
            return 0
        ps = max(row.get("pack_size_val", 1), 1)
        mq = max(row.get("moq_val", 1), 1)
        packs   = math.ceil(raw / ps)
        rounded = packs * ps
        return max(rounded, mq)

    df["pack_size_val"] = pack_size
    df["moq_val"]       = moq
    df["recommended_order_qty"] = df.apply(round_qty, axis=1)

    # Estimated cost
    df["estimated_cost"] = df["recommended_order_qty"] * df["recommended_unit_price"]

    # Stock cover in days
    daily_demand = df["monthly_demand"] / 30.0
    df["stock_cover_days"] = (
        current_stock
        .where(daily_demand > 0, other=999)
        .div(daily_demand.replace(0, float("nan")))
        .fillna(999)
        .round(0)
        .astype(int)
    )

    # Order by date — latest date to place the order and still receive before stockout
    today = datetime.date.today()

    def calc_order_date(row):
        if row.get("recommended_order_qty", 0) <= 0:
            return "—"
        stock_cover = row.get("stock_cover_days", 0)
        lead_days   = row.get("recommended_lead_days", 0)
        if stock_cover <= lead_days:
            return today.strftime("%d-%b-%Y")
        days_until_order = int(stock_cover - lead_days)
        return (today + datetime.timedelta(days=days_until_order)).strftime("%d-%b-%Y")

    df["order_by_date"] = df.apply(calc_order_date, axis=1)

    return df
