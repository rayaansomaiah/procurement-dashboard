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
  - The Indent sheet's SKU column matches Zoho's `sku` field directly
    (same NS####/SKU#### namespace), so matching is a plain SKU→SKU lookup.
    Matching itself lives in logic/indent.py; this module only fetches.
"""

import os
import time
import httpx

# ---------------------------------------------------------------------------
# Simple in-memory cache — avoids re-fetching all 3,000+ Zoho items on every
# sync click.  Cache expires after CACHE_TTL_SECONDS (default 10 minutes).
# ---------------------------------------------------------------------------
_CACHE_TTL_SECONDS = 600
_cache_stock_map: dict[str, float] | None = None
_cache_timestamp: float = 0.0

# Sales cache keyed by (from_date, to_date) -> (sales_map, timestamp)
_cache_sales: dict[tuple[str, str], tuple[dict, float]] = {}

ZOHO_TOKEN_URL  = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_BOOKS_BASE = "https://www.zohoapis.in/books/v3"

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


_PAGE_WAVE = 6  # inventory pages fetched concurrently per wave


def _fetch_inv_page(access_token: str, org_id: str, page: int) -> tuple[list[dict], bool]:
    """Fetch one inventory-summary page → (item_details, has_more_page)."""
    resp = httpx.get(
        f"{ZOHO_BOOKS_BASE}/reports/inventorysummary",
        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
        params={"organization_id": org_id, "page": page, "per_page": 200},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", 0) != 0:
        raise ValueError(f"Zoho inventory report error: {data.get('message')}")
    rows: list[dict] = []
    for group in data.get("inventory", []):
        rows.extend(group.get("item_details", []))
    has_more = bool(data.get("page_context", {}).get("has_more_page", False))
    return rows, has_more


def _fetch_inventory_summary(access_token: str, org_id: str) -> list[dict]:
    """
    Fetch stock via the Inventory Summary report, paginating in concurrent
    waves (~6 pages at a time) so the ~3,500-item fleet loads in seconds.

    NOTE: We use reports/inventorysummary instead of the /items endpoint
    because the API user is provisioned for Zoho Books reports/sales but not
    the Items module (the /items endpoint returns HTTP 401 code 57 for this
    account, while reports work fine). The report's `quantity_available` field
    is the live on-hand stock and is independent of the report's date filter.
    """
    from concurrent.futures import ThreadPoolExecutor

    rows: list[dict] = []
    first_rows, has_more = _fetch_inv_page(access_token, org_id, 1)
    rows.extend(first_rows)

    next_page = 2
    with ThreadPoolExecutor(max_workers=_PAGE_WAVE) as pool:
        while has_more:
            batch = list(range(next_page, next_page + _PAGE_WAVE))
            results = list(pool.map(
                lambda p: _fetch_inv_page(access_token, org_id, p), batch
            ))
            for page_rows, _ in results:
                rows.extend(page_rows)
            # Continue only if the last page in the wave still had more (and
            # returned data). Overshot pages return empty + has_more=False.
            last_rows, last_more = results[-1]
            has_more = last_more and bool(last_rows)
            next_page += _PAGE_WAVE

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
    Fetch Sales by Item report from Zoho Books for a date range (paginated).
    Returns {sku_upper: {qty_sold, avg_price, total_amount}}.
    Cached per date range for CACHE_TTL_SECONDS.
    """
    key = (from_date, to_date)
    cached = _cache_sales.get(key)
    if cached and (time.time() - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]

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

    sales_map: dict[str, dict] = {}
    page = 1
    while True:
        resp = httpx.get(
            f"{ZOHO_BOOKS_BASE}/reports/salesbyitem",
            headers=headers,
            params={
                "organization_id": org_id,
                "from_date":       from_date,
                "to_date":         to_date,
                "page":            page,
                "per_page":        200,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code", 0) != 0:
            raise ValueError(f"Zoho sales report error: {data.get('message')}")

        for item in data.get("sales", []):
            sku = str((item.get("item") or {}).get("sku") or "").strip().upper()
            if not sku:
                continue
            sales_map[sku] = {
                "qty_sold":     float(item.get("quantity_sold") or 0),
                "avg_price":    float(item.get("average_price") or 0),
                "total_amount": float(item.get("amount") or 0),
            }

        if not data.get("page_context", {}).get("has_more_page", False):
            break
        page += 1

    _cache_sales[key] = (sales_map, time.time())
    return sales_map


def get_sales_qty_map(from_date: str, to_date: str) -> dict[str, float]:
    """Convenience: {sku_upper: qty_sold} over the date range (for indent calc)."""
    return {sku: v["qty_sold"] for sku, v in get_sales_by_item(from_date, to_date).items()}
