import pandas as pd
import io


URGENCY_COLORS = {
    "Critical": "FFCCCC",   # red
    "High":     "FFE5CC",   # orange
    "Medium":   "FFFACC",   # yellow
    "Low":      "CCFFCC",   # light green
    "No Action":"E8E8E8",   # grey
}

DISPLAY_COLS = [
    ("sku_code",              "Part No"),
    ("description",           "Description"),
    ("category",              "Category"),
    ("monthly_demand",        "Monthly Demand"),
    ("horizon_demand",        "Horizon Demand"),
    ("safety_stock",          "Safety Stock"),
    ("current_stock",         "Current Stock"),
    ("incoming_stock",        "Incoming Stock"),
    ("recommended_order_qty", "Order Qty"),
    ("recommended_vendor",    "Vendor"),
    ("recommended_lead_days", "Lead Time (Days)"),
    ("recommended_unit_price","Unit Price"),
    ("estimated_cost",        "Est. Cost"),
    ("order_by_date",         "Order By"),
    ("urgency",               "Urgency"),
    ("flags",                 "Flags"),
    ("reason",                "Reason"),
]


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()

    # Select and rename columns that exist
    export_cols = [(src, dst) for src, dst in DISPLAY_COLS if src in df.columns]
    out_df = df[[src for src, _ in export_cols]].copy()
    out_df.columns = [dst for _, dst in export_cols]

    # Round numeric columns (coerce first to handle any mixed-type columns)
    for col in ("Monthly Demand", "Horizon Demand", "Safety Stock", "Est. Cost"):
        if col in out_df.columns:
            out_df[col] = pd.to_numeric(out_df[col], errors="coerce").round(2)

    # Replace NaN/Inf so xlsxwriter doesn't choke
    out_df = out_df.replace([float("inf"), float("-inf")], "").fillna("")

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        out_df.to_excel(writer, sheet_name="Procurement Plan", index=False)

        wb = writer.book
        ws = writer.sheets["Procurement Plan"]

        # Header format
        header_fmt = wb.add_format({
            "bold": True, "bg_color": "2C5F8A", "font_color": "FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True
        })
        for col_num, col_name in enumerate(out_df.columns):
            ws.write(0, col_num, col_name, header_fmt)

        # Row formatting by urgency
        urgency_col_idx = list(out_df.columns).index("Urgency") if "Urgency" in out_df.columns else None

        for row_num, row in enumerate(out_df.itertuples(index=False), start=1):
            urgency = row.Urgency if "Urgency" in out_df.columns else "Low"
            bg = URGENCY_COLORS.get(urgency, "FFFFFF")
            row_fmt = wb.add_format({"bg_color": bg, "border": 1})
            for col_num, val in enumerate(row):
                ws.write(row_num, col_num, val, row_fmt)

        # Column widths — auto fit based on header and data content
        for col_num, col_name in enumerate(out_df.columns):
            col_data = out_df.iloc[:, col_num].astype(str)
            max_data_len = col_data.str.len().max() if not col_data.empty else 0
            width = max(len(col_name), max_data_len, 10) + 2
            width = min(width, 60)  # cap at 60 for Reason column
            ws.set_column(col_num, col_num, width)

        ws.freeze_panes(1, 0)

    return output.getvalue()
