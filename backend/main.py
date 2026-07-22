import io
import json
import os
import datetime
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from logic.indent import compute_indent
from schemas.models import AnalyzeResponse, FilterOptions, IndentRow, KpiSummary
from utils.excel_loader import load_indent_excel
from utils.export import to_excel_bytes
from utils.zoho_sync import get_zoho_stock, get_sales_qty_map

# Load .env from backend/ directory
load_dotenv(Path(__file__).parent / ".env")

app = FastAPI(title="Replenishment Indent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_DEFAULT_SALES_DAYS = 56  # 8 weeks


def _default_range() -> tuple[str, str]:
    today = date.today()
    return (today - timedelta(days=_DEFAULT_SALES_DAYS)).isoformat(), today.isoformat()


def _weeks_between(from_date: str, to_date: str) -> float:
    try:
        d0 = datetime.date.fromisoformat(from_date)
        d1 = datetime.date.fromisoformat(to_date)
        days = (d1 - d0).days
        return days / 7.0 if days >= 7 else 1.0
    except Exception:
        return _DEFAULT_SALES_DAYS / 7.0


def _run_pipeline(
    file_bytes: bytes,
    machine_count: float,
    monthly_usage_hrs: float,
    arc_weeks: float,
    sales_from: str,
    sales_to: str,
    qoh_overrides: dict | None = None,
    flf_overrides: dict | None = None,
):
    """Load the indent sheet, pull QOH + sales from Zoho, compute indents."""
    rows, warnings = load_indent_excel(file_bytes)

    qoh_map: dict[str, float] = {}
    sales_map: dict[str, float] = {}
    try:
        qoh_map = get_zoho_stock()
    except Exception as e:
        warnings.append(f"Could not fetch QOH from Zoho — treating stock as 0. ({e})")
    try:
        sales_map = get_sales_qty_map(sales_from, sales_to)
    except Exception as e:
        warnings.append(f"Could not fetch sales from Zoho — treating sales as 0. ({e})")

    weeks = _weeks_between(sales_from, sales_to)

    results = compute_indent(
        rows,
        machine_count=machine_count,
        monthly_usage_hrs=monthly_usage_hrs,
        arc_weeks=arc_weeks,
        weeks=weeks,
        qoh_map=qoh_map,
        sales_map=sales_map,
        qoh_overrides=qoh_overrides or {},
        flf_overrides=flf_overrides or {},
    )
    unmatched = [r["sku_code"] for r in results if not r["matched"]]
    return results, warnings, unmatched


def _sorted_unique(results, key):
    return sorted({(r.get(key) or "").strip() for r in results} - {""})


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    machine_count: float = Form(500.0),
    monthly_usage_hrs: float = Form(130.0),
    arc_weeks: float = Form(1.0),
    sales_from: str = Form(""),
    sales_to: str = Form(""),
    qoh_overrides: str = Form("{}"),
    flf_overrides: str = Form("{}"),
):
    contents = await file.read()
    if not sales_from or not sales_to:
        sales_from, sales_to = _default_range()

    results, warnings, unmatched = _run_pipeline(
        contents, machine_count, monthly_usage_hrs, arc_weeks, sales_from, sales_to,
        json.loads(qoh_overrides or "{}"), json.loads(flf_overrides or "{}"),
    )

    kpis = KpiSummary(
        total_skus=len(results),
        skus_needing_indent=sum(1 for r in results if r["indent_qty"] > 0),
        total_indent_qty=float(sum(r["indent_qty"] for r in results)),
        total_purchase_amount=float(sum(r["purchase_amount"] for r in results)),
        total_stock_value=float(sum(r["stock_value"] for r in results)),
        unmatched_count=len(unmatched),
    )

    return AnalyzeResponse(
        warnings=warnings,
        kpis=kpis,
        rows=[IndentRow(**r) for r in results],
        filter_options=FilterOptions(
            categories=_sorted_unique(results, "category"),
            sub_categories=_sorted_unique(results, "sub_category"),
            brands=_sorted_unique(results, "brand"),
        ),
        unmatched_skus=unmatched,
    )


@app.post("/api/export")
async def export(
    file: UploadFile = File(...),
    machine_count: float = Form(500.0),
    monthly_usage_hrs: float = Form(130.0),
    arc_weeks: float = Form(1.0),
    sales_from: str = Form(""),
    sales_to: str = Form(""),
    qoh_overrides: str = Form("{}"),
    flf_overrides: str = Form("{}"),
    filter_category: str = Form("[]"),
    filter_sub_category: str = Form("[]"),
    filter_brand: str = Form("[]"),
    needs_indent_only: bool = Form(False),
):
    contents = await file.read()
    if not sales_from or not sales_to:
        sales_from, sales_to = _default_range()

    results, _, _ = _run_pipeline(
        contents, machine_count, monthly_usage_hrs, arc_weeks, sales_from, sales_to,
        json.loads(qoh_overrides or "{}"), json.loads(flf_overrides or "{}"),
    )

    cats   = set(json.loads(filter_category))
    subs   = set(json.loads(filter_sub_category))
    brands = set(json.loads(filter_brand))
    if cats:
        results = [r for r in results if r["category"] in cats]
    if subs:
        results = [r for r in results if r["sub_category"] in subs]
    if brands:
        results = [r for r in results if r["brand"] in brands]
    if needs_indent_only:
        results = [r for r in results if r["indent_qty"] > 0]

    excel_bytes = to_excel_bytes(results)
    filename = f"replenishment_indent_{date.today().strftime('%Y%m%d')}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/zoho/stock")
async def zoho_stock():
    """Debug: fetch current stock levels from Zoho Books (READ ONLY)."""
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
