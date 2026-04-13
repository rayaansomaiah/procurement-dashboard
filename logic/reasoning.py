import pandas as pd
import math


def build_reason(row) -> str:
    monthly = row.get("monthly_demand", 0)
    horizon_demand = row.get("horizon_demand", 0)
    safety = row.get("safety_stock", 0)
    current = row.get("current_stock", 0)
    incoming = row.get("incoming_stock", 0)
    order_qty = row.get("recommended_order_qty", 0)
    lead_days = row.get("recommended_lead_days", 0)
    vendor = row.get("recommended_vendor", "")
    urgency = row.get("urgency", "")
    stock_cover = row.get("stock_cover_days", 0)
    horizon_days = round(horizon_demand / monthly * 30) if monthly > 0 else 30
    order_by = row.get("order_by_date", "")

    daily_demand = monthly / 30.0

    # --- No Action ---
    if order_qty <= 0:
        if stock_cover >= 999:
            return (
                f"No order needed. Current stock of {int(current)} units is sufficient "
                f"and demand is negligible."
            )
        return (
            f"No order needed. You have {int(current)} units in stock, which covers "
            f"{stock_cover} days of demand. This is well beyond the {horizon_days}-day planning horizon."
        )

    # --- Build the story ---
    lines = []

    # 1. Situation
    stock_line = f"You currently have {int(current)} units in stock"
    if incoming > 0:
        stock_line += f" with {int(incoming)} more units already on order and incoming"
    stock_line += f", which will last {stock_cover} days at the current consumption rate."
    lines.append(stock_line)

    # 2. What's needed
    lines.append(
        f"Over the next {horizon_days} days, {int(math.ceil(horizon_demand))} units will be consumed "
        f"({monthly:.0f} units/month). An additional {int(math.ceil(safety))} units are held as safety stock "
        f"to absorb any supplier delays or demand spikes."
    )

    # 3. The gap
    net = horizon_demand + safety - current - incoming
    if net > 0:
        lines.append(
            f"After accounting for current and incoming stock, there is a shortfall of "
            f"{int(math.ceil(net))} units — rounded up to {int(order_qty)} units to meet "
            f"minimum order requirements."
        )

    # 4. Vendor and timing
    vendor_str = f"{vendor} (lead time: {lead_days} days)" if vendor else f"supplier (lead time: {lead_days} days)"
    if urgency == "Critical":
        if stock_cover == 0:
            lines.append(
                f"Stock is completely depleted. Order {int(order_qty)} units from {vendor_str} immediately — "
                f"every day of delay means unmet demand."
            )
        else:
            lines.append(
                f"Stock will run out in {stock_cover} days, but {vendor_str} needs {lead_days} days to deliver. "
                f"You are already in a stockout risk window — order {int(order_qty)} units today."
            )
    elif urgency == "High":
        lines.append(
            f"Stock will last only {stock_cover} days. Order {int(order_qty)} units from {vendor_str} "
            f"as soon as possible to avoid a shortage."
        )
    elif urgency == "Medium":
        lines.append(
            f"Stock will last {stock_cover} days. Place an order of {int(order_qty)} units from {vendor_str} "
            f"by {order_by} — this gives enough time for delivery before stock runs low."
        )
    else:
        lines.append(
            f"Stock is sufficient for now ({stock_cover} days), but an order of {int(order_qty)} units "
            f"from {vendor_str} is recommended by {order_by} to cover the full planning horizon."
        )

    return " ".join(lines)


def add_reasoning(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["reason"] = df.apply(build_reason, axis=1)
    return df
