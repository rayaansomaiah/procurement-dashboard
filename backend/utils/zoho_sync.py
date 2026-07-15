"""
Zoho Books integration — READ ONLY.
Fetches current stock and sales history per SKU from Zoho Books (India region).
Never writes, edits, or deletes anything in Zoho.

Data sources (both are Reports, which the API user is authorized for):
  - Stock:  reports/inventorysummary  → quantity_available per SKU
  - Sales:  reports/salesbyitem       → quantity_sold + average_price per SKU
  (The /items endpoint is NOT used — this API user gets 401/code 57 on it,
   but reports work. quantity_available is the live on-hand figure.)

Matching strategy:
  - Zoho maps are keyed by the item's SKU field (e.g. NS1682, SKU1256).
  - Each Excel row has up to 6 vendor SKUs (l1_sku … l6_sku).
  - We look up every unique vendor SKU and SUM across matches.
    (Same SKU appearing for multiple vendors is counted only once.)
"""

import os
import time
import httpx
import pandas as pd
from typing import Optional

# ---------------------------------------------------------------------------
# Simple in-memory cache — avoids re-fetching all 3,000+ Zoho items on every
# sync click.  Cache expires after CACHE_TTL_SECONDS (default 10 minutes).
# ---------------------------------------------------------------------------
_CACHE_TTL_SECONDS = 600
_cache_stock_map: dict[str, float] | None = None
_cache_timestamp: float = 0.0

ZOHO_TOKEN_URL  = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_BOOKS_BASE = "https://www.zohoapis.in/books/v3"

# All vendor SKU columns present in the normalised DataFrame
_SKU_COLS = ["l1_sku", "l2_sku", "l3_sku", "l4_sku", "l5_sku", "l6_sku"]


def _get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Exchange refresh token for a short-lived access token."""
    resp = httpx.post(
        ZOHO_TOKEN_URL,
        data={
            "client_id":     client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type":    "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        raise ValueError(f"Zoho token error: {data}")
    return data["access_token"]


def _fetch_inventory_summary(access_token: str, org_id: str) -> list[dict]:
    """
    Fetch stock via the Inventory Summary report (handles pagination).

    NOTE: We use reports/inventorysummary instead of the /items endpoint
    because the API user is provisioned for Zoho Books reports/sales but not
    the Items module (the /items endpoint returns HTTP 401 code 57 for this
    account, while reports work fine). The report's `quantity_available` field
    is the live on-hand stock and is independent of the report's date filter.
    """
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    rows    = []
    page    = 1

    while True:
        resp = httpx.get(
            f"{ZOHO_BOOKS_BASE}/reports/inventorysummary",
            headers=headers,
            params={
                "organization_id": org_id,
                "page":            page,
                "per_page":        200,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # Response shape: {"inventory": [{"item_details": [ {...}, ... ]}], ...}
        for group in data.get("inventory", []):
            rows.extend(group.get("item_details", []))

        if not data.get("page_context", {}).get("has_more_page", False):
            break
        page += 1

    return rows


def get_zoho_stock() -> dict[str, float]:
    """
    Fetch current stock from Zoho Books via the Inventory Summary report.
    Returns {sku_upper: quantity_available} keyed by Zoho's SKU field (uppercased).
    Result is cached for CACHE_TTL_SECONDS to avoid redundant API calls.
    """
    global _cache_stock_map, _cache_timestamp

    if _cache_stock_map is not None and (time.time() - _cache_timestamp) < _CACHE_TTL_SECONDS:
        return _cache_stock_map

    client_id     = os.getenv("ZOHO_CLIENT_ID",     "")
    client_secret = os.getenv("ZOHO_CLIENT_SECRET", "")
    refresh_token = os.getenv("ZOHO_REFRESH_TOKEN", "")
    org_id        = os.getenv("ZOHO_ORG_ID",        "")

    if not all([client_id, client_secret, refresh_token, org_id]):
        raise ValueError(
            "Zoho credentials missing. Make sure ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, "
            "ZOHO_REFRESH_TOKEN and ZOHO_ORG_ID are set in your .env file."
        )

    access_token = _get_access_token(client_id, client_secret, refresh_token)
    items        = _fetch_inventory_summary(access_token, org_id)

    stock_map: dict[str, float] = {}
    for item in items:
        sku = str(item.get("sku") or "").strip().upper()
        if not sku:
            continue
        stock_map[sku] = float(item.get("quantity_available") or 0)

    _cache_stock_map = stock_map
    _cache_timestamp = time.time()
    return stock_map


def get_sales_by_item(from_date: str, to_date: str) -> dict[str, dict]:
    """
    Fetch Sales by Item report from Zoho Books for a date range.
    Returns {sku_upper: {qty_sold, avg_price, total_amount}}.
    """
    client_id     = os.getenv("ZOHO_CLIENT_ID",     "")
    client_secret = os.getenv("ZOHO_CLIENT_SECRET", "")
    refresh_token = os.getenv("ZOHO_REFRESH_TOKEN", "")
    org_id        = os.getenv("ZOHO_ORG_ID",        "")

    if not all([client_id, client_secret, refresh_token, org_id]):
        raise ValueError(
            "Zoho credentials missing. Make sure ZOHO_REFRESH_TOKEN is set in .env."
        )

    access_token = _get_access_token(client_id, client_secret, refresh_token)
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

    resp = httpx.get(
        f"{ZOHO_BOOKS_BASE}/reports/salesbyitem",
        headers=headers,
        params={
            "organization_id": org_id,
            "from_date":       from_date,
            "to_date":         to_date,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code", 0) != 0:
        raise ValueError(f"Zoho sales report error: {data.get('message')}")

    sales_map: dict[str, dict] = {}
    for item in data.get("sales", []):
        sku = str((item.get("item") or {}).get("sku") or "").strip().upper()
        if not sku:
            continue
        sales_map[sku] = {
            "qty_sold":     float(item.get("quantity_sold") or 0),
            "avg_price":    float(item.get("average_price") or 0),
            "total_amount": float(item.get("amount") or 0),
        }

    return sales_map


def match_sales_to_parts(
    df: pd.DataFrame,
    sales_map: dict[str, dict],
) -> dict[str, Optional[dict]]:
    """
    For each row in df, collect all vendor SKUs (l1_sku … l6_sku), look each
    up in sales_map, and SUM qty_sold / average the avg_price across matches.
    Returns {sku_code: {qty_sold, avg_price}} — None if no match found.
    """
    result: dict[str, Optional[dict]] = {}

    for _, row in df.iterrows():
        part_id = str(row.get("sku_code", ""))

        vendor_skus: set[str] = set()
        for col in _SKU_COLS:
            val = str(row.get(col, "") or "").strip().upper()
            if val and val not in ("NAN", "NONE", ""):
                vendor_skus.add(val)

        matched = [sales_map[vsku] for vsku in vendor_skus if vsku in sales_map]
        if not matched:
            result[part_id] = None
            continue

        total_qty    = sum(m["qty_sold"] for m in matched)
        total_amount = sum(m["total_amount"] for m in matched)
        avg_price    = total_amount / total_qty if total_qty > 0 else 0.0

        result[part_id] = {
            "qty_sold":  total_qty,
            "avg_price": round(avg_price, 2),
        }

    return result


def match_stock_to_parts(
    df: pd.DataFrame,
    stock_map: dict[str, float],
) -> dict[str, Optional[float]]:
    """
    For each row in df, collect all vendor SKUs (l1_sku … l6_sku), look each
    up in stock_map, and SUM the stock_on_hand values from unique matches.

    Returns {sku_code: total_stock} — None if no vendor SKU matched Zoho.
    """
    result: dict[str, Optional[float]] = {}

    for _, row in df.iterrows():
        part_id = str(row.get("sku_code", ""))

        # Gather unique, non-empty vendor SKUs for this part
        vendor_skus: set[str] = set()
        for col in _SKU_COLS:
            val = str(row.get(col, "") or "").strip().upper()
            if val and val not in ("NAN", "NONE", ""):
                vendor_skus.add(val)

        # Sum stock from every Zoho SKU that matches
        total: Optional[float] = None
        for vsku in vendor_skus:
            if vsku in stock_map:
                total = (total or 0.0) + stock_map[vsku]

        result[part_id] = total  # None = no match found

    return result
