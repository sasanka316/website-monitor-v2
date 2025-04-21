import streamlit as st
from utils import load_websites, load_latest_statuses, is_website_down
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="Website Monitor")

st.title("🌐 Website Monitor Dashboard")
st.markdown("Automatically refreshes every 3 hours.")

# Load website info & statuses
websites_df = load_websites()
statuses_df = load_latest_statuses()

# Merge both
merged = pd.merge(websites_df, statuses_df, on="URL", how="left")

# Sort alphabetically by name
merged = merged.sort_values("Name")

# Summary counters
total = len(merged)
expired_ssl = sum(merged["SSL Expiry"] < datetime.now())
expired_domain = sum(merged["Domain Expiry"] < datetime.now())
down_count = sum(merged["Status"] != "OK")

st.markdown(f"**Total:** {total} | ❌ **Down:** {down_count} | 🔒 **Expired SSL:** {expired_ssl} | 🌐 **Expired Domain:** {expired_domain}")

st.divider()

# Show cards
for _, row in merged.iterrows():
    col = st.columns(1)[0]
    with col:
        is_down = (
            row["Status"] != "OK"
            or row["SSL Expiry"] < datetime.now()
            or row["Domain Expiry"] < datetime.now()
        )

        card_color = "#ffdddd" if is_down else "#e6ffec"

        st.markdown(
            f"""
            <div style="background-color:{card_color}; padding:1em; border-radius:1em; margin-bottom:1em;">
                <h4>{row['Name']}</h4>
                <a href="{row['URL']}" target="_blank">{row['URL']}</a><br/>
                <img src="{row['Logo URL']}" width="100"/><br/>
                <b>Status:</b> {row['Status']}<br/>
                <b>SSL Expiry:</b> {row['SSL Expiry'].date() if pd.notnull(row['SSL Expiry']) else "N/A"}<br/>
                <b>Domain Expiry:</b> {row['Domain Expiry'].date() if pd.notnull(row['Domain Expiry']) else "N/A"}
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("⏱️ This app auto-refreshes every 3 hours using Streamlit Cloud's scheduler.")
