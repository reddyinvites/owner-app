import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Owner Panel", layout="centered")

st.title("🏠 Owner Panel")

# -------- SESSION --------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "owner" not in st.session_state:
    st.session_state.owner = ""

if "pg" not in st.session_state:
    st.session_state.pg = ""

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

room_sheet = sheet.worksheet("Sheet1")
owner_sheet = sheet.worksheet("Owners")

room_df = pd.DataFrame(room_sheet.get_all_records())
owner_df = pd.DataFrame(owner_sheet.get_all_records())

# -------- LOGIN --------
def login():

    st.subheader("🔐 Owner Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        user = owner_df[
            (owner_df["username"] == username) &
            (owner_df["password"] == password)
        ]

        if not user.empty:
            st.session_state.logged_in = True
            st.session_state.owner = username
            st.session_state.pg = user.iloc[0]["pg_name"]

            st.success("Login Success")
            st.rerun()
        else:
            st.error("Invalid Login")

# -------- LOGOUT --------
def logout():
    st.session_state.logged_in = False
    st.session_state.owner = ""
    st.session_state.pg = ""
    st.rerun()

# -------- CHECK LOGIN --------
if not st.session_state.logged_in:
    login()
    st.stop()

# -------- OWNER DASHBOARD --------
st.success(f"Logged in as {st.session_state.owner}")
st.info(f"PG: {st.session_state.pg}")

st.button("🚪 Logout", on_click=logout)

# -------- ADD ROOM --------
st.subheader("➕ Add Room")

room_no = st.text_input("Room Number")
floor = st.number_input("Floor", 1)
sharing = st.selectbox("Sharing", [1,2,3,4,5])
beds = st.number_input("Available Beds", 0, sharing)

if st.button("Save Room"):

    if room_no == "":
        st.error("Enter room number")
    else:
        room_sheet.append_row([
            st.session_state.pg,
            room_no,
            floor,
            sharing,
            beds,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            st.session_state.owner
        ])

        st.success("Room Added")
        st.rerun()

# -------- VIEW ROOMS --------
st.subheader("📊 My Rooms")

my_rooms = room_df[
    room_df["owner_id"] == st.session_state.owner
]

if not my_rooms.empty:

    for f in my_rooms["floor"].unique():

        st.markdown(f"### Floor {f}")
        st.dataframe(my_rooms[my_rooms["floor"] == f])

else:
    st.info("No rooms yet")