import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from gspread_pandas import Spread, Client
from datetime import datetime
import requests
import ssl
import whois
import socket
import OpenSSL
from urllib.parse import urlparse

def connect_to_sheets():
    """Establish connection to Google Sheets with robust error handling"""
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ GCP Service Account missing in secrets!")
            return None
            
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return Client(creds)
    except Exception as e:
        st.error(f"🔴 Google Sheets connection failed: {str(e)}")
        return None

def load_data_from_sheet(sheet_name):
    """Generic function to load data from specified sheet"""
    try:
        client = connect_to_sheets()
        if not client:
            return pd.DataFrame()

        if "sheet_id" not in st.secrets:
            st.error("❌ Sheet ID missing in secrets!")
            return pd.DataFrame()

        spread = Spread(st.secrets["sheet_id"], sheet_name)
        return spread.sheet_to_df(index=None)
    except Exception as e:
        st.error(f"🔴 Failed to load {sheet_name} data: {str(e)}")
        return pd.DataFrame()

def load_websites():
    """Load websites data with fallback to empty DataFrame"""
    return load_data_from_sheet("websites")

def load_latest_statuses():
    """Load statuses data with fallback to empty DataFrame"""
    return load_data_from_sheet("status_log")

def is_website_down(url):
    """Check if website is down with timeout and proper URL handling"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    try:
        response = requests.get(
            url, 
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'},
            allow_redirects=True
        )
        return response.status_code != 200
    except requests.RequestException:
        return True

def check_ssl_expiry(url):
    """Check SSL certificate expiry with improved error handling"""
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return None
            
        cert = ssl.get_server_certificate((hostname, 443))
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        expiry_str = x509.get_notAfter().decode('ascii')
        return datetime.strptime(expiry_str, '%Y%m%d%H%M%SZ')
    except Exception:
        return None

def check_domain_expiry(url):
    """Check domain expiry with improved URL parsing"""
    try:
        domain = urlparse(url).hostname
        if not domain:
            return None
            
        w = whois.whois(domain)
        if isinstance(w.expiration_date, list):
            return w.expiration_date[0]
        return w.expiration_date
    except Exception:
        return None
