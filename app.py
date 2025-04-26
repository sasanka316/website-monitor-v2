import streamlit as st
from utils import load_websites, load_latest_statuses
import pandas as pd
from datetime import datetime
from pandas.api.types import is_datetime64_any_dtype
from zoneinfo import ZoneInfo

# Set current_time at the very top for consistency
current_time = datetime.now()

# Configure page
st.set_page_config(layout="wide", page_title="Website Monitor")
st.title("Website Monitor Dashboard")
st.markdown("<div style='margin-top:-1.2em; margin-bottom:0.2em; font-size:0.98em;'>Last Refreshed: " +
    datetime.now(ZoneInfo('Asia/Colombo')).strftime("%Y-%m-%d %H:%M:%S") +
    " (SLST, GMT+5:30)</div>", unsafe_allow_html=True)
#st.markdown("Automatically refreshes every 3 hours.")

@st.cache_data(ttl=10800)  # Cache for 3 hours
def load_data():
    """Load and merge data with error handling"""
    websites_df = load_websites()
    statuses_df = load_latest_statuses()
    
    # Create fallback data if both loads fail
    if websites_df.empty and statuses_df.empty:
        st.warning("⚠️ Using sample data - connection to Google Sheets failed")
        return pd.DataFrame({
            'Name': ['Example'],
            'URL': ['https://example.com'],
            'Logo URL': ['https://example.com/favicon.ico'],
            'Status': ['OK'],
            'SSL Expiry': [datetime.now()],
            'Domain Expiry': [datetime.now()]
        })
    
    # Merge with proper handling for empty DataFrames
    if not websites_df.empty and not statuses_df.empty:
        merged_df = pd.merge(websites_df, statuses_df, on="URL", how="left")
    else:
        merged_df = websites_df if not websites_df.empty else statuses_df
    
    # Ensure Name column exists
    if 'Name' not in merged_df.columns:
        # Try to find alternative name columns
        name_cols = [col for col in merged_df.columns if 'name' in col.lower()]
        if name_cols:
            merged_df['Name'] = merged_df[name_cols[0]]
        else:
            # If no name column found, create one from URL
            merged_df['Name'] = merged_df['URL'].apply(lambda x: x.split('//')[-1].split('/')[0] if pd.notna(x) else '')
    
    # Clean and sort the data
    merged_df['Name'] = merged_df['Name'].fillna('').astype(str).str.strip()
    return merged_df.sort_values("Name", na_position='last', ignore_index=True)

# Load and process data
merged = load_data()

# Ensure required columns exist
required_columns = {'Name', 'URL', 'Status', 'SSL Expiry', 'Domain Expiry'}
for col in required_columns:
    if col not in merged.columns:
        merged[col] = None if col in ['SSL Expiry', 'Domain Expiry'] else 'N/A'

# Sort and calculate metrics
# Clean and prepare the Name column for sorting
merged['Name'] = merged['Name'].fillna('').astype(str).str.strip()
merged = merged.sort_values("Name", na_position='last', ignore_index=True)

total = len(merged)

# Safely calculate expired SSL count
expired_ssl = 0
if 'SSL Expiry' in merged.columns:
    for date in merged['SSL Expiry']:
        try:
            if pd.notna(date) and pd.to_datetime(date) < current_time:
                expired_ssl += 1
        except:
            expired_ssl += 1  # Count as expired if date is invalid

# Safely calculate expired domain count
expired_domain = 0
if 'Domain Expiry' in merged.columns:
    for date in merged['Domain Expiry']:
        try:
            if pd.notna(date) and pd.to_datetime(date) < current_time:
                expired_domain += 1
        except:
            expired_domain += 1  # Count as expired if date is invalid

# Calculate down count
down_count = sum(
    (merged["Status"] != "OK") 
    if 'Status' in merged.columns else 0
)

# Compact summary row
st.markdown(
    f"<div style='font-size:1em; margin-bottom:0.2em; margin-top:-0.7em;'><b>Total:</b> {total} | <span style='color:#000000;'>❌ <b>Down:</b> {down_count}</span> | "
    f"<span style='color:#000000;'>🔒 <b>Expired SSL:</b> {expired_ssl}</span> | <span style='color:#000000;'>🌐 <b>Expired Domain:</b> {expired_domain}</span></div>",
    unsafe_allow_html=True
)
st.markdown("<hr style='margin-top:0.5em; margin-bottom:0.5em;'>", unsafe_allow_html=True)

# Add sorting options
sort_options = {
    "Alphabetical": "Name",
    "Not Working": "is_down",
    "SSL Expiry Date": "SSL Expiry",
    "Domain Expiry Date": "Domain Expiry"
}

# Add is_down column for sorting
def compute_is_down(row):
    status = str(row.get("Status", "")).strip().lower()
    ssl_expired = False
    domain_expired = False
    try:
        if pd.notna(row.get("SSL Expiry")):
            ssl_expired = pd.to_datetime(row["SSL Expiry"]) < current_time
    except:
        ssl_expired = True
    try:
        if pd.notna(row.get("Domain Expiry")):
            domain_expired = pd.to_datetime(row["Domain Expiry"]) < current_time
    except:
        domain_expired = True
    # Only 'ok' (case-insensitive) is considered working
    return (status != "ok") or ssl_expired or domain_expired

merged["is_down"] = merged.apply(compute_is_down, axis=1)

selected_sort = st.selectbox("Sort by:", list(sort_options.keys()))

# Sort the data based on the selected option
if selected_sort == "Not Working":
    merged = merged[merged["is_down"] == True].sort_values(by=["is_down", "Name"], ascending=[False, True], na_position='last')
else:
    merged = merged.sort_values(by=sort_options[selected_sort], na_position='last')

# Reset index to ensure correct card order
merged = merged.reset_index(drop=True)

# Add custom CSS for card animations only (revert to previous, simpler style)
st.markdown('''
<style>
.card-anim {
    transition: transform 0.18s cubic-bezier(.4,0,.2,1), box-shadow 0.18s cubic-bezier(.4,0,.2,1);
}
.card-anim:hover {
    transform: scale(1.045) translateY(-6px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.10);
    z-index: 2;
}
.card-anim:active {
    transform: scale(0.97);
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
</style>
''', unsafe_allow_html=True)

# Display website cards in a Cupertino-style grid
cols = st.columns(6)  # 6-column grid
for idx, row in merged.iterrows():
    is_down = row.get('is_down', False)

    # Use red border for down cards, light gray for working cards
    border_color = "#FF0000" if is_down else "#e5e5ea"
    card_color = "#f8f8f8"
    text_color = "#111"
    shadow = "0 4px 16px rgba(0,0,0,0.06)"

    # Format dates safely
    ssl_date = "N/A"
    domain_date = "N/A"
    try:
        if pd.notna(row.get("SSL Expiry")):
            ssl_date = pd.to_datetime(row["SSL Expiry"]).date()
    except:
        ssl_date = "Error"
    try:
        if pd.notna(row.get("Domain Expiry")):
            domain_date = pd.to_datetime(row["Domain Expiry"]).date()
    except:
        domain_date = "Error"

    # Robustly get the website name (try all possible columns, fallback to URL)
    name = None
    possible_name_cols = [c for c in row.index if c.strip().lower() in ["name", "name_x", "name_y", "website name", "site name"]]
    for col in possible_name_cols:
        if pd.notna(row[col]) and str(row[col]).strip() != "":
            name = row[col]
            break
    if not name or str(name).strip() == "":
        # Try to extract from URL
        url = str(row.get("URL", ""))
        if url and url.startswith("http"):
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                name = parsed.hostname.replace("www.", "") if parsed.hostname else url
            except:
                name = url
        else:
            name = "N/A"

    # Card HTML
    card_html = f"""
    <a href="{row.get('URL', '#')}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;">
    <div class="card-anim" style="
        background:{card_color};
        color:{text_color};
        border-radius:20px;
        box-shadow:{shadow};
        border:3px solid {border_color};
        padding:0.8em 0.7em 0.7em 0.7em;
        margin-bottom:1.2em;
        min-height:220px;
        max-height:220px;
        height:220px;
        display:flex;
        flex-direction:column;
        align-items:center;
        transition:box-shadow 0.2s;
        cursor:pointer;
    ">
        <div style="background:#fff;border-radius:50%;width:90px;height:90px;display:flex;align-items:center;justify-content:center;margin-bottom:0.5em;">
            {"<img src='"+str(row["Logo URL"]) + "' style='width:90px;height:90px;object-fit:contain;border-radius:50%;border:none;'>" if pd.notna(row.get("Logo URL")) else ""}
        </div>
        <div style="
            font-size:1em;
            font-weight:600;
            margin-bottom:0.2em;
            line-height:1.1;
            text-align:center;
            height:auto;
            overflow:visible;
            white-space:normal;
            padding:0 0.2em;">
            <span style=\"color: {'#FF0000' if is_down else '#00FF00'}; font-size:1.2em; margin-right:0.2em;\">●</span>{name}
        </div>
        <div style="flex:1 1 auto;"></div>
        <div style="font-size:0.8em;opacity:0.8;margin-bottom:0.2em;">SSL Expiry <b>{ssl_date}</b></div>
        <div style="font-size:0.8em;opacity:0.8;">Domain Expiry <b>{domain_date}</b></div>
    </div>
    </a>
    """
    cols[idx % 6].markdown(card_html, unsafe_allow_html=True)
    if (idx + 1) % 6 == 0:
        st.markdown("<div style='height:2em'></div>", unsafe_allow_html=True)

