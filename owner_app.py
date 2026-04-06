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

def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(creds)

# -----------------------
# LOAD DATA
# -----------------------
@st.cache_data(ttl=60)
def load_data():
    client = get_client()

    try:
        pg_file = client.open_by_key(PG_DATA_ID)
        pg_sheet = pg_file.worksheet("Sheet1")
        pg_df = pd.DataFrame(pg_sheet.get_all_records())

        pg_df.columns = pg_df.columns.str.strip()
        pg_df["pg_id"] = pg_df["pg_id"].astype(str).str.strip()
        pg_df["pg_name"] = pg_df["pg_name"].astype(str).str.strip()

    except:
        pg_df = pd.DataFrame(columns=["pg_id", "pg_name"])

    app_file = client.open_by_key(PG_APP_ID)

    owners_df = pd.DataFrame(app_file.worksheet("Owners").get_all_records())
    rooms_df = pd.DataFrame(app_file.worksheet("rooms").get_all_records())
    bookings_df = pd.DataFrame(app_file.worksheet("Bookings").get_all_records())

    return pg_df, owners_df, rooms_df, bookings_df

# -----------------------
# GET SHEETS
# -----------------------
def get_sheets():
    client = get_client()
    app_file = client.open_by_key(PG_APP_ID)

    owners_sheet = app_file.worksheet("Owners")
    rooms_sheet = app_file.worksheet("rooms")
    bookings_sheet = app_file.worksheet("Bookings")

    return owners_sheet, rooms_sheet, bookings_sheet

pg_df, owners_df, rooms_df, bookings_df = load_data()
owners_sheet, rooms_sheet, bookings_sheet = get_sheets()

# -----------------------
# SESSION
# -----------------------
if "login" not in st.session_state:
    st.session_state.login = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "username" not in st.session_state:
    st.session_state.username = ""

# -----------------------
# LOGIN
# -----------------------
if not st.session_state.login:

    st.title("🔐 Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if role == "Admin":
            if username == ADMIN_USER and password == ADMIN_PASS:
                st.session_state.login = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Invalid Admin ❌")

        else:
            owners_df["username"] = owners_df["username"].astype(str).str.strip().str.lower()
            owners_df["password"] = owners_df["password"].astype(str).str.strip()

            user = owners_df[
                (owners_df["username"] == username.strip().lower()) &
                (owners_df["password"] == password.strip())
            ]

            if not user.empty:
                st.session_state.login = True
                st.session_state.role = "owner"
                st.session_state.username = username.strip().lower()
                st.rerun()
            else:
                st.error("Invalid Owner ❌")

# -----------------------
# ADMIN DASHBOARD
# -----------------------
elif st.session_state.role == "admin":

    st.title("🛠 Admin Dashboard")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # -----------------------
    # CREATE OWNER + SEARCH
    # -----------------------
    st.subheader("➕ Create Owner")

    search_pg = st.text_input("🔍 Search PG (Name / ID)")

    if search_pg:
        filtered_pg = pg_df[
            pg_df["pg_name"].str.contains(search_pg, case=False, na=False) |
            pg_df["pg_id"].astype(str).str.contains(search_pg, na=False)
        ]
    else:
        filtered_pg = pg_df

    pg_names = filtered_pg["pg_name"].dropna().unique().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    new_user = st.text_input("Owner Username")
    new_pass = st.text_input("Owner Password")

    if st.button("Create Owner"):
        if new_user and new_pass:
            try:
                pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

                owners_sheet.append_row([
                    new_user.strip(),
                    new_pass.strip(),
                    pg_id,
                    selected_pg
                ])

                st.success("Owner Created ✅")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Enter all fields ❌")

    # -----------------------
    # OWNERS LIST (UPDATE + DELETE)
    # -----------------------
    st.subheader("📋 Owners List")

    if not owners_df.empty:

        for i, row in owners_df.iterrows():

            c1, c2, c3, c4, c5, c6 = st.columns([2,2,2,2,1,1])

            username = str(row["username"]).strip()
            password = str(row["password"]).strip()
            pg_id = row["pg_id"]
            pg_name = row["pg_name"]

            c1.write(username)
            new_password = c2.text_input("Password", value=password, key=f"pass_{i}")
            c3.write(pg_id)
            c4.write(pg_name)

            # UPDATE
            if c5.button("💾", key=f"update_{i}"):
                try:
                    all_values = owners_sheet.get_all_values()

                    for idx, r in enumerate(all_values[1:], start=2):
                        if r[0].strip() == username:
                            owners_sheet.update_cell(idx, 2, new_password.strip())
                            break

                    st.success("Updated ✅")
                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")

            # DELETE
            if c6.button("❌", key=f"delete_{i}"):
                try:
                    all_values = owners_sheet.get_all_values()

                    for idx, r in enumerate(all_values[1:], start=2):
                        if r[0].strip() == username:
                            owners_sheet.delete_rows(idx)
                            break

                    st.success("Deleted ✅")
                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")

    else:
        st.info("No owners available")

# -----------------------
# OWNER DASHBOARD
# -----------------------
elif st.session_state.role == "owner":

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    owners_df["username"] = owners_df["username"].astype(str).str.strip().str.lower()

    owner_data = owners_df[
        owners_df["username"] == st.session_state.username
    ]

    if owner_data.empty:
        st.error("Owner data missing ❌")
        st.stop()

    owner_pg_id = owner_data.iloc[0]["pg_id"]
    owner_pg_name = owner_data.iloc[0]["pg_name"]

    st.title(f"🏠 {owner_pg_name}")

    # ROOMS
    st.subheader("🛏 Rooms")
    owner_rooms = rooms_df[rooms_df["pg_id"] == owner_pg_id]
    st.dataframe(owner_rooms, use_container_width=True)

    # DELETE ROOM
    st.subheader("❌ Delete Room")

    if not owner_rooms.empty:

        room_options = owner_rooms["room_no"].astype(str).tolist()
        selected_room = st.selectbox("Select Room to Delete", room_options)

        if st.button("Delete Room"):
            try:
                all_values = rooms_sheet.get_all_values()

                for i, row in enumerate(all_values[1:], start=2):
                    if str(row[2]).strip() == selected_room and str(row[0]).strip() == str(owner_pg_id):
                        rooms_sheet.delete_rows(i)
                        break

                st.success("Room Deleted ✅")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    else:
        st.info("No rooms to delete")

    # ADD ROOM
    st.subheader("➕ Add Room")

    room_no = st.text_input("Room Number")
    floor = st.number_input("Floor", min_value=0)

    sharing = st.selectbox("Sharing", [1, 2, 3, 4])
    total_beds = st.number_input("Total Beds", min_value=1, max_value=sharing)
    available_beds = st.number_input("Available Beds", min_value=0, max_value=total_beds)

    if st.button("Add Room"):

        if not room_no:
            st.error("Enter room number ❌")
        else:
            try:
                new_row = [
                    owner_pg_id,
                    owner_pg_name,
                    room_no,
                    int(floor),
                    int(sharing),
                    int(available_beds),
                    int(total_beds),
                    pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                ]

                rooms_sheet.append_row(new_row)

                st.success("Room Added ✅")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    # BOOKINGS
    st.subheader("📋 Bookings")

    if not bookings_df.empty and "pg_id" in bookings_df.columns:
        owner_bookings = bookings_df[bookings_df["pg_id"] == owner_pg_id]
        st.dataframe(owner_bookings, use_container_width=True)
    else:
        st.info("No bookings yet")