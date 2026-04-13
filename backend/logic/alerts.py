import pandas as pd


URGENCY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "No Action": 4}


def classify_urgency(row) -> str:
    """
    Critical  — stock covers less than lead time (can't reorder in time)
    High      — stock covers < 30 days
    Medium    — order is needed within the horizon
    Low       — order recommended but not time-sensitive
    No Action — stock > 3× horizon demand
    """
    stock_cover = row.get("stock_cover_days", 0)
    lead_days = row.get("recommended_lead_days", 30)
    order_qty = row.get("recommended_order_qty", 0)
    horizon_demand = row.get("horizon_demand", 0)
    current_stock = row.get("current_stock", 0)

    if order_qty <= 0:
        return "No Action"

    if stock_cover < lead_days:
        return "Critical"
    elif stock_cover < 30:
        return "High"
    elif order_qty > 0:
        if stock_cover < 60:
            return "Medium"
        return "Low"
    return "No Action"


def classify_flags(row) -> list:
    flags = []
    stock_cover = row.get("stock_cover_days", 999)
    lead_days = row.get("recommended_lead_days", 30)
    current_stock = row.get("current_stock", 0)
    horizon_demand = row.get("horizon_demand", 0)

    if stock_cover < lead_days:
        flags.append("Stockout Risk")
    if current_stock > horizon_demand * 3 and horizon_demand > 0:
        flags.append("Overstock")
    if row.get("recommended_order_qty", 0) == 0 and current_stock == 0:
        flags.append("Zero Stock")

    return flags


def add_urgency(df: pd.DataFrame, current_stock_series: pd.Series) -> pd.DataFrame:
    df = df.copy()
    df["current_stock"] = current_stock_series.fillna(0)
    df["urgency"] = df.apply(classify_urgency, axis=1)
    df["flags"] = df.apply(lambda r: ", ".join(classify_flags(r)) or "-", axis=1)
    return df
