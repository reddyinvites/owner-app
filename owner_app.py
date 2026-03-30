import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random

st.set_page_config(page_title="PG PRO Management System", layout="centered")

st.title("🏠 PG PRO Management System")

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

# ⚠️ Sheet names MUST match exactly
owner_sheet = sheet.worksheet("Owners")
room_sheet = sheet.worksheet("rooms")

st.success("✅ Connected to Google Sheets")

# -------- LOAD DATA --------
@st.cache_data(ttl=10)
def load_data():
    owners = pd.DataFrame(owner_sheet.get_all_records())
    rooms = pd.DataFrame(room_sheet.get_all_records())

    # safe column handling
    if not owners.empty:
        owners.columns = owners.columns.astype(str)

    if not rooms.empty:
        rooms.columns = rooms.columns.astype(str)

    return owners, rooms

owner_df, room_df = load_data()

# -------- GENERATE PG ID --------
def generate_pg_id():
    return "PG" + str(random.randint(1000, 9999))

# -------- SESSION --------
if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= LOGIN =================
if st.session_state.page == "login":

    st.subheader("🔐 Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # ADMIN LOGIN
        if role == "Admin":
            if username == "admin" and password == "admin123":
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("Invalid admin login")

        # OWNER LOGIN
        else:
            if not owner_df.empty:

                user = owner_df[
                    (owner_df["username"].astype(str) == username) &
                    (owner_df["password"].astype(str) == password)
                ]

                if not user.empty:
                    st.session_state.page = "owner"
                    st.session_state.pg_id = user.iloc[0]["pg_id"]
                    st.session_state.pg_name = user.iloc[0]["pg_name"]
                    st.rerun()
                else:
                    st.error("Invalid owner login")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    st.subheader("➕ Create Owner")

    pg_name = st.text_input("PG Name")
    username = st.text_input("Login Username")
    password = st.text_input("Password")

    if st.button("Create Owner"):

        if not pg_name or not username or not password:
            st.error("All fields required")

        else:
            # Duplicate Username
            if not owner_df.empty:
                if username in owner_df["username"].astype(str).tolist():
                    st.error("❌ Username already exists")
                    st.stop()

                if "pg_name" in owner_df.columns:
                    if pg_name in owner_df["pg_name"].astype(str).tolist():
                        st.error("❌ PG already exists")
                        st.stop()

            pg_id = generate_pg_id()

            owner_sheet.append_row([
                username,
                password,
                pg_id,
                pg_name
            ])

            st.success(f"🎉 Owner Created | PG ID: {pg_id}")
            st.cache_data.clear()
            st.rerun()

    # OWNER LIST
    st.subheader("📋 Owners List")

    if not owner_df.empty:
        st.dataframe(owner_df, use_container_width=True)
    else:
        st.info("No owners yet")

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    pg_id = st.session_state.pg_id
    pg_name = st.session_state.pg_name

    st.info(f"PG ID: {pg_id}")
    st.info(f"PG Name: {pg_name}")

    st.subheader("➕ Add Room")

    room = st.text_input("Room No")
    floor = st.number_input("Floor", min_value=1)
    sharing = st.selectbox("Sharing", [1,2,3,4,5])
    beds = st.number_input("Available Beds", min_value=0)

    if beds > sharing:
        st.warning("Beds cannot exceed sharing")

    if st.button("Save Room"):

        if not room:
            st.error("Enter room number")

        elif beds > sharing:
            st.error("Invalid beds count")

        else:
            room_sheet.append_row([
                pg_id,
                pg_name,
                room,
                floor,
                sharing,
                beds,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])

            st.success("🎉 Room Added Successfully")
            st.cache_data.clear()
            st.rerun()

    # DISPLAY ROOMS
    st.subheader("📊 My Rooms")

    if not room_df.empty:
        my_rooms = room_df[room_df["pg_id"].astype(str) == str(pg_id)]

        if not my_rooms.empty:
            st.dataframe(my_rooms, use_container_width=True)
        else:
            st.info("No rooms added yet")
    else:
        st.info("No data")

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()