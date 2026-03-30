import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# -----------------------
# CONFIG
# -----------------------
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
    file = client.open_by_key(PG_APP_ID)

    owners_sheet = file.worksheet("Owners")
    rooms_sheet = file.worksheet("rooms")

    owners_df = pd.DataFrame(owners_sheet.get_all_records())
    rooms_df = pd.DataFrame(rooms_sheet.get_all_records())

    return owners_df, rooms_df, owners_sheet, rooms_sheet

owners_df, rooms_df, owners_sheet, rooms_sheet = load_data()

# -----------------------
# HEADER
# -----------------------
st.title("🏠 Admin Dashboard")
st.success("✅ Logged In")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# -----------------------
# ADD PG
# -----------------------
st.subheader("➕ Add PG")

pg_name = st.text_input("PG Name")

if st.button("Add PG"):
    if pg_name:
        new_id = f"PG{len(owners_df)+1:03}"

        owners_sheet.append_row(["", "", new_id, pg_name])

        st.success("PG Added ✅")
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("Enter PG name")

# -----------------------
# DELETE PG
# -----------------------
st.subheader("🗑 Delete PG")

pg_list = owners_df["pg_name"].dropna().tolist()

selected_pg = st.selectbox("Select PG", pg_list)

if st.button("Delete PG"):
    row_index = owners_df[owners_df["pg_name"] == selected_pg].index[0] + 2
    owners_sheet.delete_rows(row_index)

    st.success("Deleted ✅")
    st.cache_data.clear()
    st.rerun()

# -----------------------
# ADD ROOM
# -----------------------
st.subheader("🛏 Add Room")

pg_list = owners_df["pg_name"].dropna().tolist()
selected_pg = st.selectbox("Select PG for Room", pg_list)

room_no = st.text_input("Room No")
floor = st.text_input("Floor")
sharing = st.text_input("Sharing")
beds = st.number_input("Available Beds", 0)

if st.button("Add Room"):
    if selected_pg and room_no:
        pg_id = owners_df[owners_df["pg_name"] == selected_pg]["pg_id"].values[0]

        rooms_sheet.append_row([
            pg_id,
            selected_pg,
            room_no,
            floor,
            sharing,
            beds,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ])

        st.success("Room Added ✅")
        st.cache_data.clear()
        st.rerun()

# -----------------------
# TABLES
# -----------------------
st.subheader("📋 Owners")
st.dataframe(owners_df)

st.subheader("📋 Rooms")
st.dataframe(rooms_df)