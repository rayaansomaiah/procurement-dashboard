import pandas as pd
import io


REQUIRED_COLS = ["consumption_per_month", "l1_vendor", "l1_lead", "l1_price"]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map the raw Excel columns from Data Proc...xlsx into standardized internal names.
    Handles the existing file format:
      Category, Sub category, PART NO, DESCRIPTION, MODEL, ASSY NAME,
      Month, Consumption/Month, L1 Vendor, Lead (L1), Price (L1), L2, Lead (L2), Price (L2)
    """
    col_map = {}
    cols = list(df.columns)

    for i, c in enumerate(cols):
        c_clean = str(c).strip().lower()
        if c_clean in ("category", "category "):
            col_map[c] = "category"
        elif c_clean in ("sub category", "sub category "):
            col_map[c] = "sub_category"
        elif c_clean in ("part no", "part no.", "sku", "sku code", "part_no"):
            col_map[c] = "sku_code"
        elif c_clean in ("description",):
            col_map[c] = "description"
        elif c_clean in ("model",):
            col_map[c] = "model"
        elif c_clean in ("assy name",):
            col_map[c] = "assy_name"
        elif c_clean in ("month",):
            col_map[c] = "frequency_label"
        elif c_clean in ("consumption/month", "consumption per month", "consumption factor"):
            col_map[c] = "consumption_per_month"
        elif c_clean in ("l1 vendor", "l1_vendor", "vendor 1", "vendor1"):
            col_map[c] = "l1_vendor"
        elif c_clean in ("l2", "l2 vendor", "l2_vendor", "vendor 2", "vendor2"):
            col_map[c] = "l2_vendor"

    # Lead and Price columns — positional fallback (they repeat names in the raw file)
    lead_cols = [c for c in cols if str(c).strip().lower() in ("lead", "lead ", "lead time")]
    price_cols = [c for c in cols if str(c).strip().lower() in ("price", "price ", "unit price")]

    if len(lead_cols) >= 1 and lead_cols[0] not in col_map:
        col_map[lead_cols[0]] = "l1_lead"
    if len(lead_cols) >= 2 and lead_cols[1] not in col_map:
        col_map[lead_cols[1]] = "l2_lead"
    if len(price_cols) >= 1 and price_cols[0] not in col_map:
        col_map[price_cols[0]] = "l1_price"
    if len(price_cols) >= 2 and price_cols[1] not in col_map:
        col_map[price_cols[1]] = "l2_price"

    # Optional stock columns (if user added them)
    for c in cols:
        c_clean = str(c).strip().lower()
        if c_clean in ("current stock", "current_stock", "stock on hand", "closing stock") and c not in col_map:
            col_map[c] = "current_stock"
        elif c_clean in ("incoming stock", "incoming_stock", "open po", "on order") and c not in col_map:
            col_map[c] = "incoming_stock"
        elif c_clean in ("moq", "minimum order qty", "min order qty") and c not in col_map:
            col_map[c] = "moq"
        elif c_clean in ("pack size", "pack_size", "pack") and c not in col_map:
            col_map[c] = "pack_size"
        elif c_clean in ("machines", "no. of machines", "num machines", "machine count") and c not in col_map:
            col_map[c] = "machines_override"

    df = df.rename(columns=col_map)

    # Ensure required numeric columns exist
    if "consumption_per_month" not in df.columns:
        raise ValueError("Could not find 'Consumption/Month' column in the uploaded file.")

    df["consumption_per_month"] = pd.to_numeric(df["consumption_per_month"], errors="coerce").fillna(0)

    for col in ("l1_price", "l2_price", "current_stock", "incoming_stock", "moq", "pack_size"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Default optional columns
    for col, default in [("current_stock", 0), ("incoming_stock", 0), ("moq", 1), ("pack_size", 1)]:
        if col not in df.columns:
            df[col] = default

    # Drop rows with no consumption factor and no part info
    df = df[df["consumption_per_month"] > 0].reset_index(drop=True)

    return df


def load_excel(file) -> tuple[pd.DataFrame, list[str]]:
    """
    Load an Excel file (file-like object or path).
    Returns (dataframe, list_of_warnings).
    """
    warnings = []
    try:
        xl = pd.ExcelFile(file)
        sheet = xl.sheet_names[0]
        if len(xl.sheet_names) > 1:
            warnings.append(f"Multiple sheets found. Using first sheet: '{sheet}'.")
        df_raw = xl.parse(sheet)
    except Exception as e:
        raise ValueError(f"Could not read Excel file: {e}")

    try:
        df = normalize_columns(df_raw)
    except ValueError as e:
        raise ValueError(str(e))

    if "sku_code" not in df.columns:
        warnings.append("No 'PART NO' column found. Using row numbers as SKU codes.")
        df["sku_code"] = [f"SKU-{i+1:03d}" for i in range(len(df))]

    if "description" not in df.columns:
        df["description"] = "—"

    return df, warnings
