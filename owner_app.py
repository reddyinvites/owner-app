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
# SESSION STATE
# -----------------------
if "role" not in st.session_state:
    st.session_state.role = None

if "user" not in st.session_state:
    st.session_state.user = None

# -----------------------
# LOGIN SCREEN
# -----------------------
if st.session_state.role is None:

    st.title("🔐 Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # -----------------------
        # ADMIN LOGIN
        # -----------------------
        if role == "Admin":
            if username == ADMIN_USER and password == ADMIN_PASS:
                st.session_state.role = "admin"
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Invalid Admin Login ❌")

        # -----------------------
        # OWNER LOGIN (FIXED)
        # -----------------------
        else:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=scope
            )

            client = gspread.authorize(creds)
            app_file = client.open_by_key(PG_APP_ID)
            owners_sheet = app_file.worksheet("Owners")

            owners_df = pd.DataFrame(owners_sheet.get_all_records())

            # 🔥 FIX LOGIN BUG (strip + lower)
            owners_df["username"] = owners_df["username"].astype(str).str.strip().str.lower()
            owners_df["password"] = owners_df["password"].astype(str).str.strip()

            username_clean = username.strip().lower()
            password_clean = password.strip()

            user_row = owners_df[
                (owners_df["username"] == username_clean) &
                (owners_df["password"] == password_clean)
            ]

            if not user_row.empty:
                st.session_state.role = "owner"
                st.session_state.user = username_clean
                st.session_state.pg_id = user_row.iloc[0]["pg_id"]
                st.session_state.pg_name = user_row.iloc[0]["pg_name"]
                st.rerun()
            else:
                st.error("Invalid Owner Login ❌")

    st.stop()

# -----------------------
# GOOGLE AUTH (AFTER LOGIN)
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

# -----------------------
# LOGOUT
# -----------------------
if st.button("Logout"):
    st.session_state.role = None
    st.session_state.user = None
    st.rerun()

# =======================
# ADMIN DASHBOARD
# =======================
if st.session_state.role == "admin":

    st.title("🏠 Admin Dashboard")

    pg_names = pg_df["pg_name"].dropna().unique().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

    # CREATE OWNER
    st.subheader("➕ Create Owner")

    username = st.text_input("Username")
    password = st.text_input("Password")

    if st.button("Create Owner"):

        if username and password:

            if username in owners_df["username"].values:
                st.error("Username already exists ❌")
            else:
                owners_sheet.append_row([
                    username.strip(),
                    password.strip(),
                    pg_id,
                    selected_pg
                ])

                st.success("Owner Created ✅")
                st.rerun()

    # OWNER LIST
    st.subheader("📋 Owners List")
    st.dataframe(owners_df)

    # DELETE OWNER
    st.subheader("❌ Delete Owner")

    if not owners_df.empty:
        selected_user = st.selectbox("Select Owner", owners_df["username"])

        if st.button("Delete Owner"):
            cell = owners_sheet.find(selected_user)
            if cell:
                owners_sheet.delete_rows(cell.row)
                st.success("Deleted ✅")
                st.rerun()

# =======================
# OWNER DASHBOARD
# =======================
elif st.session_state.role == "owner":

    st.title(f"🏠 {st.session_state.pg_name}")

    owner_pg_id = st.session_state.pg_id

    # ROOMS
    st.subheader("🛏 Rooms")
    owner_rooms = rooms_df[rooms_df["pg_id"] == owner_pg_id]
    st.dataframe(owner_rooms)

    # BOOKINGS
    st.subheader("📑 Bookings")
    owner_bookings = bookings_df[bookings_df["pg_id"] == owner_pg_id]
    st.dataframe(owner_bookings)