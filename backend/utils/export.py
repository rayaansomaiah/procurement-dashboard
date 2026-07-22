import io
import pandas as pd

# (source key in result dict, display header)
DISPLAY_COLS = [
    ("sku_code",         "SKU"),
    ("item",             "Item"),
    ("category",         "Category"),
    ("sub_category",     "Sub Category"),
    ("brand",            "Brand"),
    ("qoh",              "QOH"),
    ("purchase_price",   "Purchase Price"),
    ("prev_sales_qty",   "Prev Sales Qty"),
    ("sales_per_week",   "Sales / Week"),
    ("arc",              "ARC (Weeks)"),
    ("sales_proj",       "Sales Projection"),
    ("mdp_cdp",          "MDP/CDP"),
    ("consumption_hrs",  "Consumption Hrs"),
    ("consumption_load", "Consumption Load"),
    ("wallet_proj",      "Wallet Projection"),
    ("flf",              "FLF"),
    ("effective_demand", "Effective Demand"),
    ("indent_qty",       "Indent Qty"),
    ("purchase_amount",  "Purchase Amount"),
    ("stock_value",      "Stock Value"),
    ("matched",          "Zoho Matched"),
]

_INDENT_BG = "FFF2CC"  # soft amber for rows that need ordering


def to_excel_bytes(rows: list[dict]) -> bytes:
    output = io.BytesIO()

    out_df = pd.DataFrame([
        {dst: r.get(src, "") for src, dst in DISPLAY_COLS} for r in rows
    ], columns=[dst for _, dst in DISPLAY_COLS])

    out_df = out_df.replace([float("inf"), float("-inf")], "").fillna("")

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        out_df.to_excel(writer, sheet_name="Replenishment Indent", index=False)
        wb = writer.book
        ws = writer.sheets["Replenishment Indent"]

        header_fmt = wb.add_format({
            "bold": True, "bg_color": "2C5F8A", "font_color": "FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True,
        })
        for col_num, col_name in enumerate(out_df.columns):
            ws.write(0, col_num, col_name, header_fmt)

        indent_idx = list(out_df.columns).index("Indent Qty")
        for row_num, row in enumerate(out_df.itertuples(index=False), start=1):
            needs = False
            try:
                needs = float(row[indent_idx]) > 0
            except (ValueError, TypeError):
                needs = False
            row_fmt = wb.add_format({"bg_color": _INDENT_BG, "border": 1}) if needs \
                else wb.add_format({"border": 1})
            for col_num, val in enumerate(row):
                ws.write(row_num, col_num, val, row_fmt)

        for col_num, col_name in enumerate(out_df.columns):
            col_data = out_df.iloc[:, col_num].astype(str)
            max_data_len = col_data.str.len().max() if not col_data.empty else 0
            width = min(max(len(col_name), int(max_data_len), 8) + 2, 45)
            ws.set_column(col_num, col_num, width)

        ws.freeze_panes(1, 0)

    return output.getvalue()
