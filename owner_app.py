import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# -----------------------
# AUTH
# -----------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

# -----------------------
# LOAD DATA
# -----------------------
@st.cache_data
def load_data():
    pg_file = client.open_by_key(PG_DATA_ID)
    pg_sheet = pg_file.worksheet("Sheet1")
    pg_df = pd.DataFrame(pg_sheet.get_all_records())

    app_file = client.open_by_key(PG_APP_ID)

    owners_sheet = app_file.worksheet("Owners")
    rooms_sheet = app_file.worksheet("rooms")
    bookings_sheet = app_file.worksheet("Bookings")

    owners_df = pd.DataFrame(owners_sheet.get_all_records())
    rooms_df = pd.DataFrame(rooms_sheet.get_all_records())
    bookings_df = pd.DataFrame(bookings_sheet.get_all_records())

    return pg_df, owners_df, rooms_df, bookings_df, owners_sheet, rooms_sheet, bookings_sheet

pg_df, owners_df, rooms_df, bookings_df, owners_sheet, rooms_sheet, bookings_sheet = load_data()

# -----------------------
# SESSION
# -----------------------
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.role = ""
    st.session_state.username = ""

# -----------------------
# LOGIN PAGE
# -----------------------
if not st.session_state.login:

    st.title("🔐 Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # ADMIN LOGIN
        if role == "Admin":
            if username == ADMIN_USER and password == ADMIN_PASS:
                st.session_state.login = True
                st.session_state.role = "admin"
                st.success("Admin Login Success ✅")
                st.rerun()
            else:
                st.error("Invalid Admin Login ❌")

        # OWNER LOGIN
        if role == "Owner":
            owner = owners_df[
                (owners_df["username"] == username) &
                (owners_df["password"] == password)
            ]

            if not owner.empty:
                st.session_state.login = True
                st.session_state.role = "owner"
                st.session_state.username = username
                st.success("Owner Login Success ✅")
                st.rerun()
            else:
                st.error("Invalid Owner Login ❌")

# -----------------------
# LOGOUT
# -----------------------
if st.session_state.login:
    if st.button("Logout"):
        st.session_state.login = False
        st.rerun()

# -----------------------
# ADMIN DASHBOARD
# -----------------------
if st.session_state.role == "admin":

    st.title("🏠 Admin Dashboard")

    # SELECT PG
    pg_names = pg_df["pg_name"].dropna().unique().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    # CREATE OWNER
    st.subheader("➕ Create Owner")

    username = st.text_input("New Username")
    password = st.text_input("New Password")

    if st.button("Create Owner"):
        if username and password:

            pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

            owners_sheet.append_row([username, password, pg_id, selected_pg])
            st.success("Owner Created ✅")
            st.cache_data.clear()
            st.rerun()

    # SHOW OWNERS
    st.subheader("📋 Owners List")
    st.dataframe(owners_df)

    # DELETE OWNER
    st.subheader("❌ Delete Owner")

    if not owners_df.empty:
        delete_user = st.selectbox("Select Owner", owners_df["username"])

        if st.button("Delete Owner"):
            row_index = owners_df[owners_df["username"] == delete_user].index[0] + 2
            owners_sheet.delete_rows(row_index)

            st.success("Owner Deleted ✅")
            st.cache_data.clear()
            st.rerun()

# -----------------------
# OWNER DASHBOARD
# -----------------------
if st.session_state.role == "owner":

    owner_data = owners_df[owners_df["username"] == st.session_state.username]

    owner_pg_id = owner_data["pg_id"].values[0]
    owner_pg_name = owner_data["pg_name"].values[0]

    st.title(f"🏠 {owner_pg_name}")

    # -----------------------
    # ADD ROOM
    # -----------------------
    st.subheader("🛏️ Add Room")

    room_no = st.text_input("Room Number")
    floor = st.text_input("Floor")
    sharing = st.selectbox("Sharing", [1,2,3,4])
    beds = st.number_input("Total Beds", min_value=1)

    if st.button("Add Room"):
        rooms_sheet.append_row([
            owner_pg_id,
            owner_pg_name,
            room_no,
            floor,
            sharing,
            beds,
            beds,
            pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        ])
        st.success("Room Added ✅")
        st.cache_data.clear()
        st.rerun()

    # -----------------------
    # UPDATE BEDS
    # -----------------------
    st.subheader("🔄 Update Beds")

    owner_rooms = rooms_df[rooms_df["pg_id"] == owner_pg_id]

    if not owner_rooms.empty:
        room_select = st.selectbox("Select Room", owner_rooms["room_no"])
        new_beds = st.number_input("New Available Beds", min_value=0)

        if st.button("Update Beds"):
            row_index = owner_rooms[owner_rooms["room_no"] == room_select].index[0] + 2
            rooms_sheet.update_cell(row_index, 6, new_beds)
            st.success("Beds Updated ✅")
            st.cache_data.clear()
            st.rerun()

    # -----------------------
    # VIEW ROOMS
    # -----------------------
    st.subheader("📋 Rooms")
    st.dataframe(owner_rooms)

    # -----------------------
    # BOOKINGS
    # -----------------------
    st.subheader("📑 Bookings")

    if "pg_id" in bookings_df.columns:
        owner_bookings = bookings_df[bookings_df["pg_id"] == owner_pg_id]
    else:
        owner_bookings = bookings_df

    if not owner_bookings.empty:

        for i, row in owner_bookings.iterrows():

            if row["status"] == "Pending":

                st.write(f"👤 {row['name']} | Room: {row['room_no']}")

                if st.button(f"Approve {i}"):

                    # Update booking
                    bookings_sheet.update_cell(i + 2, 6, "Approved")

                    # Reduce bed
                    room_row = owner_rooms[owner_rooms["room_no"] == row["room_no"]]

                    if not room_row.empty:
                        r_index = room_row.index[0] + 2
                        current = int(room_row["available_beds"].values[0])

                        if current > 0:
                            rooms_sheet.update_cell(r_index, 6, current - 1)

                    st.success("Approved + Beds Updated ✅")
                    st.cache_data.clear()
                    st.rerun()

    else:
        st.info("No bookings yet")