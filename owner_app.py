import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="PG Management System")

st.title("🏠 PG Management System")

# GOOGLE AUTH
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

# ✅ YOUR PG DATA FILE
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

try:
    pg_file = client.open_by_key(PG_DATA_ID)
    pg_sheet = pg_file.worksheet("Sheet1")  # EXACT NAME
    st.success("✅ PG DATA Connected")

    data = pd.DataFrame(pg_sheet.get_all_records())
    st.dataframe(data)

except Exception as e:
    st.error("❌ Connection Failed")
    st.write(str(e))