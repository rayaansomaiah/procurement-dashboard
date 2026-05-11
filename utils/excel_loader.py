import pandas as pd
import io

REQUIRED_COLS = ["consumption_per_month", "l1_vendor", "l1_lead", "l1_price"]

# ---------------------------------------------------------------------------
# Column name aliases → internal name
# ---------------------------------------------------------------------------
_ALIASES: dict[str, str] = {
    # Category / part info
    "category": "category", "category ": "category",
    "sub category": "sub_category", "sub category ": "sub_category", "sub cat": "sub_category",
    "sl no": "sl_no", "sl. no": "sl_no",
    "part no": "sku_code", "part no.": "sku_code", "sku": "sku_code",
    "sku code": "sku_code", "part_no": "sku_code",
    "description": "description",
    "model": "model",
    "assy name": "assy_name",
    "month": "frequency_label",

    # Consumption
    "consumption/month": "consumption_per_month",
    "consumption per month": "consumption_per_month",
    "consumption factor": "consumption_per_month",
    "consumption": "consumption_per_month",

    # L1
    "l1 vendor": "l1_vendor", "l1_vendor": "l1_vendor", "vendor 1": "l1_vendor",
    "vendor1": "l1_vendor", "l1": "l1_vendor",
    "l1 sku": "l1_sku",
    "l1 price": "l1_price", "price (l1)": "l1_price",
    "l1 lead time": "l1_lead", "lead (l1)": "l1_lead",

    # L2
    "l2": "l2_vendor", "l2 vendor": "l2_vendor", "l2_vendor": "l2_vendor",
    "vendor 2": "l2_vendor", "vendor2": "l2_vendor",
    "l2 sku": "l2_sku",
    "l2 price": "l2_price", "l2 price ": "l2_price", "l2price": "l2_price",
    "price (l2)": "l2_price",
    "l2 lead time": "l2_lead", "l2 lead time  ": "l2_lead",
    "lead (l2)": "l2_lead",

    # L3
    "l3": "l3_vendor", "l3 sku": "l3_sku",
    "l3 price": "l3_price", "l3 price ": "l3_price",

    # L4
    "l4": "l4_vendor", "l4 sku": "l4_sku",
    "l4 price": "l4_price", "l4price": "l4_price",

    # L5
    "l5": "l5_vendor", "l5 sku": "l5_sku",
    "l5 price": "l5_price", "l5price": "l5_price",

    # L6
    "l6": "l6_vendor", "l6 sku": "l6_sku",
    "l6 price": "l6_price", "l6price": "l6_price",

    # Stock
    "current stock": "current_stock", "current_stock": "current_stock",
    "stock on hand": "current_stock", "closing stock": "current_stock",
    "incoming stock": "incoming_stock", "incoming_stock": "incoming_stock",
    "open po": "incoming_stock", "on order": "incoming_stock",

    # MOQ / pack
    "moq": "moq", "minimum order qty": "moq", "min order qty": "moq",
    "pack size": "pack_size", "pack_size": "pack_size", "pack": "pack_size",

    # Per-row machine override
    "machines": "machines_override", "no. of machines": "machines_override",
    "num machines": "machines_override", "machine count": "machines_override",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {}
    for c in df.columns:
        key = str(c).strip().lower()
        if key in _ALIASES and _ALIASES[key] not in col_map.values():
            col_map[c] = _ALIASES[key]

    df = df.rename(columns=col_map)

    if "consumption_per_month" not in df.columns:
        raise ValueError("Could not find a 'Consumption' or 'Consumption/Month' column.")
    if "l1_vendor" not in df.columns:
        raise ValueError("Could not find an L1 vendor column.")
    if "l1_lead" not in df.columns:
        raise ValueError("Could not find an L1 lead time column.")
    if "l1_price" not in df.columns:
        raise ValueError("Could not find an L1 price column.")

    # Numeric coercion
    numeric_cols = [
        "consumption_per_month",
        "l1_price", "l2_price", "l3_price", "l4_price", "l5_price", "l6_price",
        "current_stock", "incoming_stock", "moq", "pack_size",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Default optional columns
    for col, default in [
        ("current_stock", 0), ("incoming_stock", 0), ("moq", 1), ("pack_size", 1),
        ("l2_vendor", ""), ("l2_sku", ""), ("l2_lead", None), ("l2_price", 0),
        ("l3_vendor", ""), ("l3_sku", ""), ("l3_price", 0),
        ("l4_vendor", ""), ("l4_sku", ""), ("l4_price", 0),
        ("l5_vendor", ""), ("l5_sku", ""), ("l5_price", 0),
        ("l6_vendor", ""), ("l6_sku", ""), ("l6_price", 0),
    ]:
        if col not in df.columns:
            df[col] = default

    # Drop rows with no consumption
    df = df[df["consumption_per_month"] > 0].reset_index(drop=True)
    return df


def load_excel(file) -> tuple[pd.DataFrame, list[str]]:
    warnings = []
    try:
        xl = pd.ExcelFile(file)
        sheet = xl.sheet_names[0]
        if len(xl.sheet_names) > 1:
            warnings.append(f"Multiple sheets found. Using first sheet: '{sheet}'.")
        df_raw = xl.parse(sheet)
    except Exception as e:
        raise ValueError(f"Could not read Excel file: {e}")

    df = normalize_columns(df_raw)

    if "sku_code" not in df.columns:
        warnings.append("No 'Part No' column found. Using row numbers as SKU codes.")
        df["sku_code"] = [f"SKU-{i+1:03d}" for i in range(len(df))]

    if "description" not in df.columns:
        df["description"] = "—"

    return df, warnings
