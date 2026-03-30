import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="PG Management System", layout="centered")

st.title("🏠 PG Management System")

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

SHEET_ID = "YOUR_SHEET_ID_HERE"

try:
    sheet = client.open_by_key(SHEET_ID)
    room_sheet = sheet.worksheet("Sheet1")
    owner_sheet = sheet.worksheet("Owners")
    st.success("✅ Connected to Google Sheet")
except Exception as e:
    st.error(f"❌ ERROR: {e}")
    st.stop()

# ---------------- LOAD ----------------
@st.cache_data(ttl=30)
def load_data():
    room_df = pd.DataFrame(room_sheet.get_all_records())
    owner_df = pd.DataFrame(owner_sheet.get_all_records())
    return room_df, owner_df

room_df, owner_df = load_data()

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
                owner_df.columns = owner_df.columns.str.strip()

                user = owner_df[
                    (owner_df["username"].astype(str).str.strip() == username.strip()) &
                    (owner_df["password"].astype(str).str.strip() == password.strip())
                ]

                if not user.empty:
                    st.session_state.page = "owner"
                    st.session_state.owner = username.strip()
                    st.session_state.pg_id = user.iloc[0]["pg_id"]
                    st.rerun()
                else:
                    st.error("Invalid owner login")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    new_pg_id = st.text_input("PG ID (Ex: PG001)")

    if st.button("Create Owner"):

        if new_user.strip() == "" or new_pass.strip() == "" or new_pg_id.strip() == "":
            st.error("All fields required")

        else:
            existing = owner_df[owner_df["username"] == new_user]

            if not existing.empty:
                st.error("Username already exists")

            else:
                owner_sheet.append_row([new_user, new_pass, new_pg_id])
                st.success("Owner created successfully 🎉")
                st.rerun()

    st.subheader("Owners List")

    if not owner_df.empty:
        for i, row in owner_df.iterrows():
            col1, col2, col3, col4 = st.columns([2,2,2,1])

            col1.write(row["username"])
            col2.write(row["password"])
            col3.write(row["pg_id"])

            if col4.button("❌", key=f"del_owner_{i}"):
                owner_sheet.delete_rows(i+2)
                st.rerun()

    if st.button("Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    pg_id = st.session_state.pg_id

    st.success(f"PG ID: {pg_id}")

    # FILTER DATA
    if not room_df.empty:
        room_df.columns = room_df.columns.str.strip().str.lower()
        my_df = room_df[room_df["pg_id"].astype(str) == pg_id]
    else:
        my_df = pd.DataFrame()

    # -------- ADD ROOM --------
    st.subheader("➕ Add Room")

    room = st.text_input("Room No")
    floor = st.number_input("Floor", min_value=1, step=1)
    sharing = st.selectbox("Sharing", [1,2,3,4,5])
    beds = st.number_input("Available Beds", min_value=0, step=1)

    if beds > sharing:
        st.warning(f"⚠️ Max beds = {sharing}")

    if st.button("Save Room"):

        if room.strip() == "":
            st.error("Enter room number")

        elif beds > sharing:
            st.error("Beds cannot exceed sharing")

        else:
            room_sheet.append_row([
                pg_id,
                "", "", "", "",   # pg details optional
                room,
                floor,
                sharing,
                beds,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])

            st.success("Room added ✅")

            # 🔥 CLEAR INPUTS
            st.rerun()

    # -------- DISPLAY --------
    st.subheader("📊 My Rooms")

    if not my_df.empty:
        st.dataframe(my_df[[
            "pg_id","room_no","floor","sharing","available_beds"
        ]], use_container_width=True)
    else:
        st.info("No rooms added")

    # -------- ACTIONS --------
    st.subheader("⚙️ Actions")

    if not my_df.empty:

        selected = st.selectbox("Select Room", my_df.index)

        col1, col2 = st.columns(2)

        if col1.button("🗑 Delete"):
            room_sheet.delete_rows(selected + 2)
            st.success("Deleted")
            st.rerun()

        if col2.button("✏️ Edit"):
            st.session_state.edit_index = selected

    # -------- EDIT --------
    if "edit_index" in st.session_state:

        i = st.session_state.edit_index
        row = my_df.loc[i]

        st.subheader("✏️ Edit Room")

        new_room = st.text_input("Room", value=row["room_no"])
        new_floor = st.number_input("Floor", value=int(row["floor"]))
        new_sharing = st.number_input("Sharing", value=int(row["sharing"]))
        new_beds = st.number_input("Beds", value=int(row["available_beds"]))

        if st.button("Update"):

            if new_beds > new_sharing:
                st.error("Beds > Sharing not allowed")

            else:
                updated = [
                    pg_id,
                    "", "", "", "",
                    new_room,
                    new_floor,
                    new_sharing,
                    new_beds,
                    row["timestamp"]
                ]

                room_sheet.update(f"A{i+2}:J{i+2}", [updated])

                st.success("Updated ✅")
                del st.session_state.edit_index
                st.rerun()

    if st.button("Logout"):
        st.session_state.page = "login"
        st.rerun()