import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="PG PRO SYSTEM", layout="centered")
st.title("🏠 PG PRO Management System")

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

owners_sheet = sheet.worksheet("Owners")
pg_sheet = sheet.worksheet("pg_data")
room_sheet = sheet.worksheet("rooms")

st.success("✅ Connected to Google Sheets")

# -------- LOAD --------
@st.cache_data(ttl=30)
def load():
    owners = pd.DataFrame(owners_sheet.get_all_records())
    pg = pd.DataFrame(pg_sheet.get_all_records())
    rooms = pd.DataFrame(room_sheet.get_all_records())

    owners.columns = owners.columns.str.strip().str.lower()
    pg.columns = pg.columns.str.strip().str.lower()
    rooms.columns = rooms.columns.str.strip().str.lower()

    return owners, pg, rooms

owners_df, pg_df, room_df = load()

# -------- SESSION --------
if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= LOGIN =================
if st.session_state.page == "login":

    st.subheader("🔐 Login")

    role = st.selectbox("Login as", ["Owner", "Admin"])
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):

        if role == "Admin":
            if user == "admin" and pwd == "admin123":
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("Invalid admin")

        else:
            u = owners_df[
                (owners_df["username"] == user) &
                (owners_df["password"] == pwd)
            ]

            if not u.empty:
                pg_id = u.iloc[0]["pg_id"]

                st.session_state.page = "owner"
                st.session_state.pg_id = pg_id
                st.session_state.username = user

                st.rerun()
            else:
                st.error("Invalid login")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    st.subheader("➕ Create PG + Owner")

    pg_id = st.text_input("PG ID (Ex: PG001)")
    pg_name = st.text_input("PG Name")
    location = st.text_input("Location")
    owner_name = st.text_input("Owner Name")
    owner_number = st.text_input("Owner Number")

    username = st.text_input("Login Username")
    password = st.text_input("Login Password")

    if st.button("Create"):

        if username in owners_df["username"].astype(str).tolist():
            st.error("Username exists")

        else:
            # Save PG
            pg_sheet.append_row([
                pg_id, pg_name, location, owner_name, owner_number
            ])

            # Save Owner login
            owners_sheet.append_row([
                username, password, pg_id
            ])

            st.success("🎉 PG + Owner Created")
            st.cache_data.clear()
            st.rerun()

    if st.button("Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    pg_id = st.session_state.pg_id

    # 👉 FETCH PG DETAILS
    pg_row = pg_df[pg_df["pg_id"] == pg_id]

    if not pg_row.empty:
        pg_name = pg_row.iloc[0]["pg_name"]
        location = pg_row.iloc[0]["location"]
        owner_name = pg_row.iloc[0]["owner_name"]
        owner_number = pg_row.iloc[0]["owner_number"]

        st.info(f"🏠 {pg_name} | 📍 {location}")
        st.write(f"👤 {owner_name} | 📞 {owner_number}")

    # -------- ADD ROOM --------
    st.subheader("➕ Add Room")

    room = st.text_input("Room No")
    floor = st.number_input("Floor", 1)
    sharing = st.selectbox("Sharing", [1,2,3,4,5])
    beds = st.number_input("Available Beds", 0)

    if beds > sharing:
        st.warning("Beds > sharing not allowed")

    if st.button("Save Room"):

        room_sheet.append_row([
            pg_id,
            room,
            floor,
            sharing,
            beds,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ])

        st.success("Room Added")
        st.cache_data.clear()
        st.rerun()

    # -------- VIEW ROOMS --------
    st.subheader("📊 My Rooms")

    my_rooms = room_df[room_df["pg_id"] == pg_id]

    if not my_rooms.empty:
        st.dataframe(my_rooms, use_container_width=True)
    else:
        st.info("No rooms")

    if st.button("Logout"):
        st.session_state.page = "login"
        st.rerun()