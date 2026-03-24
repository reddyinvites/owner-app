import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="PG Management System", layout="centered")

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

SHEET_ID = "YOUR_SHEET_ID"

room_sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")
owner_sheet = client.open_by_key(SHEET_ID).worksheet("Owners")

# -------- LOAD DATA --------
room_df = pd.DataFrame(room_sheet.get_all_records())
owner_df = pd.DataFrame(owner_sheet.get_all_records())

# -------- SESSION --------
if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= LOGIN =================
if st.session_state.page == "login":

    st.subheader("🔐 Login")

    role = st.selectbox("Login as", ["Owner", "Admin"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # ADMIN LOGIN
        if role == "Admin":
            if username == "admin" and password == "admin123":
                st.session_state.page = "admin"
                st.success("Admin Login Success")
                st.rerun()
            else:
                st.error("Invalid admin login")

        # OWNER LOGIN
        else:
            user = owner_df[
                (owner_df["username"].astype(str).str.strip() == username.strip()) &
                (owner_df["password"].astype(str).str.strip() == password.strip())
            ]

            if not user.empty:
                st.session_state.page = "owner"
                st.session_state.owner = username
                st.session_state.pg = user.iloc[0]["pg_name"]
                st.success("Owner Login Success")
                st.rerun()
            else:
                st.error("Invalid owner login")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    menu = st.radio("Menu", ["➕ Create Owner", "📋 Owners List"])

    # CREATE OWNER
    if menu == "➕ Create Owner":

        st.subheader("Create Owner")

        new_pg = st.text_input("PG Name")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        if st.button("Create"):
            owner_sheet.append_row([new_user, new_pass, new_pg])
            st.success("Owner Created")
            st.rerun()

    # OWNER LIST
    elif menu == "📋 Owners List":

        st.subheader("Owners")

        if not owner_df.empty:

            for i, row in owner_df.iterrows():

                col1, col2, col3, col4 = st.columns([2,2,2,1])

                col1.write(row["username"])
                col2.write(row["password"])
                col3.write(row["pg_name"])

                if col4.button("❌", key=f"del_{i}"):
                    owner_sheet.delete_rows(i+2)
                    st.rerun()

    if st.button("Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    owner = st.session_state.owner
    pg = st.session_state.pg

    st.info(f"PG: {pg}")

    # -------- DEFAULT SESSION --------
    if "room_input" not in st.session_state:
        st.session_state.room_input = ""

    if "floor_input" not in st.session_state:
        st.session_state.floor_input = 1

    if "sharing_input" not in st.session_state:
        st.session_state.sharing_input = 1

    if "beds_input" not in st.session_state:
        st.session_state.beds_input = 0

    # -------- ADD ROOM --------
    st.subheader("➕ Add Room")

    room = st.text_input("Room No", key="room_input")

    floor = st.number_input(
        "Floor",
        min_value=1,
        step=1,
        key="floor_input"
    )

    sharing = st.selectbox(
        "Sharing",
        [1,2,3,4,5],
        key="sharing_input"
    )

    beds = st.number_input(
        "Available Beds",
        min_value=0,
        step=1,
        key="beds_input"
    )

    # VALIDATION
    if beds > sharing:
        st.error(f"Beds cannot be more than sharing ({sharing})")

    # SAVE
    if st.button("Save"):

        if beds > sharing:
            st.warning("Fix beds value before saving")
            st.stop()

        room_sheet.append_row([
            pg,
            room,
            floor,
            sharing,
            beds,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            owner
        ])

        st.success("Room Added ✅")

        # CLEAR FORM
        st.session_state.room_input = ""
        st.session_state.floor_input = 1
        st.session_state.sharing_input = 1
        st.session_state.beds_input = 0

        st.rerun()

    # -------- MY ROOMS --------
    st.subheader("📊 My Rooms")

    my_df = room_df[room_df["owner_id"] == owner]

    if not my_df.empty:

        for f in my_df["floor"].unique():
            st.markdown(f"### Floor {f}")
            st.dataframe(my_df[my_df["floor"] == f])

    else:
        st.info("No rooms added yet")

    if st.button("Logout"):
        st.session_state.page = "login"
        st.rerun()