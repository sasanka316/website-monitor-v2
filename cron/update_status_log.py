import sys
import socket
import cloudscraper
import datetime
import whois
import ssl
import OpenSSL
import gspread
import json
import os
from urllib.parse import urlparse
from gspread_pandas import Spread
from google.oauth2.service_account import Credentials
import dns.resolver

# Define required scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def authenticate_gspread():
    try:
        # Read credentials from file
        with open('creds.json', 'r') as f:
            creds_info = json.load(f)
        
        # Create credentials object
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        sys.exit(1)

def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

def check_ssl_expiry(domain):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                expires = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                return expires.date()
    except Exception as e:
        return f"SSL Error: {e}"

def check_domain_expiry(domain):
    try:
        w = whois.whois(domain)
        if isinstance(w.expiration_date, list):
            return min([d for d in w.expiration_date if d])  # pick the earliest valid one
        return w.expiration_date
    except Exception as e:
        return f"Whois Error: {e}"

def is_website_down(url):
    try:
        # DNS check
        domain = get_domain(url)
        dns.resolver.resolve(domain, 'A')
        
        # HTTP check using cloudscraper
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=10)
        return response.status_code != 200
    except Exception:
        return True  # Consider website down if any error occurs

def find_row_by_url(sheet, url):
    """Find the row number for a given URL in the status log sheet"""
    try:
        # Get all values from the sheet
        all_values = sheet.get_all_values()
        
        # Look for the URL in the third column (index 2)
        for i, row in enumerate(all_values, start=1):  # start=1 because sheet rows are 1-indexed
            if len(row) >= 3 and row[2] == url:  # URL is in the third column
                return i
        return None
    except Exception as e:
        print(f"Error finding row for URL {url}: {str(e)}")
        return None

def main():
    try:
        client = authenticate_gspread()
        sheet = client.open("WebsiteMonitor")

        websites_sheet = sheet.worksheet("websites")
        status_log_sheet = sheet.worksheet("status_log")

        websites = websites_sheet.get_all_records()
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        for site in websites:
            name = site["Name"]
            url = site["URL"]

            domain = get_domain(url)

            ssl_expiry = check_ssl_expiry(domain)
            domain_expiry = check_domain_expiry(domain)
            is_down = is_website_down(url)

            status = "OK"
            if isinstance(ssl_expiry, str) or isinstance(domain_expiry, str) or is_down:
                status = "DOWN"

            new_row = [
                datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                name,
                url,
                status,
                ssl_expiry.strftime("%Y-%m-%d") if isinstance(ssl_expiry, datetime.date) else str(ssl_expiry),
                domain_expiry.strftime("%Y-%m-%d") if isinstance(domain_expiry, datetime.date) else str(domain_expiry)
            ]

            # Find existing row for this URL
            row_num = find_row_by_url(status_log_sheet, url)
            
            if row_num:
                # Update existing row
                status_log_sheet.update(f'A{row_num}:F{row_num}', [new_row])
            else:
                # If no existing row found, append new row
                status_log_sheet.append_row(new_row, value_input_option="USER_ENTERED")

    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
