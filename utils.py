import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import gspread
from datetime import datetime, timedelta
import requests
import ssl
import whois
import socket
import OpenSSL
from urllib.parse import urlparse
import json

def connect_to_sheets():
    """Establish connection to Google Sheets with robust error handling"""
    try:
        # Debug: Print available secrets
        st.write("Available secrets:", list(st.secrets.keys()))
        
        if "gcp_service_account" not in st.secrets:
            st.error("❌ GCP Service Account missing in secrets!")
            return None
            
        # Debug: Print service account info
        service_account_info = st.secrets["gcp_service_account"]
        st.write("Service account email:", service_account_info.get("client_email", "Not found"))
        
        # Get sheet_id from service account info
        sheet_id = service_account_info.get("sheet_id")
        if not sheet_id:
            st.error("❌ Sheet ID missing in service account info!")
            return None
            
        # Create credentials
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        
        # Create client
        client = gspread.authorize(creds)
        
        # Test the connection
        try:
            spreadsheet = client.open_by_key(sheet_id)
            st.success("✅ Successfully connected to Google Sheets")
            return client, sheet_id
        except Exception as e:
            st.error(f"❌ Failed to open spreadsheet: {str(e)}")
            return None, None
            
    except Exception as e:
        st.error(f"🔴 Google Sheets connection failed: {str(e)}")
        st.error("Please check your secrets configuration in Streamlit Cloud")
        return None, None

def load_data_from_sheet(sheet_name):
    """Generic function to load data from specified sheet"""
    try:
        client, sheet_id = connect_to_sheets()
        if not client or not sheet_id:
            st.error("❌ Failed to connect to Google Sheets")
            return pd.DataFrame()

        # Open the spreadsheet
        spreadsheet = client.open_by_key(sheet_id)
        
        # Get the worksheet
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Get all values
        data = worksheet.get_all_records()
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        if df.empty:
            st.warning(f"⚠️ No data found in sheet: {sheet_name}")
        else:
            st.success(f"✅ Successfully loaded {len(df)} rows from {sheet_name}")
            
        return df
    except Exception as e:
        st.error(f"🔴 Failed to load {sheet_name} data: {str(e)}")
        st.error("Please check your sheet ID and make sure the service account has access")
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
            return datetime.now() - timedelta(days=1)  # Return expired date
            
        cert = ssl.get_server_certificate((hostname, 443))
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        expiry_str = x509.get_notAfter().decode('ascii')
        return datetime.strptime(expiry_str, '%Y%m%d%H%M%SZ')
    except Exception:
        return datetime.now() - timedelta(days=1)  # Return expired date

def check_domain_expiry(url):
    """Check domain expiry with improved URL parsing"""
    try:
        domain = urlparse(url).hostname
        if not domain:
            return datetime.now() - timedelta(days=1)  # Return expired date
            
        w = whois.whois(domain)
        if isinstance(w.expiration_date, list):
            return min([d for d in w.expiration_date if d])  # pick the earliest valid one
        return w.expiration_date
    except Exception:
        return datetime.now() - timedelta(days=1)  # Return expired date
