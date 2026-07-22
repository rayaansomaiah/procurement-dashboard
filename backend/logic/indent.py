"""
Replenishment indent calculation.

Blends two demand signals per SKU and compares against on-hand stock:

  Sales-based projection  = (sales_qty / weeks) * ARC
  Wallet-based projection = wallet_qty * (machine_count * applicability%)
                            * (monthly_usage_hrs / consumption_hrs) * ARC / 4
  Effective demand        = ROUNDUP( sales_proj*(1-FLF) + wallet_proj*FLF )
  Indent                  = max(effective_demand - QOH, 0)

All global levers (machine_count, monthly_usage_hrs, ARC, sales period length)
are passed in; per-SKU master values come from the uploaded sheet; QOH and sales
come from Zoho. QOH and FLF can be overridden per SKU from the UI.
"""

import math


def _clamp_flf(v: float) -> float:
    if v < 0:
        return 0.0
    if v > 1:
        return 1.0
    return v


def compute_indent(
    rows: list[dict],
    *,
    machine_count: float,
    monthly_usage_hrs: float,
    arc_weeks: float,
    weeks: float,
    qoh_map: dict[str, float],
    sales_map: dict[str, float],
    qoh_overrides: dict[str, float] | None = None,
    flf_overrides: dict[str, float] | None = None,
) -> list[dict]:
    qoh_overrides = qoh_overrides or {}
    flf_overrides = flf_overrides or {}
    weeks = weeks if weeks and weeks > 0 else 1.0

    results: list[dict] = []
    for row in rows:
        sku = row["sku_code"]
        sku_u = sku.strip().upper()
        matched = sku_u in qoh_map

        # --- QOH (override > Zoho > 0) ---
        if sku in qoh_overrides:
            qoh = float(qoh_overrides[sku])
        else:
            qoh = float(qoh_map.get(sku_u, 0.0))

        # --- Sales-based projection ---
        sales_qty = float(sales_map.get(sku_u, 0.0))
        sales_per_week = sales_qty / weeks
        sales_proj = sales_per_week * arc_weeks

        # --- Wallet-based projection ---
        applicability = float(row.get("applicability", 1.0))
        mdp_cdp = machine_count * applicability
        cons_hrs = float(row.get("consumption_hrs", 0.0))
        consumption_load = (monthly_usage_hrs / cons_hrs) if cons_hrs > 0 else 0.0
        wallet_qty = float(row.get("wallet_qty", 0.0))
        demand_planning = wallet_qty * mdp_cdp * consumption_load
        wallet_proj = demand_planning * arc_weeks / 4.0

        # --- Blend (FLF: override > master) ---
        flf = _clamp_flf(float(flf_overrides[sku]) if sku in flf_overrides
                         else float(row.get("flf", 0.0)))
        effective_demand = math.ceil(sales_proj * (1 - flf) + wallet_proj * flf)

        # --- Indent + money ---
        indent_qty = max(effective_demand - qoh, 0)
        indent_qty = int(math.ceil(indent_qty)) if indent_qty > 0 else 0
        price = float(row.get("purchase_price", 0.0))
        purchase_amount = indent_qty * price
        stock_value = qoh * price

        results.append({
            "sku_code":         sku,
            "item":             row.get("item", sku),
            "category":         row.get("category", ""),
            "sub_category":     row.get("sub_category", ""),
            "brand":            row.get("brand", ""),
            "qoh":              round(qoh, 2),
            "purchase_price":   round(price, 2),
            "prev_sales_qty":   round(sales_qty, 2),
            "sales_per_week":   round(sales_per_week, 2),
            "arc":              arc_weeks,
            "sales_proj":       round(sales_proj, 2),
            "mdp_cdp":          round(mdp_cdp, 2),
            "applicability":    round(applicability, 4),
            "consumption_hrs":  round(cons_hrs, 2),
            "consumption_load": round(consumption_load, 4),
            "wallet_proj":      round(wallet_proj, 2),
            "flf":              round(flf, 3),
            "effective_demand": int(effective_demand),
            "indent_qty":       indent_qty,
            "purchase_amount":  round(purchase_amount, 2),
            "stock_value":      round(stock_value, 2),
            "matched":          matched,
        })

    return results
