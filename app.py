import streamlit as st
from utils import load_websites, load_latest_statuses
import pandas as pd
from datetime import datetime

# Configure page
st.set_page_config(layout="wide", page_title="Website Monitor")
st.title("Website Monitor Dashboard")
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
        return pd.merge(websites_df, statuses_df, on="URL", how="left")
    return websites_df if not websites_df.empty else statuses_df

# Load and process data
merged = load_data()

# Ensure required columns exist
required_columns = {'Name', 'URL', 'Status', 'SSL Expiry', 'Domain Expiry'}
for col in required_columns:
    if col not in merged.columns:
        merged[col] = None if col in ['SSL Expiry', 'Domain Expiry'] else 'N/A'

# Sort and calculate metrics
merged = merged.sort_values("Name", na_position='last')
current_time = datetime.now()

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

# Display summary
st.markdown(
    f"**Total:** {total} | ❌ **Down:** {down_count} | "
    f"🔒 **Expired SSL:** {expired_ssl} | 🌐 **Expired Domain:** {expired_domain}"
)
st.divider()

# Display website cards in a Cupertino-style grid
cols = st.columns(2)  # 2-column grid
for idx, row in merged.iterrows():
    # Determine card status
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
    is_down = (row.get("Status", "N/A") != "OK") or ssl_expired or domain_expired

    # Use #FB4141 for down cards
    card_color = "#FB4141" if is_down else "#f8f8f8"
    text_color = "#fff" if is_down else "#111"
    border_color = "#e5e5ea"
    shadow = "0 4px 16px rgba(0,0,0,0.06)" if not is_down else "0 4px 16px rgba(251,65,65,0.15)"

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

    # Robustly get the website name (handle possible whitespace/case issues and fallback to URL if missing)
    name = None
    for col in row.index:
        if col.strip().lower() in ["name", "website name", "site name"]:
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
    <div style="
        background:{card_color};
        color:{text_color};
        border-radius:24px;
        box-shadow:{shadow};
        border:1.5px solid {border_color};
        padding:2em 1.5em 1.5em 1.5em;
        margin-bottom:2em;
        min-height:270px;
        display:flex;
        flex-direction:column;
        align-items:center;
        transition:box-shadow 0.2s;
        cursor:pointer;
    ">
        <div style="background:#fff;border-radius:50%;width:128px;height:128px;display:flex;align-items:center;justify-content:center;margin-bottom:1em;">
            {"<img src='"+str(row["Logo URL"])+"' style='width:110px;height:110px;object-fit:contain;border-radius:50%;border:none;'>" if pd.notna(row.get("Logo URL")) else ""}
        </div>
        <div style="font-size:2em;font-weight:700;margin-bottom:0.5em;line-height:1.1;text-align:center;">{name}</div>
        <div style="font-size:1em;opacity:0.8;margin-bottom:0.5em;">SSL Expiry <b>{ssl_date}</b></div>
        <div style="font-size:1em;opacity:0.8;">Domain Expiry <b>{domain_date}</b></div>
    </div>
    </a>
    """
    cols[idx % 2].markdown(card_html, unsafe_allow_html=True)

st.markdown("⏱️ Last refreshed: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))