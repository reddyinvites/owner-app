import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="PG System", layout="centered")

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

room_sheet = client.open_by_key(SHEET_ID).worksheet("Sheet1")
owner_sheet = client.open_by_key(SHEET_ID).worksheet("Owners")

# -------- LOAD DATA --------
room_df = pd.DataFrame(room_sheet.get_all_records())
owner_df = pd.DataFrame(owner_sheet.get_all_records())

# -------- SESSION --------
if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= LOGIN PAGE =================
if st.session_state.page == "login":

    st.subheader("🔐 Login")

    role = st.selectbox("Login as", ["Owner", "Admin"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if role == "Admin":
            if username == "admin" and password == "admin123":
                st.session_state.page = "admin"
                st.success("Admin Login Success")
                st.rerun()
            else:
                st.error("Invalid admin login")

        else:
            user = owner_df[
                (owner_df["username"] == username) &
                (owner_df["password"] == password)
            ]

            if not user.empty:
                st.session_state.page = "owner"
                st.session_state.owner = username
                st.session_state.pg = user.iloc[0]["pg_name"]
                st.success("Owner Login Success")
                st.rerun()
            else:
                st.error("Invalid owner login")

# ================= ADMIN PAGE =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    menu = st.radio("Go to", ["➕ Create Owner", "📋 Owners List", "📊 PG Dashboard"])

    # -------- CREATE OWNER --------
    if menu == "➕ Create Owner":

        st.subheader("Create Owner")

        new_pg = st.text_input("PG Name")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        if st.button("Create"):
            owner_sheet.append_row([new_user, new_pass, new_pg])
            st.success("Owner Created")
            st.rerun()

    # -------- OWNER LIST --------
    elif menu == "📋 Owners List":

        st.subheader("Owners")

        if not owner_df.empty:

            for i, row in owner_df.iterrows():

                col1, col2, col3, col4 = st.columns([2,2,2,1])

                col1.write(row["username"])
                col2.write(row["password"])
                col3.write(row["pg_name"])

                # DELETE BUTTON
                if col4.button("❌", key=f"del_{i}"):
                    owner_sheet.delete_rows(i+2)
                    st.success("Deleted")
                    st.rerun()

                # EDIT PASSWORD
                new_pass = st.text_input(
                    f"New pass {i}", key=f"edit_{i}"
                )

                if st.button("Update", key=f"upd_{i}"):
                    owner_sheet.update(f"B{i+2}", new_pass)
                    st.success("Password Updated")
                    st.rerun()

        else:
            st.info("No owners")

    # -------- PG DASHBOARD --------
    elif menu == "📊 PG Dashboard":

        if not room_df.empty:

            for pg in room_df["pg_name"].unique():

                st.markdown(f"## 🏠 {pg}")

                pg_df = room_df[room_df["pg_name"] == pg]

                for f in pg_df["floor"].unique():

                    st.markdown(f"### Floor {f}")
                    st.dataframe(pg_df[pg_df["floor"] == f])

    # LOGOUT
    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER PAGE =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    owner = st.session_state.owner
    pg = st.session_state.pg

    st.info(f"PG: {pg}")

    # FILTER
    my_df = room_df[room_df["owner_id"] == owner]

    # ADD ROOM
    st.subheader("Add Room")

    room = st.text_input("Room")
    floor = st.number_input("Floor", 1)
    share = st.selectbox("Sharing", [1,2,3,4])
    beds = st.number_input("Beds", 0, share)

    if st.button("Save"):
        room_sheet.append_row([
            pg, room, floor, share, beds,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            owner
        ])
        st.success("Added")
        st.rerun()

    # DISPLAY
    st.subheader("Rooms")

    for f in my_df["floor"].unique():
        st.markdown(f"### Floor {f}")
        st.dataframe(my_df[my_df["floor"] == f])

    # LOGOUT
    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()