import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="PG Management System", layout="centered")

st.title("🏠 PG Management System")

# -------- GOOGLE SHEETS --------
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

# SHEETS
pg_sheet = sheet.sheet1          # pg_data
owner_sheet = sheet.worksheet("Owners")
room_sheet = sheet.worksheet("rooms")

st.success("✅ Connected to Google Sheets")

# -------- LOAD DATA --------
@st.cache_data(ttl=10)
def load_data():
    pg_df = pd.DataFrame(pg_sheet.get_all_records())
    owner_df = pd.DataFrame(owner_sheet.get_all_records())
    room_df = pd.DataFrame(room_sheet.get_all_records())

    if not pg_df.empty:
        pg_df.columns = pg_df.columns.astype(str)

    if not owner_df.empty:
        owner_df.columns = owner_df.columns.astype(str)

    if not room_df.empty:
        room_df.columns = room_df.columns.astype(str)

    return pg_df, owner_df, room_df

pg_df, owner_df, room_df = load_data()

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

    username = st.text_input("Login Username")
    password = st.text_input("Password")

    # SELECT PG FROM pg_data
    if not pg_df.empty:
        pg_list = pg_df["pg_name"].astype(str).tolist()
        selected_pg = st.selectbox("Select PG", pg_list)
    else:
        st.warning("No PGs found")
        selected_pg = None

    if st.button("Create Owner"):

        if not username or not password or not selected_pg:
            st.error("All fields required")

        else:
            # GET PG ID
            selected_row = pg_df[pg_df["pg_name"] == selected_pg]

            pg_id = selected_row.iloc[0]["pg_id"]
            pg_name = selected_pg

            # DUPLICATE USERNAME CHECK
            if not owner_df.empty:
                if username in owner_df["username"].astype(str).tolist():
                    st.error("❌ Username already exists")
                    st.stop()

            # SAVE OWNER (NO NEW PG ID)
            owner_sheet.append_row([
                username,
                password,
                pg_id,
                pg_name
            ])

            st.success(f"✅ Owner Created for {pg_name} ({pg_id})")
            st.cache_data.clear()
            st.rerun()

    # OWNER LIST
    st.subheader("📋 Owners List")

    if not owner_df.empty:
        st.dataframe(owner_df, use_container_width=True)
    else:
        st.info("No owners")

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
            st.error("Invalid beds")

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

    # SHOW ROOMS
    st.subheader("📊 My Rooms")

    if not room_df.empty:
        my_rooms = room_df[room_df["pg_id"].astype(str) == str(pg_id)]

        if not my_rooms.empty:
            st.dataframe(my_rooms, use_container_width=True)
        else:
            st.info("No rooms yet")
    else:
        st.info("No data")

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()