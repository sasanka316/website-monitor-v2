# 🌐 Website Monitor Dashboard

A Streamlit dashboard to monitor websites for:

- Server/DNS issues
- SSL certificate expiry
- Domain expiry

## 🛠 Setup

1. Clone the repo
2. Set up `.streamlit/secrets.toml` with your Google credentials
3. Run the app:
   ```
   streamlit run app.py
   ```

## ☁️ Deploy on Streamlit Cloud

1. Push to GitHub
2. Visit [streamlit.io/cloud](https://streamlit.io/cloud)
3. Create new app → connect repo → choose `app.py`
4. Paste secrets from `.streamlit/secrets.toml` into the Secrets manager
