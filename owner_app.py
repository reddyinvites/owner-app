import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

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
@st.cache_data(ttl=10)
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
    st.session_state.role = None

if "username" not in st.session_state:
    st.session_state.username = ""

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
            if username == ADMIN_USER and password == ADMIN_PASS:
                st.session_state.login = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Invalid Admin Login ❌")

        # OWNER LOGIN
        else:
            owner_data = owners_df[
                (owners_df["username"].astype(str).str.strip() == username.strip()) &
                (owners_df["password"].astype(str).str.strip() == password.strip())
            ]

            if not owner_data.empty:
                st.session_state.login = True
                st.session_state.role = "owner"
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid Owner Login ❌")

# -----------------------
# ADMIN DASHBOARD
# -----------------------
elif st.session_state.role == "admin":

    st.title("🛠 Admin Dashboard")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.subheader("➕ Create Owner")

    pg_names = pg_df["pg_name"].dropna().unique().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    username = st.text_input("Owner Username")
    password = st.text_input("Owner Password")

    if st.button("Create Owner"):
        if username and password and selected_pg:

            pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

            owners_sheet.append_row([username, password, pg_id, selected_pg])

            st.success("Owner Created ✅")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("All fields required")

    st.subheader("📋 Owners List")
    st.dataframe(owners_df)

    st.subheader("❌ Delete Owner")

    owner_list = owners_df["username"].tolist()

    delete_user = st.selectbox("Select Owner", owner_list)

    if st.button("Delete Owner"):
        records = owners_sheet.get_all_values()

        for i, row in enumerate(records):
            if row[0] == delete_user:
                owners_sheet.delete_rows(i + 1)
                st.success("Deleted ✅")
                st.cache_data.clear()
                st.rerun()

# -----------------------
# OWNER DASHBOARD
# -----------------------
elif st.session_state.role == "owner":

    st.title("🏠 Owner Dashboard")

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

    st.header(owner_pg_name)

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
    floor = st.number_input("Floor", min_value=0)
    sharing = st.selectbox("Sharing", [1, 2, 3, 4])
    total_beds = st.number_input("Total Beds", min_value=1)

    if st.button("Add Room"):
        if room_no:

            rooms_sheet.append_row([
                owner_pg_id,
                owner_pg_name,
                room_no,
                floor,
                sharing,
                total_beds,
                total_beds,
                pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
            ])

            st.success("Room Added ✅")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Enter room number")

    # -----------------------
    # BOOKINGS
    # -----------------------
    st.subheader("📋 Bookings")

    if "pg_id" in bookings_df.columns:
        owner_bookings = bookings_df[bookings_df["pg_id"] == owner_pg_id]
        st.dataframe(owner_bookings)
    else:
        st.warning("No bookings data")