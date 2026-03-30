import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random

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

room_sheet = sheet.worksheet("rooms")
owner_sheet = sheet.worksheet("Owners")

# -------- LOAD --------
room_df = pd.DataFrame(room_sheet.get_all_records())
owner_df = pd.DataFrame(owner_sheet.get_all_records())

# -------- PG ID --------
def generate_pg_id():
    return "PG" + str(random.randint(1000, 9999))

# -------- SESSION --------
if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= LOGIN =================
if st.session_state.page == "login":

    st.subheader("Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if role == "Admin":
            if username == "admin" and password == "admin123":
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("Wrong admin login")

        else:
            user = owner_df[
                (owner_df["username"] == username) &
                (owner_df["password"] == password)
            ]

            if not user.empty:
                st.session_state.page = "owner"
                st.session_state.pg = user.iloc[0]["pg_id"]
                st.rerun()
            else:
                st.error("Wrong owner login")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.subheader("Admin Dashboard")

    username = st.text_input("Owner Username")
    password = st.text_input("Owner Password")

    if st.button("Create Owner"):

        pg_id = generate_pg_id()

        owner_sheet.append_row([
            username,
            password,
            pg_id
        ])

        st.success(f"Owner Created | PG ID: {pg_id}")
        st.rerun()

    if st.button("Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.subheader("Owner Dashboard")

    pg_id = st.session_state.pg

    st.write("PG ID:", pg_id)

    # -------- ADD ROOM --------
    st.subheader("Add Room")

    room = st.text_input("Room No")
    floor = st.number_input("Floor", 1)
    sharing = st.selectbox("Sharing", [1,2,3,4,5])
    beds = st.number_input("Beds", 0)

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

            st.success("Room Added")
            st.rerun()

    # -------- SHOW ROOMS --------
    st.subheader("My Rooms")

    my_rooms = room_df[room_df["pg_id"] == pg_id]

    if not my_rooms.empty:
        st.dataframe(my_rooms)
    else:
        st.info("No rooms yet")

    if st.button("Logout"):
        st.session_state.page = "login"
        st.rerun()