import pandas as pd
import math


def build_reason(row) -> str:
    """Reasoning for Period 1 — machines already onboarded, uses current stock."""
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

    if order_qty <= 0:
        if stock_cover >= 999:
            return f"No order needed. Current stock of {int(current)} units is sufficient and demand is negligible."
        return (
            f"No order needed. You have {int(current)} units in stock, which covers "
            f"{stock_cover} days of demand — well beyond the {horizon_days}-day planning horizon."
        )

    lines = []
    stock_line = f"You currently have {int(current)} units in stock"
    if incoming > 0:
        stock_line += f" with {int(incoming)} more units already on order and incoming"
    stock_line += f", which will last {stock_cover} days at the current consumption rate."
    lines.append(stock_line)

    lines.append(
        f"Over the next {horizon_days} days, {int(math.ceil(horizon_demand))} units will be consumed "
        f"({monthly:.0f} units/month). An additional {int(math.ceil(safety))} units are held as safety stock "
        f"to absorb any supplier delays or demand spikes."
    )

    net = horizon_demand + safety - current - incoming
    if net > 0:
        lines.append(
            f"After accounting for current and incoming stock, there is a shortfall of "
            f"{int(math.ceil(net))} units — rounded up to {int(order_qty)} units to meet minimum order requirements."
        )

    vendor_str = f"{vendor} (lead time: {lead_days} days)" if vendor else f"supplier (lead time: {lead_days} days)"
    if urgency == "Critical":
        if stock_cover == 0:
            lines.append(f"Stock is completely depleted. Order {int(order_qty)} units from {vendor_str} immediately — every day of delay means unmet demand.")
        else:
            lines.append(f"Stock will run out in {stock_cover} days, but {vendor_str} needs {lead_days} days to deliver. You are already in a stockout risk window — order {int(order_qty)} units today.")
    elif urgency == "High":
        lines.append(f"Stock will last only {stock_cover} days. Order {int(order_qty)} units from {vendor_str} as soon as possible to avoid a shortage.")
    elif urgency == "Medium":
        lines.append(f"Stock will last {stock_cover} days. Place an order of {int(order_qty)} units from {vendor_str} by {order_by} — this gives enough time for delivery before stock runs low.")
    else:
        lines.append(f"Stock is sufficient for now ({stock_cover} days), but an order of {int(order_qty)} units from {vendor_str} is recommended by {order_by} to cover the full planning horizon.")

    return " ".join(lines)


def build_reason_period(row, period: int) -> str:
    """
    Reasoning for Period 2 or 3 — new machines onboarding at day 30 or 60.
    No existing stock involved; purely forward-looking.
    """
    onboard_day = 30 if period == 2 else 60
    suffix = "_m2" if period == 2 else "_m3"

    consumption = row.get("consumption_per_month", 0)
    order_qty = row.get(f"order_qty{suffix}", 0)
    order_by  = row.get(f"order_by{suffix}", "—")
    lead_days = row.get("recommended_lead_days", 0)
    vendor    = row.get("recommended_vendor", "")
    vendor_str = f"{vendor} (lead time: {lead_days} days)" if vendor else f"supplier (lead time: {lead_days} days)"

    if order_qty <= 0:
        return f"No machines are onboarding at day {onboard_day}, so no order is needed for this period."

    lines = []
    lines.append(
        f"New machines are onboarding at day {onboard_day} and will immediately begin consuming this part "
        f"at a rate of {consumption:.1f} units/machine/month."
    )

    leftover = row.get("remaining_stock_used", 0)
    if leftover and leftover > 0:
        lines.append(
            f"After M1 machines consume their share, approximately {int(leftover)} units of existing stock "
            f"remain and will be used for these machines. The remaining {int(order_qty)} units still need to be procured."
        )
    else:
        lines.append(
            f"No existing stock is available for these machines — {int(order_qty)} units need to be procured fresh "
            f"to cover their first 30 days of operation plus a safety buffer."
        )

    days_to_order = max(0, onboard_day - lead_days)
    if days_to_order == 0:
        lines.append(
            f"The supplier lead time ({lead_days} days) is longer than or equal to the time until onboarding ({onboard_day} days). "
            f"Order {int(order_qty)} units from {vendor_str} immediately."
        )
    else:
        lines.append(
            f"Order {int(order_qty)} units from {vendor_str} by {order_by} — that is {days_to_order} days from today, "
            f"giving the supplier enough time to deliver before the machines arrive."
        )

    return " ".join(lines)


def add_reasoning(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["reason"]    = df.apply(build_reason, axis=1)
    df["reason_m2"] = df.apply(lambda r: build_reason_period(r, 2), axis=1)
    df["reason_m3"] = df.apply(lambda r: build_reason_period(r, 3), axis=1)
    return df
