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

# ✅ IMPORTANT: Correct sheet names
pg_sheet = sheet.worksheet("Sheet1")   # PG DATA
owner_sheet = sheet.worksheet("Owners")  # OWNERS

# -------- LOAD DATA --------
def load_data():
    pg_df = pd.DataFrame(pg_sheet.get_all_records())
    owner_df = pd.DataFrame(owner_sheet.get_all_records())

    # CLEAN COLUMN NAMES
    if not pg_df.empty:
        pg_df.columns = pg_df.columns.astype(str).str.strip().str.lower()

    if not owner_df.empty:
        owner_df.columns = owner_df.columns.astype(str).str.strip().str.lower()

    return pg_df, owner_df

pg_df, owner_df = load_data()

st.success("✅ Connected to Google Sheets")

# -------- CLEAN PG DATA --------
pg_list = []

if not pg_df.empty and "pg_name" in pg_df.columns:
    pg_df = pg_df.drop_duplicates()

    pg_df = pg_df[pg_df["pg_name"].astype(str).str.strip() != ""]

    pg_list = pg_df["pg_name"].astype(str).str.strip().tolist()

# -------- ADMIN LOGIN --------
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

# ✅ CLEAN DROPDOWN
selected_pg = st.selectbox("Select PG", pg_list)

# GET PG ID FROM NAME
pg_id = ""

if selected_pg:
    row = pg_df[pg_df["pg_name"] == selected_pg]
    if not row.empty:
        pg_id = row.iloc[0]["pg_id"]

if st.button("Create Owner"):

    if username.strip() == "" or password.strip() == "" or selected_pg == "":
        st.error("All fields required")

    else:
        # CHECK DUPLICATE USER
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