import streamlit as st
from utils import load_websites, load_latest_statuses
import pandas as pd
from datetime import datetime

# Configure page
st.set_page_config(layout="wide", page_title="Website Monitor")
st.title("🌐 Website Monitor Dashboard")
st.markdown("Automatically refreshes every 3 hours.")

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

# Display website cards
for _, row in merged.iterrows():
    col = st.columns(1)[0]
    with col:
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
        
        card_color = "#ffdddd" if is_down else "#e6ffec"
        status_icon = "🔴" if is_down else "🟢"
        
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
        
        st.markdown(
            f"""
            <div style="background-color:{card_color}; padding:1em; border-radius:1em; margin-bottom:1em;">
                <h4>{status_icon} {row.get('Name', 'N/A')}</h4>
                <a href="{row.get('URL', '#')}" target="_blank">{row.get('URL', 'N/A')}</a><br/>
                {f'<img src="{row["Logo URL"]}" width="100"/><br/>' if pd.notna(row.get("Logo URL")) else ''}
                <b>Status:</b> {row.get('Status', 'N/A')}<br/>
                <b>SSL Expiry:</b> {ssl_date}<br/>
                <b>Domain Expiry:</b> {domain_date}
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("⏱️ Last refreshed: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))