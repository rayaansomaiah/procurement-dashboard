import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import datetime

from utils.excel_loader import load_excel
from logic.demand import compute_demand
from logic.alerts import add_urgency
from logic.reasoning import add_reasoning
from utils.export import to_excel_bytes

st.set_page_config(
    page_title="Procurement Planner",
    page_icon="📦",
    layout="wide",
)

URGENCY_COLORS = {
    "Critical" : "🔴",
    "High"     : "🟠",
    "Medium"   : "🟡",
    "Low"      : "🟢",
    "No Action": "⚪",
}

URGENCY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "No Action": 4}

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Settings")

    uploaded_file = st.file_uploader(
        "Upload Data File (Excel)",
        type=["xlsx", "xls"],
        help="Upload your consumption & vendor data.",
    )

    st.divider()

    num_machines = st.number_input(
        "Number of Machines Onboarded",
        min_value=1,
        value=1,
        step=1,
    )

    horizon_days = st.selectbox(
        "Planning Horizon",
        options=[30, 60, 90],
        index=0,
        format_func=lambda x: f"{x} days ({x//30} month{'s' if x > 30 else ''})",
    )

    safety_buffer_pct = st.slider(
        "Safety Buffer %",
        min_value=0,
        max_value=100,
        value=20,
        step=5,
        help="Extra stock buffer on top of lead time coverage.",
    )

    st.divider()

    vendor_strategy = st.radio(
        "🏭 Vendor Strategy",
        options=["Prefer L1", "Fastest Delivery", "Cheapest Price"],
        index=0,
        help=(
            "**Prefer L1** — Use L1 vendor by default; switch to L2 only if L2 is faster.\n\n"
            "**Fastest Delivery** — Always pick whichever vendor delivers sooner.\n\n"
            "**Cheapest Price** — Always pick whichever vendor has the lower unit price."
        ),
    )

    st.divider()
    st.caption(f"Today: {datetime.date.today().strftime('%d %b %Y')}")

# ── Main area ─────────────────────────────────────────────────────────────────

st.title("📦 Procurement Planning Dashboard")

if not uploaded_file:
    st.info("👈 Upload your Excel file from the sidebar to get started.")
    st.subheader("Expected File Format")
    sample = pd.DataFrame({
        "PART NO"           : ["990-14900", "53103205"],
        "DESCRIPTION"       : ["Side Cutter Bolt", "Tooth Point"],
        "Category"          : ["GET", "GET"],
        "Consumption/Month" : [1.5, 1.5],
        "L1 Vendor"         : ["GTS", "XHGET"],
        "Lead "             : ["15 days", "60 days"],
        "Price "            : [22.42, 319.00],
        "L2"                : ["J V Industries", "B NAIL"],
        "Lead"              : ["15 days", "90 days"],
        "Price"             : [22.87, 325.38],
        "Current Stock"     : [10, 0],
        "Incoming Stock"    : [0, 0],
    })
    st.dataframe(sample, use_container_width=True)
    st.caption(
        "**Required:** Consumption/Month, L1 Vendor, Lead (L1), Price (L1). "
        "**Optional:** Current Stock, Incoming Stock, MOQ, Pack Size."
    )
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────

try:
    df, warnings = load_excel(uploaded_file)
except ValueError as e:
    st.error(f"Error reading file: {e}")
    st.stop()

for w in warnings:
    st.warning(w)

if "machines_override" in df.columns:
    machines_col = df["machines_override"].fillna(num_machines)
else:
    machines_col = pd.Series(num_machines, index=df.index)

# ── Compute ───────────────────────────────────────────────────────────────────

results = []
for idx, row in df.iterrows():
    row_df = row.to_frame().T.reset_index(drop=True)
    m = int(machines_col.iloc[idx] if idx < len(machines_col) else num_machines)
    r = compute_demand(row_df, m, horizon_days, safety_buffer_pct, vendor_strategy)
    results.append(r)

result_df = pd.concat(results, ignore_index=True)
current_stock = result_df.get("current_stock", pd.Series(0, index=result_df.index))
result_df = add_urgency(result_df, current_stock)
result_df = add_reasoning(result_df)

# ── KPI Cards ─────────────────────────────────────────────────────────────────

total_skus    = len(result_df)
critical      = (result_df["urgency"] == "Critical").sum()
high          = (result_df["urgency"] == "High").sum()
action_needed = (result_df["recommended_order_qty"] > 0).sum()
total_cost    = result_df["estimated_cost"].sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total SKUs",       total_skus)
c2.metric("🔴 Critical",      int(critical))
c3.metric("🟠 High",          int(high))
c4.metric("📋 Action Needed", int(action_needed))
c5.metric("💰 Est. Total Spend", f"₹{total_cost:,.0f}")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_table, tab_alerts, tab_export = st.tabs([
    "📋 Procurement Table",
    f"⚠️ Alerts  ({int(critical + high)})",
    "📥 Export",
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Procurement Table
# ════════════════════════════════════════════════════════════════════════════

with tab_table:

    # Filters
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])
    with fc1:
        urgency_filter = st.multiselect(
            "Urgency",
            options=["Critical", "High", "Medium", "Low", "No Action"],
            default=[],
        )
    with fc2:
        categories = (
            result_df["category"].dropna().unique().tolist()
            if "category" in result_df.columns else []
        )
        cat_filter = st.multiselect("Category", options=categories, default=[])
    with fc3:
        vendors = result_df["recommended_vendor"].dropna().unique().tolist()
        vendor_filter = st.multiselect("Vendor", options=vendors, default=[])
    with fc4:
        action_only = st.checkbox("Needs order only", value=True)

    # Apply filters — empty selection means "show all"
    filtered = result_df.copy()
    if urgency_filter:
        filtered = filtered[filtered["urgency"].isin(urgency_filter)]
    if cat_filter:
        filtered = filtered[filtered["category"].isin(cat_filter)]
    if vendor_filter:
        filtered = filtered[filtered["recommended_vendor"].isin(vendor_filter)]
    if action_only:
        filtered = filtered[filtered["recommended_order_qty"] > 0]

    filtered = filtered.sort_values("urgency", key=lambda s: s.map(URGENCY_ORDER))

    st.caption(f"Showing **{len(filtered)}** of **{total_skus}** SKUs")

    # Build display dataframe
    display_cols = []
    col_labels   = {}
    for src, label in [
        ("sku_code",               "Part No"),
        ("description",            "Description"),
        ("category",               "Category"),
        ("monthly_demand",         "Monthly Demand"),
        ("current_stock",          "Current Stock"),
        ("stock_cover_days",       "Stock Cover (Days)"),
        ("recommended_order_qty",  "Order Qty"),
        ("recommended_vendor",     "Vendor"),
        ("recommended_lead_days",  "Lead (Days)"),
        ("recommended_unit_price", "Unit Price (₹)"),
        ("estimated_cost",         "Est. Cost (₹)"),
        ("order_by_date",          "Order By"),
        ("urgency",                "Urgency"),
        ("flags",                  "Flags"),
    ]:
        if src in filtered.columns:
            display_cols.append(src)
            col_labels[src] = label

    show_df = filtered[display_cols].rename(columns=col_labels).copy()

    if "Urgency" in show_df.columns:
        show_df["Urgency"] = show_df["Urgency"].map(
            lambda u: f"{URGENCY_COLORS.get(u, '')} {u}"
        )

    for col in ("Monthly Demand", "Est. Cost (₹)", "Unit Price (₹)"):
        if col in show_df.columns:
            show_df[col] = pd.to_numeric(show_df[col], errors="coerce").round(1)

    for col in ("Order Qty", "Current Stock", "Stock Cover (Days)"):
        if col in show_df.columns:
            show_df[col] = pd.to_numeric(show_df[col], errors="coerce").fillna(0).astype(int)

    st.dataframe(
        show_df,
        use_container_width=True,
        height=480,
        column_config={
            "Part No"           : st.column_config.TextColumn(),
            "Description"       : st.column_config.TextColumn(),
            "Category"          : st.column_config.TextColumn(),
            "Monthly Demand"    : st.column_config.NumberColumn(format="%.1f"),
            "Current Stock"     : st.column_config.NumberColumn(format="%d"),
            "Stock Cover (Days)": st.column_config.NumberColumn(format="%d"),
            "Order Qty"         : st.column_config.NumberColumn(format="%d"),
            "Vendor"            : st.column_config.TextColumn(),
            "Lead (Days)"       : st.column_config.NumberColumn(format="%d"),
            "Unit Price (₹)"   : st.column_config.NumberColumn(format="₹%.2f"),
            "Est. Cost (₹)"    : st.column_config.NumberColumn(format="₹%.0f"),
            "Order By"          : st.column_config.TextColumn(),
            "Urgency"           : st.column_config.TextColumn(),
            "Flags"             : st.column_config.TextColumn(),
        },
        hide_index=True,
    )

    # Reasoning panel
    st.subheader("🔍 Why is this being recommended?")
    if not filtered.empty:
        sku_options   = (filtered["sku_code"].astype(str) + " — " + filtered["description"].astype(str)).tolist()
        selected_label = st.selectbox("Select a part:", sku_options)
        selected_idx   = sku_options.index(selected_label)
        selected_row   = filtered.iloc[selected_idx]
        urgency        = selected_row.get("urgency", "")
        color_map      = {"Critical": "red", "High": "orange", "Medium": "blue", "Low": "green"}
        st.markdown(
            f"**{URGENCY_COLORS.get(urgency, '')} {urgency}** &nbsp;|&nbsp; "
            f"**{selected_row.get('sku_code', '')}** — {selected_row.get('description', '')}"
        )
        st.info(selected_row["reason"])
    else:
        st.caption("No parts match the current filters.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Alerts
# ════════════════════════════════════════════════════════════════════════════

with tab_alerts:
    alerts_df = result_df[result_df["urgency"].isin(["Critical", "High"])].copy()
    alerts_df = alerts_df.sort_values("urgency", key=lambda s: s.map(URGENCY_ORDER))

    if alerts_df.empty:
        st.success("✅ No critical or high urgency items. You're all good!")
    else:
        crit_count = (alerts_df["urgency"] == "Critical").sum()
        high_count = (alerts_df["urgency"] == "High").sum()
        st.markdown(
            f"**{int(crit_count)} Critical** items need immediate ordering &nbsp;|&nbsp; "
            f"**{int(high_count)} High** items need ordering soon."
        )
        st.divider()
        for _, row in alerts_df.iterrows():
            icon  = URGENCY_COLORS.get(row["urgency"], "")
            sku   = "" if str(row.get("sku_code", "")).lower() == "nan" else str(row.get("sku_code", ""))
            desc  = "" if str(row.get("description", "")).lower() == "nan" else str(row.get("description", ""))
            label = f"{sku}: {desc}".strip(": ")
            vendor = row.get("recommended_vendor", "")
            qty    = int(row.get("recommended_order_qty", 0))
            cost   = row.get("estimated_cost", 0)
            with st.expander(f"{icon} {row['urgency']} — {label}"):
                m1, m2, m3 = st.columns(3)
                m1.metric("Order Qty",   qty)
                m2.metric("Vendor",      vendor)
                m3.metric("Est. Cost",   f"₹{cost:,.0f}")
                st.write(row["reason"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Export
# ════════════════════════════════════════════════════════════════════════════

with tab_export:
    st.subheader("Download Procurement Plan")

    e1, e2 = st.columns(2)
    with e1:
        st.markdown("**Full Plan** — all SKUs")
        excel_bytes = to_excel_bytes(result_df)
        st.download_button(
            label="⬇️ Download Full Plan (Excel)",
            data=excel_bytes,
            file_name=f"procurement_plan_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with e2:
        st.markdown("**Filtered View** — matches current table filters")
        filtered_bytes = to_excel_bytes(filtered)
        st.download_button(
            label="⬇️ Download Filtered View (Excel)",
            data=filtered_bytes,
            file_name=f"procurement_filtered_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
