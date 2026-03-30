import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

# -----------------------
# AUTH
# -----------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

# -----------------------
# LOAD DATA
# -----------------------
@st.cache_data
def load_data():
    # ✅ FILE 1 → pg_data
    pg_file = client.open_by_key(PG_DATA_ID)
    pg_sheet = pg_file.worksheet("Sheet1")   # ✅ correct
    pg_df = pd.DataFrame(pg_sheet.get_all_records())

    # ✅ FILE 2 → pg_availability
    app_file = client.open_by_key(PG_APP_ID)

    owners_sheet = app_file.worksheet("Owners")
    rooms_sheet = app_file.worksheet("rooms")
    bookings_sheet = app_file.worksheet("Bookings")

    owners_df = pd.DataFrame(owners_sheet.get_all_records())

    return pg_df, owners_df, owners_sheet

pg_df, owners_df, owners_sheet = load_data()

# -----------------------
# UI
# -----------------------
st.title("🏠 PG Management System")

st.success("✅ Connected Successfully")

# -----------------------
# DROPDOWN (PG LIST)
# -----------------------
pg_names = pg_df["pg_name"].dropna().unique().tolist()

selected_pg = st.selectbox("Select PG", pg_names)

# -----------------------
# CREATE OWNER
# -----------------------
st.subheader("➕ Create Owner")

username = st.text_input("Username")
password = st.text_input("Password")

if st.button("Create Owner"):
    if username and password and selected_pg:

        pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

        owners_sheet.append_row([username, password, pg_id, selected_pg])

        st.success("Owner Created ✅")
        st.cache_data.clear()

    else:
        st.error("All fields required")

# -----------------------
# SHOW OWNERS
# -----------------------
st.subheader("📋 Owners List")
st.dataframe(owners_df)