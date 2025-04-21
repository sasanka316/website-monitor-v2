import socket
import ssl
import whois
import gspread
from google.oauth2.service_account import Credentials
from urllib.parse import urlparse
from datetime import datetime
import sys
import pandas as pd

def get_ssl_expiry_date(hostname):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                return datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
    except:
        return None

def get_domain_expiry_date(domain):
    try:
        w = whois.whois(domain)
        exp = w.expiration_date
        if isinstance(exp, list):
            exp = exp[0]
        return pd.to_datetime(exp)
    except:
        return None

def check_status(url):
    try:
        host = urlparse(url).netloc
        socket.gethostbyname(host)
        return "OK"
    except:
        return "DOWN"

def main(creds_path):
    # Auth
    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open("website-monitor")

    websites_ws = sheet.worksheet("websites")
    status_log_ws = sheet.worksheet("status_log")

    websites = websites_ws.get_all_records()

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    for site in websites:
        url = site["URL"]
        name = site["Name"]
        parsed = urlparse(url)
        domain = parsed.netloc

        status = check_status(url)
        ssl_expiry = get_ssl_expiry_date(domain)
        domain_expiry = get_domain_expiry_date(domain)

        row = [
            now,
            name,
            url,
            status,
            ssl_expiry.strftime('%Y-%m-%d') if ssl_expiry else '',
            domain_expiry.strftime('%Y-%m-%d') if domain_expiry else ''
        ]

        status_log_ws.append_row(row, value_input_option="USER_ENTERED")

if __name__ == "__main__":
    main(sys.argv[1])
