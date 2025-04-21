# Functions to check server/DNS issues
import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
import gspread
import socket
import ssl
from urllib.parse import urlparse

def connect_to_sheets():
    creds = service_account.Credentials.from_service_account_info(
         st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open("WebsiteMonitor")
    return sheet

def load_websites():
    sheet = connect_to_sheets()
    data = sheet.worksheet("websites").get_all_records()
    return pd.DataFrame(data)

def load_latest_statuses():
    sheet = connect_to_sheets()
    log_data = sheet.worksheet("status_log").get_all_records()

    df = pd.DataFrame(log_data)
    if df.empty:
        return pd.DataFrame(columns=["Name", "URL", "Status", "SSL Expiry", "Domain Expiry"])

    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df["SSL Expiry"] = pd.to_datetime(df["SSL Expiry"], errors="coerce")
    df["Domain Expiry"] = pd.to_datetime(df["Domain Expiry"], errors="coerce")

    latest = df.sort_values("Timestamp").groupby("URL").tail(1)
    return latest

def is_website_down(url):
    try:
        host = urlparse(url).netloc
        socket.gethostbyname(host)
        return False
    except Exception:
        return True
