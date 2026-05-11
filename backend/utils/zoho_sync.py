"""
Zoho Books integration — READ ONLY.
Fetches stock_on_hand per SKU from Zoho Books Items API (India region).
Never writes, edits, or deletes anything in Zoho.
"""

import os
import httpx
from typing import Optional

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

        # Stop if no more pages
        page_context = data.get("page_context", {})
        if not page_context.get("has_more_page", False):
            break
        page += 1

    return items


def get_zoho_stock() -> dict[str, float]:
    """
    Main entry point.
    Returns {sku: stock_on_hand} for all items in Zoho Books.
    Keys are stripped/uppercased for consistent matching.
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
        # Zoho items have a 'sku' field — match it to our PART NO
        sku = str(item.get("sku") or item.get("name") or "").strip().upper()
        if not sku:
            continue
        stock = float(item.get("stock_on_hand") or 0)
        stock_map[sku] = stock

    return stock_map


def match_stock_to_parts(
    part_numbers: list[str],
    stock_map: dict[str, float],
) -> dict[str, Optional[float]]:
    """
    Match Excel part numbers to Zoho stock.
    Returns {part_no: stock} — None if no match found in Zoho.
    """
    result = {}
    for pn in part_numbers:
        key = str(pn).strip().upper()
        result[pn] = stock_map.get(key)   # None if not found
    return result
