import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

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
    pg_file = client.open_by_key(PG_DATA_ID)
    pg_sheet = pg_file.worksheet("Sheet1")
    pg_df = pd.DataFrame(pg_sheet.get_all_records())

    app_file = client.open_by_key(PG_APP_ID)
    owners_sheet = app_file.worksheet("Owners")
    rooms_sheet = app_file.worksheet("rooms")
    bookings_sheet = app_file.worksheet("Bookings")

    owners_df = pd.DataFrame(owners_sheet.get_all_records())
    rooms_df = pd.DataFrame(rooms_sheet.get_all_records())
    bookings_df = pd.DataFrame(bookings_sheet.get_all_records())

    return pg_df, owners_df, rooms_df, bookings_df, owners_sheet, rooms_sheet

pg_df, owners_df, rooms_df, bookings_df, owners_sheet, rooms_sheet = load_data()

# -----------------------
# SESSION
# -----------------------
if "login" not in st.session_state:
    st.session_state.login = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "user" not in st.session_state:
    st.session_state.user = ""

# -----------------------
# LOGIN PAGE
# -----------------------
if not st.session_state.login:

    st.title("🔐 Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # ADMIN LOGIN
        if role == "Admin":
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state.login = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Invalid Admin Login ❌")

        # OWNER LOGIN
        else:
            owner = owners_df[
                (owners_df["username"].astype(str).str.strip() == username.strip()) &
                (owners_df["password"].astype(str).str.strip() == password.strip())
            ]

            if not owner.empty:
                st.session_state.login = True
                st.session_state.role = "owner"
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Invalid Owner Login ❌")

# -----------------------
# LOGOUT
# -----------------------
if st.session_state.login:
    if st.button("Logout"):
        st.session_state.login = False
        st.rerun()

# -----------------------
# ADMIN DASHBOARD
# -----------------------
if st.session_state.login and st.session_state.role == "admin":

    st.title("🏠 Admin Dashboard")

    st.success("Connected Successfully ✅")

    # -----------------------
    # CREATE OWNER
    # -----------------------
    st.subheader("➕ Create Owner")

    pg_names = pg_df["pg_name"].dropna().unique().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    username = st.text_input("Username")
    password = st.text_input("Password")

    if st.button("Create Owner"):
        if username and password:

            pg_row = pg_df[pg_df["pg_name"] == selected_pg]

            if not pg_row.empty:
                pg_id = pg_row.iloc[0]["pg_id"]

                owners_sheet.append_row([username, password, pg_id, selected_pg])

                st.success("Owner Created ✅")
                st.cache_data.clear()
                st.rerun()

    # -----------------------
    # OWNER LIST
    # -----------------------
    st.subheader("📋 Owners List")
    st.dataframe(owners_df)

    # -----------------------
    # DELETE OWNER
    # -----------------------
    st.subheader("❌ Delete Owner")

    owner_list = owners_df["username"].tolist()
    selected_owner = st.selectbox("Select Owner", owner_list)

    if st.button("Delete Owner"):
        cell = owners_sheet.find(selected_owner)
        owners_sheet.delete_rows(cell.row)
        st.success("Deleted ✅")
        st.cache_data.clear()
        st.rerun()

# -----------------------
# OWNER DASHBOARD
# -----------------------
if st.session_state.login and st.session_state.role == "owner":

    owner_data = owners_df[owners_df["username"] == st.session_state.user]

    if owner_data.empty:
        st.error("Owner data missing ❌")
        st.stop()

    owner_pg_id = owner_data.iloc[0]["pg_id"]
    owner_pg_name = owner_data.iloc[0]["pg_name"]

    st.title(f"🏠 {owner_pg_name}")

    # -----------------------
    # ROOMS VIEW
    # -----------------------
    st.subheader("🛏 Rooms")

    owner_rooms = rooms_df[rooms_df["pg_id"] == owner_pg_id]
    st.dataframe(owner_rooms)

    # -----------------------
    # ADD ROOM
    # -----------------------
    st.subheader("➕ Add Room")

    room_no = st.text_input("Room Number")
    floor = st.number_input("Floor", 0, 50)
    sharing = st.selectbox("Sharing", [1, 2, 3, 4])
    total_beds = st.number_input("Total Beds", 1, 10)
    available_beds = total_beds

    if st.button("Add Room"):

        try:
            rooms_sheet.append_row([
                owner_pg_id,
                owner_pg_name,
                room_no,
                floor,
                sharing,
                available_beds,
                total_beds,
                pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
            ])

            st.success("Room Added ✅")
            st.cache_data.clear()
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")

    # -----------------------
    # BOOKINGS
    # -----------------------
    st.subheader("📋 Bookings")

    if "pg_id" in bookings_df.columns:
        owner_bookings = bookings_df[bookings_df["pg_id"] == owner_pg_id]
        st.dataframe(owner_bookings)
    else:
        st.warning("Bookings sheet missing pg_id column ⚠️")