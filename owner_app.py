import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random

st.set_page_config(page_title="PG PRO Management System", layout="centered")

st.title("🏠 PG PRO Management System")

# ---------------- GOOGLE SHEETS ----------------
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

pg_sheet = sheet.worksheet("pg_data")
room_sheet = sheet.worksheet("rooms")
owner_sheet = sheet.worksheet("Owners")

st.success("✅ Connected to Google Sheets")

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=30)
def load_data():
    pg_df = pd.DataFrame(pg_sheet.get_all_records())
    room_df = pd.DataFrame(room_sheet.get_all_records())
    owner_df = pd.DataFrame(owner_sheet.get_all_records())

    if not pg_df.empty:
        pg_df.columns = [str(c).strip().lower() for c in pg_df.columns]

    if not room_df.empty:
        room_df.columns = [str(c).strip().lower() for c in room_df.columns]

    if not owner_df.empty:
        owner_df.columns = [str(c).strip().lower() for c in owner_df.columns]

    return pg_df, room_df, owner_df

pg_df, room_df, owner_df = load_data()

# ---------------- GENERATE PG ID ----------------
def generate_pg_id():
    return "PG" + str(random.randint(1000, 9999))

# ---------------- SESSION ----------------
if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= LOGIN =================
if st.session_state.page == "login":

    st.subheader("🔐 Login")

    role = st.selectbox("Login as", ["Owner", "Admin"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if role == "Admin":
            if username == "admin" and password == "admin123":
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("Invalid admin login")

        else:
            if not owner_df.empty:

                user = owner_df[
                    (owner_df["username"].astype(str).str.strip() == username.strip()) &
                    (owner_df["password"].astype(str).str.strip() == password.strip())
                ]

                if not user.empty:
                    st.session_state.page = "owner"
                    st.session_state.owner = username.strip()
                    st.session_state.pg = user.iloc[0]["pg_id"]
                    st.rerun()
                else:
                    st.error("Invalid owner login")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    menu = st.radio("Menu", ["➕ Create Owner & PG", "📋 Owners List"])

    # -------- CREATE OWNER + PG --------
    if menu == "➕ Create Owner & PG":

        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        pg_name = st.text_input("PG Name")
        location = st.text_input("Location")
        owner_name = st.text_input("Owner Name")
        owner_number = st.text_input("Owner Number")

        if st.button("Create"):

            if new_user == "" or new_pass == "" or pg_name == "":
                st.error("Fill all fields")

            else:
                # DUPLICATE CHECK
                if not owner_df.empty:
                    users = owner_df["username"].astype(str).tolist()
                    if new_user in users:
                        st.error("Username already exists")
                        st.stop()

                pg_id = generate_pg_id()

                # SAVE OWNER
                owner_sheet.append_row([new_user, new_pass, pg_id])

                # SAVE PG DATA
                pg_sheet.append_row([
                    pg_id,
                    pg_name,
                    location,
                    owner_name,
                    owner_number
                ])

                st.success(f"🎉 Created Successfully (PG ID: {pg_id})")

                st.cache_data.clear()
                st.rerun()

    # -------- OWNER LIST --------
    elif menu == "📋 Owners List":

        if not owner_df.empty:
            st.dataframe(owner_df)
        else:
            st.info("No owners")

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    pg_id = st.session_state.pg

    st.info(f"PG ID: {pg_id}")

    # -------- SHOW PG DETAILS --------
    pg_row = pg_df[pg_df["pg_id"].astype(str) == str(pg_id)]

    if not pg_row.empty:
        st.success(f"🏠 {pg_row.iloc[0]['pg_name']}")
        st.write(f"📍 {pg_row.iloc[0]['location']}")
        st.write(f"👤 {pg_row.iloc[0]['owner_name']}")
        st.write(f"📞 {pg_row.iloc[0]['owner_number']}")
    else:
        st.warning("PG data not found")

    # -------- ADD ROOM --------
    st.subheader("➕ Add Room")

    room = st.text_input("Room No")
    floor = st.number_input("Floor", min_value=1)
    sharing = st.selectbox("Sharing", [1,2,3,4,5])
    beds = st.number_input("Available Beds", min_value=0)

    if beds > sharing:
        st.warning("Beds cannot exceed sharing")

    if st.button("Save Room"):

        if room == "":
            st.error("Enter Room No")

        elif beds > sharing:
            st.error("Invalid beds")

        else:
            room_sheet.append_row([
                pg_id,
                room,
                floor,
                sharing,
                beds,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])

            st.success("Room Added ✅")

            st.cache_data.clear()
            st.rerun()

    # -------- SHOW ROOMS --------
    st.subheader("📊 My Rooms")

    my_rooms = room_df[room_df["pg_id"].astype(str) == str(pg_id)]

    if not my_rooms.empty:
        st.dataframe(my_rooms)
    else:
        st.info("No rooms added")

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()