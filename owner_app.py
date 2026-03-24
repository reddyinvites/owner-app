import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="PG Management", layout="centered")

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

room_sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")
owner_sheet = client.open_by_key(SHEET_ID).worksheet("Owners")

# -------- LOAD DATA --------
room_df = pd.DataFrame(room_sheet.get_all_records())
owner_df = pd.DataFrame(owner_sheet.get_all_records())

# -------- LOGIN RESET FIX --------
if "username_input" not in st.session_state:
    st.session_state.username_input = ""

if "password_input" not in st.session_state:
    st.session_state.password_input = ""

# -------- ROLE SELECT --------
role = st.selectbox("Login as", ["Owner", "Admin"])

# ================= ADMIN =================
if role == "Admin":

    st.header("🧑‍💼 Admin Panel")

    admin_user = st.text_input("Admin Username")
    admin_pass = st.text_input("Admin Password", type="password")

    if admin_user == "admin" and admin_pass == "admin123":

        st.success("✅ Admin Logged In")

        # -------- CREATE OWNER --------
        st.subheader("➕ Create PG Owner")

        col1, col2 = st.columns(2)

        with col1:
            new_pg = st.text_input("🏠 PG Name")

        with col2:
            new_user = st.text_input("👤 Username")

        new_pass = st.text_input("🔐 Password", type="password")

        if st.button("🚀 Create Owner"):

            if new_pg and new_user and new_pass:

                owner_sheet.append_row([
                    new_user,
                    new_pass,
                    new_pg
                ])

                st.session_state.username_input = ""
                st.session_state.password_input = ""

                st.success("✅ Owner Created")
                st.rerun()

            else:
                st.error("⚠️ Fill all fields")

        st.markdown("---")

        # -------- OWNERS TABLE --------
        st.subheader("📋 All PG Owners")

        if not owner_df.empty:

            display_df = owner_df.copy()
            display_df.columns = ["👤 Username", "🔐 Password", "🏠 PG Name"]

            search = st.text_input("🔍 Search Owner")

            if search:
                display_df = display_df[
                    display_df["👤 Username"].str.contains(search, case=False)
                ]

            st.dataframe(display_df, use_container_width=True)

        else:
            st.info("No owners available")

        st.markdown("---")

        # -------- ALL PG DASHBOARD --------
        st.header("📊 All PGs Dashboard")

        if not room_df.empty:

            room_df["floor"] = pd.to_numeric(room_df["floor"], errors="coerce")
            room_df["room_no"] = pd.to_numeric(room_df["room_no"], errors="coerce")
            room_df["sharing"] = pd.to_numeric(room_df["sharing"], errors="coerce")
            room_df["available_beds"] = pd.to_numeric(room_df["available_beds"], errors="coerce")

            total_rooms = len(room_df)
            total_beds = room_df["sharing"].sum()
            available_beds = room_df["available_beds"].sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("🏠 Total Rooms", total_rooms)
            col2.metric("🛏 Total Beds", total_beds)
            col3.metric("📉 Available Beds", available_beds)

            st.markdown("---")

            pgs = room_df["pg_name"].dropna().unique()

            for pg in pgs:

                st.markdown(f"## 🏠 {pg}")

                pg_df = room_df[room_df["pg_name"] == pg]
                pg_df = pg_df.sort_values(by=["floor", "room_no"])

                for f in pg_df["floor"].dropna().unique():
                    st.markdown(f"### 🏢 Floor {int(f)}")
                    floor_df = pg_df[pg_df["floor"] == f]
                    st.dataframe(floor_df, use_container_width=True)

                st.markdown("---")

        else:
            st.info("No PG data")

    else:
        st.info("🔐 Enter admin credentials")

# ================= OWNER =================
else:

    if "login" not in st.session_state:
        st.session_state.login = False

    if not st.session_state.login:

        st.subheader("🔐 Owner Login")

        username = st.text_input("Username", key="username_input")
        password = st.text_input("Password", type="password", key="password_input")

        if st.button("Login"):

            user = owner_df[
                (owner_df["username"] == username) &
                (owner_df["password"] == password)
            ]

            if not user.empty:
                st.session_state.login = True
                st.session_state.username = username
                st.session_state.pg = user.iloc[0]["pg_name"]

                st.session_state.username_input = ""
                st.session_state.password_input = ""

                st.success("✅ Login successful")
                st.rerun()
            else:
                st.error("❌ Invalid login")

        st.stop()

    # -------- OWNER DASHBOARD --------
    owner_pg = st.session_state.pg
    owner_id = st.session_state.username

    st.success(f"👤 Logged in as: {owner_id}")
    st.info(f"🏠 PG: {owner_pg}")

    if not room_df.empty:
        room_df = room_df[room_df["owner_id"] == owner_id]

    # -------- ADD ROOM --------
    st.subheader("➕ Add Room")

    room_no = st.text_input("Room Number")
    floor = st.number_input("Floor", min_value=1, step=1)
    sharing = st.selectbox("Sharing", [1,2,3,4,5,6])
    beds = st.number_input("Available Beds", min_value=0, max_value=sharing)

    if st.button("💾 Save Room"):

        room_sheet.append_row([
            owner_pg,
            room_no,
            floor,
            sharing,
            beds,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            owner_id
        ])

        st.success("Room Added")
        st.rerun()

    # -------- DISPLAY --------
    st.subheader("📊 Your Rooms")

    if not room_df.empty:
        room_df = room_df.sort_values(by=["floor", "room_no"])

        for f in room_df["floor"].unique():
            st.markdown(f"### 🏢 Floor {int(f)}")
            st.dataframe(room_df[room_df["floor"] == f], use_container_width=True)
    else:
        st.info("No rooms yet")

    # -------- LOGOUT --------
    if st.button("🚪 Logout"):
        st.session_state.login = False
        st.rerun()