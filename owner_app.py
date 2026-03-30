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

# -------- LOAD SAFE --------
@st.cache_data(ttl=30)
def load():
    owners = pd.DataFrame(owners_sheet.get_all_records())
    pg = pd.DataFrame(pg_sheet.get_all_records())
    rooms = pd.DataFrame(room_sheet.get_all_records())

    # SAFE COLUMN CLEAN
    if not owners.empty:
        owners.columns = [str(c).strip().lower() for c in owners.columns]

    if not pg.empty:
        pg.columns = [str(c).strip().lower() for c in pg.columns]

    if not rooms.empty:
        rooms.columns = [str(c).strip().lower() for c in rooms.columns]

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
            if not owners_df.empty:
                u = owners_df[
                    (owners_df["username"] == user) &
                    (owners_df["password"] == pwd)
                ]

                if not u.empty:
                    pg_id = str(u.iloc[0]["pg_id"])

                    st.session_state.page = "owner"
                    st.session_state.pg_id = pg_id
                    st.session_state.username = user
                    st.rerun()
                else:
                    st.error("Invalid login")
            else:
                st.error("No owners found")

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

        if username.strip() == "" or password.strip() == "" or pg_id.strip() == "":
            st.error("Fill all fields")

        elif not owners_df.empty and username in owners_df["username"].astype(str).tolist():
            st.error("❌ Username exists")

        else:
            # SAVE PG DATA
            pg_sheet.append_row([
                pg_id, pg_name, location, owner_name, owner_number
            ])

            # SAVE OWNER LOGIN
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

    # -------- FETCH PG DETAILS --------
    if not pg_df.empty:
        pg_row = pg_df[pg_df["pg_id"].astype(str) == str(pg_id)]
    else:
        pg_row = pd.DataFrame()

    if not pg_row.empty:
        st.info(f"🏠 {pg_row.iloc[0]['pg_name']} | 📍 {pg_row.iloc[0]['location']}")
        st.write(f"👤 {pg_row.iloc[0]['owner_name']} | 📞 {pg_row.iloc[0]['owner_number']}")
    else:
        st.warning("PG data not found")

    # -------- ADD ROOM --------
    st.subheader("➕ Add Room")

    room = st.text_input("Room No")
    floor = st.number_input("Floor", min_value=1)
    sharing = st.selectbox("Sharing", [1,2,3,4,5])
    beds = st.number_input("Available Beds", min_value=0)

    if beds > sharing:
        st.warning("Beds > sharing not allowed")

    if st.button("Save Room"):

        if room.strip() == "":
            st.error("Enter Room No")

        elif beds > sharing:
            st.error("Beds cannot exceed sharing")

        else:
            room_sheet.append_row([
                pg_id,
                room,
                floor,
                sharing,
                beds,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])

            st.success("🎉 Room Added")
            st.cache_data.clear()
            st.rerun()

    # -------- VIEW ROOMS --------
    st.subheader("📊 My Rooms")

    if not room_df.empty:
        my_rooms = room_df[room_df["pg_id"].astype(str) == str(pg_id)]
    else:
        my_rooms = pd.DataFrame()

    if not my_rooms.empty:
        st.dataframe(my_rooms, use_container_width=True)
    else:
        st.info("No rooms added")

    if st.button("Logout"):
        st.session_state.page = "login"
        st.rerun()