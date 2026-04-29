import io
import json
import math
import os
from datetime import date
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from logic.alerts import add_urgency
from logic.demand import compute_demand, compute_period_demand
from logic.reasoning import add_reasoning
from schemas.models import AnalyzeResponse, FilterOptions, KpiSummary, ProcurementRow
from utils.excel_loader import load_excel
from utils.export import to_excel_bytes

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
):
    df, warnings = load_excel(io.BytesIO(file_bytes))

    results = []
    for _, row in df.iterrows():
        row_df = row.to_frame().T.reset_index(drop=True)

        # Period 1: machines onboarded now — uses current stock, 30-day horizon
        m1 = int(row.get("machines_override", machines_m1) or machines_m1)
        r = compute_demand(row_df, m1, 30, safety_buffer_pct, vendor_strategy)

        # Period 2: new machines onboarding at day 30
        p2 = compute_period_demand(row_df, machines_m2, 30, safety_buffer_pct, vendor_strategy)
        r["order_qty_m2"] = int(p2["order_qty_period"].iloc[0])
        r["order_by_m2"]  = str(p2["order_by_period"].iloc[0])
        r["est_cost_m2"]  = float(p2["est_cost_period"].iloc[0])

        # Period 3: new machines onboarding at day 60
        p3 = compute_period_demand(row_df, machines_m3, 60, safety_buffer_pct, vendor_strategy)
        r["order_qty_m3"] = int(p3["order_qty_period"].iloc[0])
        r["order_by_m3"]  = str(p3["order_by_period"].iloc[0])
        r["est_cost_m3"]  = float(p3["est_cost_period"].iloc[0])

        results.append(r)

    result_df = pd.concat(results, ignore_index=True)
    result_df = add_urgency(result_df, result_df["current_stock"])
    result_df = add_reasoning(result_df)
    return result_df, warnings


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
            recommended_lead_days=_safe_int(r.get("recommended_lead_days", 0)),
            recommended_unit_price=_safe_float(r.get("recommended_unit_price", 0)),
            urgency=_safe_str(r.get("urgency", "")),
            flags=_safe_str(r.get("flags", "—")),
            reason=_safe_str(r.get("reason", "")),
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
):
    contents = await file.read()
    result_df, warnings = _run_pipeline(
        contents, machines_m1, machines_m2, machines_m3, safety_buffer_pct, vendor_strategy
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
):
    contents = await file.read()
    result_df, _ = _run_pipeline(
        contents, machines_m1, machines_m2, machines_m3, safety_buffer_pct, vendor_strategy
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


# Serve built React app only in production
if os.getenv("PRODUCTION") == "true":
    dist_path = Path(__file__).parent.parent / "frontend" / "dist"
    if dist_path.exists():
        app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static")
