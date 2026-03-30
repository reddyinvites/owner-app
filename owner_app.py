import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "YOUR_PG_DATA_ID"
PG_APP_ID = "YOUR_APP_ID"

ADMIN_USER = "admin"
ADMIN_PASS = "1234"

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
# SESSION
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -----------------------
# LOGIN
# -----------------------
if not st.session_state.logged_in:
    st.title("🔐 Admin Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Wrong credentials")

    st.stop()

# -----------------------
# LOAD DATA
# -----------------------
@st.cache_data
def load_data():
    pg_file = client.open_by_key(PG_DATA_ID)
    pg_sheet = pg_file.worksheet("Sheet1")
    pg_df = pd.DataFrame(pg_sheet.get_all_records())

    app_file = client.open_by_key(PG_APP_ID)
    owners_sheet = app_file.worksheet("Owners")
    owners_df = pd.DataFrame(owners_sheet.get_all_records())

    return pg_df, pg_sheet, owners_df, owners_sheet

pg_df, pg_sheet, owners_df, owners_sheet = load_data()

# -----------------------
# HEADER
# -----------------------
st.title("🏠 PG Management System")
st.success("✅ Admin Logged In")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# -----------------------
# ADD PG
# -----------------------
st.subheader("➕ Add New PG")

pg_name = st.text_input("PG Name")
location = st.text_input("Location")
owner_name = st.text_input("Owner Name")
owner_number = st.text_input("Owner Phone")

if st.button("Add PG"):
    if pg_name and location:
        new_id = f"PG{len(pg_df)+1:03}"

        pg_sheet.append_row([
            new_id,
            pg_name,
            location,
            owner_name,
            owner_number,
            "[]"
        ])

        st.success("PG Added ✅")
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("Fill required fields")

# -----------------------
# PG TABLE
# -----------------------
st.subheader("📋 PG List")
st.dataframe(pg_df)

# -----------------------
# DELETE PG
# -----------------------
st.subheader("🗑 Delete PG")

pg_list = pg_df["pg_name"].tolist()

selected_pg = st.selectbox("Select PG to Delete", pg_list)

if st.button("Delete PG"):
    row_index = pg_df[pg_df["pg_name"] == selected_pg].index[0] + 2
    pg_sheet.delete_rows(row_index)

    st.success("PG Deleted ✅")
    st.cache_data.clear()
    st.rerun()

# -----------------------
# CREATE OWNER
# -----------------------
st.subheader("➕ Create Owner")

pg_names = pg_df["pg_name"].tolist()
selected_pg = st.selectbox("Select PG", pg_names)

username = st.text_input("Username")
password = st.text_input("Password")

if st.button("Create Owner"):
    if username and password:
        pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

        owners_sheet.append_row([username, password, pg_id, selected_pg])

        st.success("Owner Created ✅")
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("Fill all fields")

# -----------------------
# OWNERS LIST
# -----------------------
st.subheader("📋 Owners List")
st.dataframe(owners_df)