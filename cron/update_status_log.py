import sys
import socket
import requests
import datetime
import whois
import ssl
import OpenSSL
import gspread
from urllib.parse import urlparse
from google.oauth2.service_account import Credentials
import dns.resolver

# Define required scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def authenticate_gspread(creds_path):
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

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
        
        # HTTP check
        response = requests.get(url, timeout=10)
        return response.status_code != 200
    except Exception:
        return True  # Consider website down if any error occurs

def main(creds_path):
    client = authenticate_gspread(creds_path)
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


        status_log_sheet.append_row(new_row, value_input_option="USER_ENTERED")

if __name__ == "__main__":
    main(sys.argv[1])
