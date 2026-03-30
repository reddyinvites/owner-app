import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -------------------------------
# GOOGLE SHEETS CONNECT
# -------------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

# -------------------------------
# YOUR FILE IDS
# -------------------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

# -------------------------------
# LOAD DATA
# -------------------------------
@st.cache_data
def load_data():
    # PG DATA FILE
    pg_data_file = client.open_by_key(PG_DATA_ID)
    pg_sheet = pg_data_file.worksheet("pg_data")
    pg_df = pd.DataFrame(pg_sheet.get_all_records())

    # APP FILE
    app_file = client.open_by_key(PG_APP_ID)
    owners_sheet = app_file.worksheet("Owners")

    owners_df = pd.DataFrame(owners_sheet.get_all_records())

    return pg_df, owners_df, owners_sheet


pg_df, owners_df, owners_sheet = load_data()

st.title("🏠 PG Management System")

# -------------------------------
# ADMIN DASHBOARD
# -------------------------------
st.subheader("👨‍💼 Admin Dashboard")

st.markdown("### ➕ Create Owner")

username = st.text_input("Login Username")
password = st.text_input("Password", type="password")

# ✅ CLEAN DROPDOWN (NO EMPTY VALUES)
pg_df = pg_df.dropna(subset=["pg_name"])
pg_names = pg_df["pg_name"].astype(str).tolist()

selected_pg = st.selectbox("Select PG", pg_names)

# -------------------------------
# CREATE OWNER
# -------------------------------
if st.button("Create Owner"):
    if username and password and selected_pg:

        # GET PG ID
        pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

        owners_sheet.append_row([
            username,
            password,
            pg_id,
            selected_pg
        ])

        st.success("✅ Owner Created Successfully")
        st.cache_data.clear()
        st.rerun()

    else:
        st.error("❌ All fields required")

# -------------------------------
# OWNERS LIST
# -------------------------------
st.subheader("📋 Owners List")

if not owners_df.empty:
    st.dataframe(owners_df)
else:
    st.info("No owners found")