import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

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
@st.cache_data(ttl=5)
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

    return pg_df, owners_df, rooms_df, bookings_df, owners_sheet, rooms_sheet, bookings_sheet

pg_df, owners_df, rooms_df, bookings_df, owners_sheet, rooms_sheet, bookings_sheet = load_data()

# -----------------------
# SESSION
# -----------------------
if "login" not in st.session_state:
    st.session_state.login = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "username" not in st.session_state:
    st.session_state.username = ""

# -----------------------
# LOGIN
# -----------------------
if not st.session_state.login:

    st.title("🔐 Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # ADMIN
        if role == "Admin":
            if username == ADMIN_USER and password == ADMIN_PASS:
                st.session_state.login = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Invalid Admin ❌")

        # OWNER
        else:
            owner = owners_df[
                (owners_df["username"].astype(str).str.strip() == username.strip()) &
                (owners_df["password"].astype(str).str.strip() == password.strip())
            ]

            if not owner.empty:
                st.session_state.login = True
                st.session_state.role = "owner"
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid Owner ❌")

# -----------------------
# ADMIN DASHBOARD
# -----------------------
elif st.session_state.role == "admin":

    st.title("🛠 Admin Dashboard")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # CREATE OWNER
    st.subheader("➕ Create Owner")

    pg_names = pg_df["pg_name"].dropna().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    username = st.text_input("Owner Username")
    password = st.text_input("Owner Password")

    if st.button("Create Owner"):
        if username and password:

            pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

            owners_sheet.append_row([username, password, pg_id, selected_pg])

            st.success("Owner Created ✅")
            st.cache_data.clear()
            st.rerun()

    # SHOW OWNERS
    st.subheader("📋 Owners List")
    st.dataframe(owners_df)

# -----------------------
# OWNER DASHBOARD
# -----------------------
elif st.session_state.role == "owner":

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    owner_data = owners_df[
        owners_df["username"].astype(str).str.strip() == st.session_state.username.strip()
    ]

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
# ADD ROOM (UPDATED)
# -----------------------
st.subheader("➕ Add Room")

room_no = st.text_input("Room Number")

floor = st.number_input("Floor", min_value=0)

sharing = st.selectbox("Sharing", [1, 2, 3, 4])

# 👉 total beds max = sharing
total_beds = st.number_input(
    "Total Beds",
    min_value=1,
    max_value=sharing
)

# 👉 available beds max = total beds
available_beds = st.number_input(
    "Available Beds",
    min_value=0,
    max_value=total_beds
)

# -----------------------
# VALIDATION + SAVE
# -----------------------
if st.button("Add Room"):

    if not room_no:
        st.error("Enter room number ❌")

    elif total_beds > sharing:
        st.error("Total beds cannot exceed sharing ❌")

    elif available_beds > total_beds:
        st.error("Available beds cannot exceed total beds ❌")

    else:
        rooms_sheet.append_row([
            owner_pg_id,
            owner_pg_name,
            room_no,
            int(floor),
            int(sharing),
            int(available_beds),
            int(total_beds),
            pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        ])

        st.success("Room Added Successfully ✅")
        st.cache_data.clear()
        st.rerun()


    # -----------------------
    # BOOKINGS
    # -----------------------
    st.subheader("📋 Bookings")

    if "pg_id" in bookings_df.columns:
        owner_bookings = bookings_df[bookings_df["pg_id"] == owner_pg_id]
        st.dataframe(owner_bookings)
    else:
        st.warning("No bookings data")