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
            f"No order needed for Month 1. You have {int(current)} units in stock"
            + (f" plus {int(incoming)} incoming" if incoming > 0 else "")
            + f", which covers {stock_cover} days of demand at the current consumption rate"
            + f" — well beyond the {horizon_days}-day planning horizon."
        )

    lines = []
    stock_line = f"You currently have {int(current)} units in stock"
    if incoming > 0:
        stock_line += f" with {int(incoming)} more units already on order and incoming"
    stock_line += f", which will last {stock_cover} days at the current consumption rate."
    lines.append(stock_line)

    gross = horizon_demand + safety
    safety_pct_display = f"{round(safety / horizon_demand * 100) if horizon_demand else 0}%"
    lines.append(
        f"Total required = {int(math.ceil(horizon_demand))} units (base, {monthly:.0f}/month) "
        f"+ {int(math.ceil(safety))} units ({safety_pct_display} safety buffer) "
        f"= {int(math.ceil(gross))} units."
    )

    net = horizon_demand + safety - current - incoming
    if net > 0:
        stock_str = f"{int(current)} in stock" + (f" + {int(incoming)} incoming" if incoming > 0 else "")
        lines.append(
            f"Available stock: {stock_str} = {int(current + incoming)} units. "
            f"Shortfall: {int(math.ceil(gross))} - {int(current + incoming)} = {int(order_qty)} units to order."
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

    machines = int(row.get(f"machines_m{period}", 0) or 0)

    if order_qty <= 0:
        if machines <= 0:
            return f"No machines are onboarding at day {onboard_day}, so no order is needed for this period."
        # Machines exist but stock is sufficient — explain why
        leftover = float(row.get(f"remaining_stock_m{period}", 0) or 0)
        monthly_needed = consumption * machines
        days_covered = round((leftover / (monthly_needed / 30)) if monthly_needed > 0 else 999)
        return (
            f"{machines} machines are onboarding at day {onboard_day} and will need "
            f"{monthly_needed:.0f} units/month. No new order is required — after earlier "
            f"machines consume their share, {int(leftover)} units of existing stock remain, "
            f"covering approximately {min(days_covered, 999)} days of demand for this batch."
        )

    monthly_demand = consumption * machines
    consumption_str = f"{consumption:.4g}"  # avoids 0.16 rounding to "0.2"
    safety_pct = float(row.get("safety_buffer_pct", 20) or 20)
    safety_units = monthly_demand * (safety_pct / 100.0)
    gross_required = monthly_demand + safety_units

    lines = []
    lines.append(
        f"{int(machines)} machines onboarding at day {onboard_day}, "
        f"each consuming {consumption_str} units/month."
    )

    # Show the calculation explicitly
    lines.append(
        f"Total required = {monthly_demand:.1f} units (base) "
        f"+ {safety_units:.1f} units ({safety_pct:.4g}% safety buffer) "
        f"= {gross_required:.1f} units."
    )

    leftover = float(row.get(f"remaining_stock_m{period}", 0) or 0)
    if leftover > 0:
        lines.append(
            f"Carry-over stock from earlier: {int(leftover)} units. "
            f"Shortfall to order: {gross_required:.1f} - {int(leftover)} = {int(order_qty)} units."
        )
    else:
        lines.append(
            f"No stock carries over — all {int(order_qty)} units need to be freshly ordered."
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
