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
expired_ssl = sum(
    (pd.to_datetime(merged["SSL Expiry"]) < current_time) 
    if 'SSL Expiry' in merged.columns else 0
)
expired_domain = sum(
    (pd.to_datetime(merged["Domain Expiry"]) < current_time) 
    if 'Domain Expiry' in merged.columns else 0
)
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
        ssl_expired = pd.to_datetime(row.get("SSL Expiry", current_time)) < current_time
        domain_expired = pd.to_datetime(row.get("Domain Expiry", current_time)) < current_time
        is_down = (row.get("Status", "N/A") != "OK") or ssl_expired or domain_expired
        
        card_color = "#ffdddd" if is_down else "#e6ffec"
        status_icon = "🔴" if is_down else "🟢"
        
        st.markdown(
            f"""
            <div style="background-color:{card_color}; padding:1em; border-radius:1em; margin-bottom:1em;">
                <h4>{status_icon} {row.get('Name', 'N/A')}</h4>
                <a href="{row.get('URL', '#')}" target="_blank">{row.get('URL', 'N/A')}</a><br/>
                {f'<img src="{row["Logo URL"]}" width="100"/><br/>' if pd.notna(row.get("Logo URL")) else ''}
                <b>Status:</b> {row.get('Status', 'N/A')}<br/>
                <b>SSL Expiry:</b> {row['SSL Expiry'].date() if pd.notna(row.get('SSL Expiry')) else "N/A"}<br/>
                <b>Domain Expiry:</b> {row['Domain Expiry'].date() if pd.notna(row.get('Domain Expiry')) else "N/A"}
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("⏱️ Last refreshed: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))