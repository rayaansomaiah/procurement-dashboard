"""
Zoho Books integration — READ ONLY.
Fetches stock_on_hand per SKU from Zoho Books Items API (India region).
Never writes, edits, or deletes anything in Zoho.

Matching strategy:
  - Zoho stock map is keyed by the item's SKU field (e.g. NS1682, SKU1256).
  - Each Excel row has up to 6 vendor SKUs (l1_sku … l6_sku).
  - We look up every unique vendor SKU in the Zoho map and SUM the stock.
    (Same SKU appearing for multiple vendors is counted only once.)
"""

import os
import httpx
import pandas as pd
from typing import Optional

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


def _fetch_all_items(access_token: str, org_id: str) -> list[dict]:
    """Fetch all inventory items from Zoho Books (handles pagination)."""
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    items   = []
    page    = 1

    while True:
        resp = httpx.get(
            f"{ZOHO_BOOKS_BASE}/items",
            headers=headers,
            params={
                "organization_id": org_id,
                "page":            page,
                "per_page":        200,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        batch = data.get("items", [])
        items.extend(batch)

        if not data.get("page_context", {}).get("has_more_page", False):
            break
        page += 1

    return items


def get_zoho_stock() -> dict[str, float]:
    """
    Fetch all items from Zoho Books.
    Returns {sku_upper: stock_on_hand} keyed by Zoho's SKU field (uppercased).
    """
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
    items        = _fetch_all_items(access_token, org_id)

    stock_map: dict[str, float] = {}
    for item in items:
        sku = str(item.get("sku") or "").strip().upper()
        if not sku:
            continue
        stock_map[sku] = float(item.get("stock_on_hand") or 0)

    return stock_map


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
