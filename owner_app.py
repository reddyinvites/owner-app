import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="PG Management System", layout="centered")

st.title("🏠 PG Management System")

# -------- GOOGLE SHEETS CONNECTION --------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

SHEET_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

sheet = client.open_by_key(SHEET_ID)

# -------- SAFE SHEET LOADING (FIX ERROR) --------
pg_sheet = None
owner_sheet = None

for ws in sheet.worksheets():
    name = ws.title.strip().lower()

    if name == "sheet1":
        pg_sheet = ws

    if name == "owners":
        owner_sheet = ws

if pg_sheet is None:
    st.error("❌ Sheet1 not found")
    st.write([ws.title for ws in sheet.worksheets()])
    st.stop()

if owner_sheet is None:
    st.error("❌ Owners sheet not found")
    st.stop()

st.success("✅ Connected to Google Sheets")

# -------- LOAD DATA --------
def load_data():
    pg_df = pd.DataFrame(pg_sheet.get_all_records())
    owner_df = pd.DataFrame(owner_sheet.get_all_records())

    if not pg_df.empty:
        pg_df.columns = pg_df.columns.astype(str).str.strip().str.lower()

    if not owner_df.empty:
        owner_df.columns = owner_df.columns.astype(str).str.strip().str.lower()

    return pg_df, owner_df

pg_df, owner_df = load_data()

# -------- CLEAN PG LIST --------
pg_list = []

if not pg_df.empty and "pg_name" in pg_df.columns:
    pg_df = pg_df.drop_duplicates()

    pg_df = pg_df[pg_df["pg_name"].astype(str).str.strip() != ""]

    pg_list = pg_df["pg_name"].astype(str).str.strip().tolist()

# -------- LOGIN --------
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.subheader("🔐 Admin Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == "admin" and pwd == "admin123":
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Invalid login")

    st.stop()

# -------- ADMIN DASHBOARD --------
st.header("🧑‍💼 Admin Dashboard")

st.subheader("➕ Create Owner")

username = st.text_input("Login Username")
password = st.text_input("Password", type="password")

# -------- DROPDOWN --------
selected_pg = st.selectbox("Select PG", pg_list)

# -------- GET PG ID --------
pg_id = ""

if selected_pg:
    row = pg_df[pg_df["pg_name"] == selected_pg]
    if not row.empty:
        pg_id = row.iloc[0]["pg_id"]

# -------- CREATE OWNER --------
if st.button("Create Owner"):

    if username.strip() == "" or password.strip() == "" or selected_pg == "":
        st.error("All fields required")

    else:
        # DUPLICATE CHECK
        if not owner_df.empty:
            users = owner_df["username"].astype(str).str.strip().tolist()
            if username.strip() in users:
                st.error("❌ Username already exists")
                st.stop()

        owner_sheet.append_row([
            username.strip(),
            password.strip(),
            pg_id,
            selected_pg
        ])

        st.success("🎉 Owner Created Successfully")
        st.rerun()

# -------- OWNERS LIST --------
st.subheader("📋 Owners List")

if not owner_df.empty:
    st.dataframe(owner_df)
else:
    st.info("No owners yet")

# -------- LOGOUT --------
if st.button("🚪 Logout"):
    st.session_state.login = False
    st.rerun()