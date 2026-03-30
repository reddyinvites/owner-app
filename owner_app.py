import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("🏠 PG Management System")

# -------- GOOGLE AUTH --------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

# 🔥 TWO DIFFERENT SHEETS

PG_DATA_ID = "👉 PASTE pg_data FILE ID HERE"
PG_AVAIL_ID = "👉 PASTE pg_availability FILE ID HERE"

pg_data_file = client.open_by_key(PG_DATA_ID)
pg_avail_file = client.open_by_key(PG_AVAIL_ID)

# -------- SHEETS --------
pg_sheet = pg_data_file.worksheet("Sheet1")   # PG DATA
rooms_sheet = pg_avail_file.worksheet("rooms")
owner_sheet = pg_avail_file.worksheet("Owners")

st.success("✅ Connected to both sheets")

# -------- LOAD DATA --------
pg_df = pd.DataFrame(pg_sheet.get_all_records())
owner_df = pd.DataFrame(owner_sheet.get_all_records())

if not pg_df.empty:
    pg_df.columns = pg_df.columns.str.strip().str.lower()

if not owner_df.empty:
    owner_df.columns = owner_df.columns.str.strip().str.lower()

# -------- PG LIST --------
pg_list = []

if not pg_df.empty:
    pg_df = pg_df[pg_df["pg_name"].astype(str).str.strip() != ""]
    pg_list = pg_df["pg_name"].tolist()

# -------- UI --------
st.subheader("➕ Create Owner")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

selected_pg = st.selectbox("Select PG", pg_list)

pg_id = ""

if selected_pg:
    row = pg_df[pg_df["pg_name"] == selected_pg]
    if not row.empty:
        pg_id = row.iloc[0]["pg_id"]

if st.button("Create Owner"):

    if username == "" or password == "" or selected_pg == "":
        st.error("All fields required")

    else:
        owner_sheet.append_row([
            username,
            password,
            pg_id,
            selected_pg
        ])

        st.success("Owner Created 🎉")
        st.rerun()

# -------- VIEW OWNERS --------
st.subheader("📋 Owners")

if not owner_df.empty:
    st.dataframe(owner_df)