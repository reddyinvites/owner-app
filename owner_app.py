import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# -----------------------
# AUTH
# -----------------------
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

if "user" not in st.session_state:
    st.session_state.user = ""

# -----------------------
# LOGIN
# -----------------------
if not st.session_state.login:

    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # 🔥 FIX: safe match
        owner_data = owners_df[
            (owners_df["username"].astype(str).str.strip() == username.strip()) &
            (owners_df["password"].astype(str).str.strip() == password.strip())
        ]

        if not owner_data.empty:
            st.session_state.login = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Invalid Login ❌")

# -----------------------
# OWNER DASHBOARD
# -----------------------
else:

    st.button("Logout", on_click=lambda: st.session_state.update({"login": False}))

    owner_data = owners_df[
        owners_df["username"].astype(str).str.strip() == st.session_state.user
    ]

    # 🔥 SAFETY FIX
    if owner_data.empty:
        st.error("Owner data missing ❌")
        st.stop()

    owner_pg_id = str(owner_data.iloc[0]["pg_id"])
    owner_pg_name = owner_data.iloc[0]["pg_name"]

    st.title(f"🏠 {owner_pg_name}")

    # -----------------------
    # ROOMS
    # -----------------------
    st.subheader("🛏 Rooms")

    owner_rooms = rooms_df[
        rooms_df["pg_id"].astype(str) == owner_pg_id
    ]

    st.dataframe(owner_rooms)

    # -----------------------
    # ADD ROOM
    # -----------------------
    st.subheader("➕ Add Room")

    room_no = st.text_input("Room Number")
    floor = st.number_input("Floor", 1, 10, 1)
    sharing = st.selectbox("Sharing", [1,2,3,4])
    total_beds = st.number_input("Total Beds", 1, 10, 1)

    if st.button("Add Room"):

        if room_no:

            try:
                rooms_sheet.append_row([
                    owner_pg_id,
                    owner_pg_name,
                    room_no,
                    floor,
                    sharing,
                    total_beds,
                    total_beds,
                    datetime.now().strftime("%Y-%m-%d %H:%M")
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

    if not bookings_df.empty and "pg_id" in bookings_df.columns:

        owner_bookings = bookings_df[
            bookings_df["pg_id"].astype(str) == owner_pg_id
        ]

        st.dataframe(owner_bookings)

    else:
        st.info("No bookings yet")