import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
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

SHEET_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

sheet = client.open_by_key(SHEET_ID)

room_sheet = sheet.worksheet("Sheet1")
owner_sheet = sheet.worksheet("Owners")

# -------- SESSION --------
if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= LOGIN =================
if st.session_state.page == "login":

    st.subheader("🔐 Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # ADMIN LOGIN
        if role == "Admin":
            if username == "admin" and password == "admin123":
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("Invalid Admin")

        # OWNER LOGIN
        else:
            owner_df = pd.DataFrame(owner_sheet.get_all_records())
            owner_df.columns = owner_df.columns.str.strip().str.lower()

            user = owner_df[
                (owner_df["username"].astype(str).str.lower().str.strip() == username.lower().strip()) &
                (owner_df["password"].astype(str).str.strip() == password.strip())
            ]

            if not user.empty:
                st.session_state.page = "owner"
                st.session_state.owner = username
                st.session_state.pg = user.iloc[0]["pg_name"]
                st.rerun()
            else:
                st.error("Invalid Owner")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    menu = st.radio("Menu", [
        "➕ Create Owner",
        "📋 Owners List",
        "📊 PG Dashboard"
    ])

    # -------- CREATE OWNER --------
    if menu == "➕ Create Owner":

        st.subheader("Create Owner")

        pg = st.text_input("PG Name")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        phone = st.text_input("Phone Number")

        if st.button("Create"):

            if pg and user and pwd and phone:
                owner_sheet.append_row([user, pwd, pg, phone])
                st.success("Owner Created")
                st.rerun()
            else:
                st.error("Fill all fields")

    # -------- OWNER LIST --------
    elif menu == "📋 Owners List":

        owner_df = pd.DataFrame(owner_sheet.get_all_records())
        owner_df.columns = owner_df.columns.str.strip().str.lower()

        if not owner_df.empty:

            for i, row in owner_df.iterrows():

                st.write(f"👤 {row['username']} | 📞 {row['phone']} | 🏠 {row['pg_name']}")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("❌ Delete", key=f"del_{i}"):
                        owner_sheet.delete_rows(i+2)
                        st.rerun()

                with col2:
                    new_pass = st.text_input("New Password", key=f"pass_{i}")
                    if st.button("Update", key=f"upd_{i}"):
                        owner_sheet.update(f"B{i+2}", new_pass)
                        st.rerun()

                st.divider()

        else:
            st.info("No owners")

    # -------- PG DASHBOARD --------
    elif menu == "📊 PG Dashboard":

        room_df = pd.DataFrame(room_sheet.get_all_records())

        if not room_df.empty:

            for pg in room_df["pg_name"].unique():

                st.markdown(f"## 🏠 {pg}")

                pg_df = room_df[room_df["pg_name"] == pg]

                for f in pg_df["floor"].unique():
                    st.markdown(f"### Floor {f}")
                    st.dataframe(pg_df[pg_df["floor"] == f])

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    st.info(f"PG: {st.session_state.pg}")

    # -------- ADD ROOM (FORM FIXED) --------
    st.subheader("➕ Add Room")

    with st.form("add_room_form", clear_on_submit=True):

        room = st.text_input("Room No")
        floor = st.number_input("Floor", 1)
        sharing = st.selectbox("Sharing", [1,2,3,4,5])
        beds = st.number_input("Beds", 0, sharing)

        st.caption(f"Max beds = {sharing}")

        submitted = st.form_submit_button("Save")

        if submitted:

            if room.strip() == "":
                st.error("Enter room number")
            else:
                room_sheet.append_row([
                    st.session_state.pg,
                    room,
                    floor,
                    sharing,
                    beds,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    st.session_state.owner
                ])

                st.success("Room Added ✅")
                st.rerun()

    # -------- VIEW ROOMS --------
    st.subheader("📊 My Rooms")

    room_df = pd.DataFrame(room_sheet.get_all_records())

    if "owner" in st.session_state:
        my_df = room_df[room_df["owner_id"] == st.session_state.owner]
    else:
        st.error("Login again")
        st.stop()

    if not my_df.empty:

        for f in my_df["floor"].unique():
            st.markdown(f"### Floor {f}")
            st.dataframe(my_df[my_df["floor"] == f])

    else:
        st.info("No rooms yet")

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()