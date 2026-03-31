import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

# -----------------------
# AUTH (FIXED)
# -----------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"],
    scope
)

client = gspread.authorize(creds)

# -----------------------
# LOAD DATA
# -----------------------
@st.cache_data
def load_data():
    pg_file = client.open_by_key(PG_DATA_ID)
    pg_df = pd.DataFrame(pg_file.worksheet("Sheet1").get_all_records())

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

if "username" not in st.session_state:
    st.session_state.username = ""

# -----------------------
# LOGIN
# -----------------------
if not st.session_state.login:

    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = owners_df[
            (owners_df["username"] == username) &
            (owners_df["password"] == password)
        ]

        if not user.empty:
            st.session_state.login = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid Owner Login ❌")

# -----------------------
# OWNER DASHBOARD
# -----------------------
else:

    if st.button("Logout"):
        st.session_state.login = False
        st.rerun()

    owner_data = owners_df[owners_df["username"] == st.session_state.username]

    if owner_data.empty:
        st.error("Owner data missing ❌")
        st.stop()

    owner_pg_id = owner_data.iloc[0]["pg_id"]
    owner_pg_name = owner_data.iloc[0]["pg_name"]

    st.title(f"🏠 {owner_pg_name}")

    # -----------------------
    # ROOMS
    # -----------------------
    st.subheader("🛏 Rooms")

    owner_rooms = rooms_df[rooms_df["pg_id"] == owner_pg_id]

    st.dataframe(owner_rooms)

    # -----------------------
    # ADD ROOM
    # -----------------------
    st.subheader("➕ Add Room")

    room_no = st.text_input("Room Number")
    floor = st.number_input("Floor", min_value=0, step=1)
    sharing = st.selectbox("Sharing", [1,2,3,4,5])
    total_beds = st.number_input("Total Beds", min_value=1, step=1)

    # ✅ LOGIC: available <= total & sharing
    max_beds = min(sharing, total_beds)

    available_beds = st.number_input(
        "Available Beds",
        min_value=0,
        max_value=max_beds,
        step=1
    )

    if st.button("Add Room"):

        if not room_no:
            st.error("Enter Room Number")
        else:
            try:
                new_row = [
                    owner_pg_id,
                    owner_pg_name,
                    room_no,
                    floor,
                    sharing,
                    available_beds,
                    total_beds,
                    pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                ]

                rooms_sheet.append_row(new_row)

                st.success("Room Added ✅")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    # -----------------------
    # BOOKINGS
    # -----------------------
    st.subheader("📋 Bookings")

    if not bookings_df.empty and "pg_id" in bookings_df.columns:
        owner_bookings = bookings_df[bookings_df["pg_id"] == owner_pg_id]
        st.dataframe(owner_bookings)
    else:
        st.info("No bookings yet")