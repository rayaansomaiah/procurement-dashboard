import io
import json
import math
import os
import datetime
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from logic.alerts import add_urgency
from logic.demand import parse_lead_time_days, _pick_vendor
from logic.reasoning import add_reasoning
from schemas.models import AnalyzeResponse, FilterOptions, KpiSummary, ProcurementRow
from utils.excel_loader import load_excel
from utils.export import to_excel_bytes
from utils.zoho_sync import get_zoho_stock, match_stock_to_parts

# Load .env from backend/ directory
load_dotenv(Path(__file__).parent / ".env")

app = FastAPI(title="Procurement Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_pipeline(
    file_bytes: bytes,
    machines_m1: int,
    machines_m2: int,
    machines_m3: int,
    safety_buffer_pct: float,
    vendor_strategy: str,
    stock_overrides: dict | None = None,
):
    """
    Fully vectorised pipeline — processes all rows in one pass instead of
    looping 430 times × 3 periods.  ~10-20× faster than the old loop.
    """
    df, warnings = load_excel(io.BytesIO(file_bytes))

    # Apply per-SKU stock overrides entered in the UI
    if stock_overrides:
        for sku, stock_val in stock_overrides.items():
            mask = df["sku_code"].astype(str) == str(sku)
            if mask.any():
                df.loc[mask, "current_stock"] = float(stock_val)

    # --- Effective M1 per row (respects machines_override column if present) ---
    if "machines_override" in df.columns:
        raw_ov = pd.to_numeric(df["machines_override"], errors="coerce")
        eff_m1 = raw_ov.where(raw_ov > 0, float(machines_m1)).fillna(float(machines_m1))
    else:
        eff_m1 = pd.Series(float(machines_m1), index=df.index)

    # --- Parse lead times for all tiers (one pass each, string→int) ---
    df["lead_time_days_l1"] = df["l1_lead"].apply(parse_lead_time_days)
    for lvl in ["l2", "l3", "l4", "l5", "l6"]:
        col = f"{lvl}_lead"
        df[f"lead_time_days_{lvl}"] = (
            df[col].apply(parse_lead_time_days) if col in df.columns
            else df["lead_time_days_l1"]
        )

    # --- Vendor selection — single apply pass, reused for all 3 periods ---
    vendor_info = df.apply(lambda r: _pick_vendor(r, vendor_strategy), axis=1)
    df["recommended_vendor"]     = [v[0] for v in vendor_info]
    df["recommended_vendor_sku"] = [v[1] if v[1] and v[1] != "nan" else "" for v in vendor_info]
    df["recommended_lead_days"]  = [v[2] for v in vendor_info]
    df["recommended_unit_price"] = [float(v[3]) for v in vendor_info]

    current_stock  = df["current_stock"].fillna(0).astype(float)
    incoming_stock = df["incoming_stock"].fillna(0).astype(float)
    moq       = df["moq"].fillna(1).clip(lower=1).astype(float)
    pack_size = df["pack_size"].fillna(1).clip(lower=1).astype(float)
    unit_price = df["recommended_unit_price"]
    lead_days  = pd.to_numeric(df["recommended_lead_days"], errors="coerce").fillna(0).astype(int)
    buf = safety_buffer_pct / 100.0

    def _qty_vec(net_series: pd.Series) -> pd.Series:
        """Vectorised round-up to pack size, respecting MOQ. Zero if net ≤ 0."""
        raw = net_series.astype(float).values
        ps  = pack_size.values
        mq  = moq.values
        qty = np.where(raw <= 0, 0, np.maximum(np.ceil(raw / ps) * ps, mq))
        return pd.Series(qty.astype(int), index=net_series.index)

    today = datetime.date.today()

    def _order_dates(qty_s, cover_s, lead_s):
        out = []
        for qty, cover, lead in zip(qty_s, cover_s, lead_s):
            if qty <= 0:
                out.append("—")
            elif cover <= lead:
                out.append(today.strftime("%d-%b-%Y"))
            else:
                out.append((today + datetime.timedelta(days=int(cover - lead))).strftime("%d-%b-%Y"))
        return out

    # ── Period 1 ────────────────────────────────────────────────────────────
    df["monthly_demand"] = df["consumption_per_month"] * eff_m1
    df["horizon_demand"] = df["monthly_demand"]          # 30-day window
    df["safety_stock"]   = df["horizon_demand"] * buf
    net_m1 = df["horizon_demand"] + df["safety_stock"] - current_stock - incoming_stock
    df["net_required"]          = net_m1                 # kept for alerts compat
    df["recommended_order_qty"] = _qty_vec(net_m1)
    df["estimated_cost"]        = df["recommended_order_qty"] * unit_price

    daily = df["monthly_demand"] / 30.0
    cover_arr = np.where(daily > 0, current_stock / daily, 999)
    df["stock_cover_days"] = np.minimum(cover_arr, 999).astype(int)

    df["order_by_date"] = _order_dates(
        df["recommended_order_qty"], df["stock_cover_days"], lead_days
    )

    remaining_m1 = (current_stock + incoming_stock - df["horizon_demand"]).clip(lower=0)
    df["remaining_stock_m2"] = remaining_m1
    df["machines_m2"] = machines_m2           # stored for reasoning
    df["machines_m3"] = machines_m3           # stored for reasoning
    df["safety_buffer_pct"] = safety_buffer_pct  # stored for reasoning

    # ── Period 2 ────────────────────────────────────────────────────────────
    if machines_m2 > 0:
        m2_monthly = df["consumption_per_month"] * machines_m2
        net_m2 = m2_monthly * (1.0 + buf) - remaining_m1
        df["order_qty_m2"] = _qty_vec(net_m2)
        df["est_cost_m2"]  = df["order_qty_m2"] * unit_price
        days_m2 = (30 - lead_days).clip(lower=0)
        df["order_by_m2"] = [
            "—" if q <= 0 else
            (today + datetime.timedelta(days=int(d))).strftime("%d-%b-%Y")
            for q, d in zip(df["order_qty_m2"], days_m2)
        ]
    else:
        df["order_qty_m2"] = 0
        df["order_by_m2"]  = "—"
        df["est_cost_m2"]  = 0.0

    remaining_m2 = (remaining_m1 - df["consumption_per_month"] * machines_m2).clip(lower=0)
    df["remaining_stock_m3"] = remaining_m2

    # ── Period 3 ────────────────────────────────────────────────────────────
    if machines_m3 > 0:
        m3_monthly = df["consumption_per_month"] * machines_m3
        net_m3 = m3_monthly * (1.0 + buf) - remaining_m2
        df["order_qty_m3"] = _qty_vec(net_m3)
        df["est_cost_m3"]  = df["order_qty_m3"] * unit_price
        days_m3 = (60 - lead_days).clip(lower=0)
        df["order_by_m3"] = [
            "—" if q <= 0 else
            (today + datetime.timedelta(days=int(d))).strftime("%d-%b-%Y")
            for q, d in zip(df["order_qty_m3"], days_m3)
        ]
    else:
        df["order_qty_m3"] = 0
        df["order_by_m3"]  = "—"
        df["est_cost_m3"]  = 0.0

    df = add_urgency(df, df["current_stock"])
    df = add_reasoning(df)
    return df, warnings


def _safe_int(v):
    try:
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            return 0
        return int(v)
    except Exception:
        return 0


def _safe_float(v):
    try:
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def _safe_str(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return str(v).strip()


def _df_to_rows(df: pd.DataFrame):
    rows = []
    for _, r in df.iterrows():
        rows.append(ProcurementRow(
            sku_code=_safe_str(r.get("sku_code", "")),
            description=_safe_str(r.get("description", "")),
            category=_safe_str(r.get("category", "")),
            monthly_demand=_safe_float(r.get("monthly_demand", 0)),
            current_stock=_safe_int(r.get("current_stock", 0)),
            stock_cover_days=_safe_int(r.get("stock_cover_days", 0)),
            recommended_order_qty=_safe_int(r.get("recommended_order_qty", 0)),
            order_by_date=_safe_str(r.get("order_by_date", "—")),
            estimated_cost=_safe_float(r.get("estimated_cost", 0)),
            order_qty_m2=_safe_int(r.get("order_qty_m2", 0)),
            order_by_m2=_safe_str(r.get("order_by_m2", "—")),
            est_cost_m2=_safe_float(r.get("est_cost_m2", 0)),
            order_qty_m3=_safe_int(r.get("order_qty_m3", 0)),
            order_by_m3=_safe_str(r.get("order_by_m3", "—")),
            est_cost_m3=_safe_float(r.get("est_cost_m3", 0)),
            recommended_vendor=_safe_str(r.get("recommended_vendor", "")),
            recommended_vendor_sku=_safe_str(r.get("recommended_vendor_sku", "")),
            recommended_lead_days=_safe_int(r.get("recommended_lead_days", 0)),
            recommended_unit_price=_safe_float(r.get("recommended_unit_price", 0)),
            urgency=_safe_str(r.get("urgency", "")),
            flags=_safe_str(r.get("flags", "—")),
            reason=_safe_str(r.get("reason", "")),
            reason_m2=_safe_str(r.get("reason_m2", "")),
            reason_m3=_safe_str(r.get("reason_m3", "")),
        ))
    return rows


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    machines_m1: int = Form(0),
    machines_m2: int = Form(0),
    machines_m3: int = Form(0),
    safety_buffer_pct: float = Form(20.0),
    vendor_strategy: str = Form("Prefer L1"),
    stock_overrides: str = Form("{}"),
):
    contents = await file.read()
    overrides = json.loads(stock_overrides) if stock_overrides else {}
    result_df, warnings = _run_pipeline(
        contents, machines_m1, machines_m2, machines_m3, safety_buffer_pct, vendor_strategy, overrides
    )

    kpis = KpiSummary(
        total_skus=len(result_df),
        critical=int((result_df["urgency"] == "Critical").sum()),
        high=int((result_df["urgency"] == "High").sum()),
        action_needed=int((result_df["recommended_order_qty"] > 0).sum()),
        est_total_spend_m1=_safe_float(result_df["estimated_cost"].sum()),
        est_total_spend_m2=_safe_float(result_df["est_cost_m2"].sum()),
        est_total_spend_m3=_safe_float(result_df["est_cost_m3"].sum()),
    )

    urgency_order = ["Critical", "High", "Medium", "Low", "No Action"]
    present = result_df["urgency"].dropna().unique().tolist()
    urgency_levels = [u for u in urgency_order if u in present]

    categories = sorted(set(result_df["category"].dropna().str.strip().tolist()))
    categories = [c for c in categories if c]
    vendors = sorted(set(result_df["recommended_vendor"].dropna().str.strip().tolist()))
    vendors = [v for v in vendors if v]

    return AnalyzeResponse(
        warnings=warnings,
        kpis=kpis,
        rows=_df_to_rows(result_df),
        filter_options=FilterOptions(
            urgency_levels=urgency_levels,
            categories=categories,
            vendors=vendors,
        ),
    )


@app.post("/api/export")
async def export(
    file: UploadFile = File(...),
    machines_m1: int = Form(0),
    machines_m2: int = Form(0),
    machines_m3: int = Form(0),
    safety_buffer_pct: float = Form(20.0),
    vendor_strategy: str = Form("Prefer L1"),
    filter_urgency: str = Form("[]"),
    filter_category: str = Form("[]"),
    filter_vendor: str = Form("[]"),
    action_only: bool = Form(False),
    stock_overrides: str = Form("{}"),
):
    contents = await file.read()
    overrides = json.loads(stock_overrides) if stock_overrides else {}
    result_df, _ = _run_pipeline(
        contents, machines_m1, machines_m2, machines_m3, safety_buffer_pct, vendor_strategy, overrides
    )

    urgencies  = json.loads(filter_urgency)
    categories = json.loads(filter_category)
    vendors    = json.loads(filter_vendor)

    if urgencies:
        result_df = result_df[result_df["urgency"].isin(urgencies)]
    if categories:
        result_df = result_df[result_df["category"].isin(categories)]
    if vendors:
        result_df = result_df[result_df["recommended_vendor"].isin(vendors)]
    if action_only:
        result_df = result_df[result_df["recommended_order_qty"] > 0]

    excel_bytes = to_excel_bytes(result_df)
    filename = f"procurement_plan_{date.today().strftime('%Y%m%d')}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/zoho/stock")
async def zoho_stock():
    """
    Fetch current stock levels from Zoho Books (READ ONLY).
    Returns {sku: stock_on_hand} for all items.
    """
    try:
        stock_map = get_zoho_stock()
        return {"status": "ok", "count": len(stock_map), "stock": stock_map}
    except Exception as e:
        return {"status": "error", "message": str(e), "stock": {}}


# Serve built React app only in production
if os.getenv("PRODUCTION") == "true":
    dist_path = Path(__file__).parent.parent / "frontend" / "dist"
    if dist_path.exists():
        app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static")
