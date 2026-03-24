import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="PG Management", layout="centered")

st.title("🏠 PG Management System")

# -------- GOOGLE SHEETS CONNECT --------
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
room_data = room_sheet.get_all_records()
owner_data = owner_sheet.get_all_records()

room_df = pd.DataFrame(room_data)
owner_df = pd.DataFrame(owner_data)

# -------- ROLE SELECT --------
role = st.selectbox("Login as", ["Owner", "Admin"])

# ================= ADMIN =================
if role == "Admin":

    st.subheader("🔐 Admin Login")

    admin_user = st.text_input("Admin Username")
    admin_pass = st.text_input("Admin Password", type="password")

    if admin_user == "admin" and admin_pass == "admin123":

        st.success("✅ Admin Logged In")

        st.subheader("➕ Create PG Owner")

        new_pg = st.text_input("PG Name")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        if st.button("Create Owner"):

            if new_pg and new_user and new_pass:

                owner_sheet.append_row([
                    new_user,
                    new_pass,
                    new_pg
                ])

                st.success("✅ Owner Created")
                st.rerun()
            else:
                st.error("Fill all fields")

    else:
        st.info("Enter admin credentials")

# ================= OWNER =================
else:

    if "login" not in st.session_state:
        st.session_state.login = False

    if not st.session_state.login:

        st.subheader("🔐 Owner Login")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):

            user = owner_df[
                (owner_df["username"] == username) &
                (owner_df["password"] == password)
            ]

            if not user.empty:
                st.session_state.login = True
                st.session_state.username = username
                st.session_state.pg = user.iloc[0]["pg_name"]
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

    # -------- FILTER DATA --------
    if not room_df.empty:
        room_df = room_df[room_df["owner_id"] == owner_id]

    # -------- ADD ROOM --------
    st.subheader("➕ Add Room")

    room_no = st.text_input("Room Number (e.g. 101, 201)")
    st.caption("💡 Tip: 101=Floor1, 201=Floor2")

    floor = st.number_input("Floor", min_value=1, step=1)
    sharing = st.selectbox("Sharing", [1,2,3,4,5,6])
    beds = st.number_input("Available Beds", min_value=0, max_value=sharing)

    if beds > sharing:
        st.error("Beds cannot exceed sharing")

    if st.button("💾 Save / Update"):

        if room_no.strip() == "":
            st.error("Enter room number")

        else:
            found = False

            for i, row in enumerate(room_data):
                if (
                    str(row["room_no"]) == str(room_no) and
                    row["owner_id"] == owner_id
                ):
                    # UPDATE
                    room_sheet.update(f"A{i+2}:G{i+2}", [[
                        owner_pg,
                        room_no,
                        int(floor),
                        int(sharing),
                        int(beds),
                        datetime.now().strftime("%Y-%m-%d %H:%M"),
                        owner_id
                    ]])
                    st.success("✅ Room Updated")
                    found = True
                    break

            if not found:
                # ADD NEW
                room_sheet.append_row([
                    owner_pg,
                    room_no,
                    int(floor),
                    int(sharing),
                    int(beds),
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    owner_id
                ])
                st.success("✅ Room Added")

            st.rerun()

    # -------- DISPLAY --------
    st.subheader("📊 Your Rooms")

    if not room_df.empty:

        # SORT BY FLOOR + ROOM
        room_df = room_df.sort_values(by=["floor", "room_no"])

        for floor_no in sorted(room_df["floor"].unique()):
            st.markdown(f"### 🏢 Floor {floor_no}")

            floor_df = room_df[room_df["floor"] == floor_no]
            st.dataframe(floor_df, use_container_width=True)

    else:
        st.info("No rooms added yet")

    # -------- LOGOUT --------
    if st.button("🚪 Logout"):
        st.session_state.login = False
        st.rerun()