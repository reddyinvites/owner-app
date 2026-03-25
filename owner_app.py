import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="PG Management System", layout="wide")

# ---------------- GOOGLE SHEET ----------------
SHEET_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp"], scope
    )
    client = gspread.authorize(creds)

    room_sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")
    owner_sheet = client.open_by_key(SHEET_ID).worksheet("Owners")

    st.success("✅ Connected to Google Sheet")

except Exception as e:
    st.error("❌ Sheet connection error")
    st.stop()

# ---------------- LOAD DATA ----------------
try:
    room_df = pd.DataFrame(room_sheet.get_all_records())
    owner_df = pd.DataFrame(owner_sheet.get_all_records())

    room_df.columns = room_df.columns.str.strip().str.lower()
    owner_df.columns = owner_df.columns.str.strip().str.lower()

except:
    room_df = pd.DataFrame()
    owner_df = pd.DataFrame()

# ---------------- LOGIN ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.title("🏠 PG Management System")

if not st.session_state.logged_in:

    st.subheader("🔐 Login")

    role = st.selectbox("Login as", ["Owner"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        user = owner_df[
            (owner_df["username"] == username) &
            (owner_df["password"] == password)
        ]

        if not user.empty:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.pg_name = user.iloc[0]["pg_name"]
            st.success("Login success")
            st.rerun()
        else:
            st.error("Invalid Owner")

    st.stop()

# ---------------- OWNER DASHBOARD ----------------
owner = st.session_state.username
pg_name = st.session_state.pg_name

st.subheader("🏠 Owner Dashboard")
st.info(f"PG: {pg_name}")

# ---------------- FORM STATE ----------------
if "room_input" not in st.session_state:
    st.session_state.room_input = ""
if "floor_input" not in st.session_state:
    st.session_state.floor_input = 1
if "sharing_input" not in st.session_state:
    st.session_state.sharing_input = 1
if "beds_input" not in st.session_state:
    st.session_state.beds_input = 1

# ---------------- ADD ROOM ----------------
st.subheader("➕ Add Room")

room_no = st.text_input("Room No", key="room_input")
floor = st.number_input("Floor", min_value=1, step=1, key="floor_input")
sharing = st.selectbox("Sharing", [1,2,3,4,5], key="sharing_input")

beds = st.number_input(
    "Available Beds",
    min_value=0,
    max_value=sharing,   # ✅ limit by sharing
    step=1,
    key="beds_input"
)

if st.button("Save"):

    if room_no == "":
        st.warning("Enter room number")

    elif beds > sharing:
        st.error("Beds cannot exceed sharing")

    else:
        row = [
            pg_name,
            room_no,
            floor,
            sharing,
            beds,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            owner
        ]

        room_sheet.append_row(row)

        st.success("✅ Room Added")

        # CLEAR FORM
        st.session_state.room_input = ""
        st.session_state.floor_input = 1
        st.session_state.sharing_input = 1
        st.session_state.beds_input = 1

        st.rerun()

# ---------------- MY ROOMS ----------------
st.subheader("📊 My Rooms")

if not room_df.empty:
    my_df = room_df[room_df["owner_id"] == owner]
else:
    my_df = pd.DataFrame()

if not my_df.empty:

    for floor in sorted(my_df["floor"].unique()):

        st.write(f"### Floor {floor}")

        floor_df = my_df[my_df["floor"] == floor]

        st.dataframe(floor_df, use_container_width=True)

else:
    st.info("No rooms found")

# ---------------- LOGOUT ----------------
if st.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()