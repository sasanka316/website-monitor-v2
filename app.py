import streamlit as st
from utils import load_websites, load_latest_statuses
import pandas as pd
from datetime import datetime

# Configure page
st.set_page_config(layout="wide", page_title="Website Monitor")
st.title("Website Monitor Dashboard")
st.markdown("Last refreshed: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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

# Add custom CSS for card animations
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
        border-radius:24px;
        box-shadow:{shadow};
        border:1.5px solid {border_color};
        padding:1.2em 1em 1em 1em;
        margin-bottom:2em;
        min-height:320px;
        max-height:320px;
        height:320px;
        display:flex;
        flex-direction:column;
        align-items:center;
        transition:box-shadow 0.2s;
        cursor:pointer;
    ">
        <div style="background:#fff;border-radius:50%;width:150px;height:150px;display:flex;align-items:center;justify-content:center;margin-bottom:0.9em;">
            {"<img src='"+str(row["Logo URL"]) + "' style='width:130px;height:130px;object-fit:contain;border-radius:50%;border:none;'>" if pd.notna(row.get("Logo URL")) else ""}
        </div>
        <div style="
            font-size:1.55em;
            font-weight:700;
            margin-bottom:0.3em;
            line-height:1.1;
            text-align:center;
            height:2.7em;
            overflow:hidden;
            display:-webkit-box;
            -webkit-line-clamp:2;
            -webkit-box-orient:vertical;
            text-overflow:ellipsis;
            white-space:normal;">
            {name}
        </div>
        <div style="flex:1 1 auto;"></div>
        <div style="font-size:0.95em;opacity:0.8;margin-bottom:0.3em;">SSL Expiry <b>{ssl_date}</b></div>
        <div style="font-size:0.95em;opacity:0.8;">Domain Expiry <b>{domain_date}</b></div>
    </div>
    </a>
    """
    cols[idx % 6].markdown(card_html, unsafe_allow_html=True)
    # Add vertical space after every 6 cards (i.e., after each row)
    if (idx + 1) % 6 == 0:
        st.markdown("<div style='height:2em'></div>", unsafe_allow_html=True)

