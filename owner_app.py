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
# SAFE LOAD DATA
# -----------------------
@st.cache_data(ttl=60)
def load_data():
    client = get_client()

    # PG DATA
    try:
        pg_file = client.open_by_key(PG_DATA_ID)
        pg_sheet = pg_file.worksheet("Sheet1")
        pg_df = pd.DataFrame(pg_sheet.get_all_records())

        pg_df.columns = pg_df.columns.str.strip()
        pg_df["pg_id"] = pg_df["pg_id"].astype(str).str.strip()
        pg_df["pg_name"] = pg_df["pg_name"].astype(str).str.strip()

    except:
        pg_df = pd.DataFrame(columns=["pg_id", "pg_name"])

    # APP DATA
    try:
        app_file = client.open_by_key(PG_APP_ID)

        owners_df = pd.DataFrame(app_file.worksheet("Owners").get_all_records())
        rooms_df = pd.DataFrame(app_file.worksheet("rooms").get_all_records())
        bookings_df = pd.DataFrame(app_file.worksheet("Bookings").get_all_records())

    except:
        owners_df = pd.DataFrame()
        rooms_df = pd.DataFrame()
        bookings_df = pd.DataFrame()

    return pg_df, owners_df, rooms_df, bookings_df

# -----------------------
# SAFE SHEETS
# -----------------------
def get_sheets():
    try:
        client = get_client()
        app_file = client.open_by_key(PG_APP_ID)

        return (
            app_file.worksheet("Owners"),
            app_file.worksheet("rooms"),
            app_file.worksheet("Bookings")
        )
    except Exception as e:
        st.error("Google Sheet Error ❌")
        st.write(e)
        st.stop()

pg_df, owners_df, rooms_df, bookings_df = load_data()

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

    owners_sheet, rooms_sheet, bookings_sheet = get_sheets()

    st.title("🛠 Admin Dashboard")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # CREATE OWNER
    st.subheader("➕ Create Owner")

    pg_names = pg_df["pg_name"].dropna().unique().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    new_user = st.text_input("Owner Username")
    new_pass = st.text_input("Owner Password")

    if st.button("Create Owner"):
        if new_user and new_pass:
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
        else:
            st.error("Enter all fields ❌")

    # OWNERS LIST
    st.subheader("📋 Owners List")

    for i, row in owners_df.iterrows():
        col1, col2, col3, col4, col5, col6 = st.columns([2,2,2,2,1,1])

        col1.write(row.get("username", ""))
        col2.write(row.get("password", ""))
        col3.write(row.get("pg_id", ""))
        col4.write(row.get("pg_name", ""))

        if col5.button("❌", key=f"del_owner_{i}"):
            owners_sheet.delete_rows(i + 2)
            st.cache_data.clear()
            st.rerun()

        if col6.button("✏️", key=f"edit_owner_{i}"):
            st.session_state[f"edit_owner_{i}"] = True

        if st.session_state.get(f"edit_owner_{i}", False):
            new_u = st.text_input("New Username", value=row["username"], key=f"u_{i}")
            new_p = st.text_input("New Password", value=row["password"], key=f"p_{i}")

            if st.button("Save", key=f"save_owner_{i}"):
                owners_sheet.update(f"A{i+2}:D{i+2}", [[
                    new_u.strip(),
                    new_p.strip(),
                    row["pg_id"],
                    row["pg_name"]
                ]])
                st.cache_data.clear()
                st.rerun()

    # PG LIST
    st.subheader("🏠 All PGs")

    pg_sheet = get_client().open_by_key(PG_DATA_ID).worksheet("Sheet1")

    for i, row in pg_df.iterrows():
        col1, col2, col3, col4 = st.columns([3,2,1,1])

        col1.write(row.get("pg_name", ""))
        col2.write(row.get("pg_id", ""))

        if col3.button("❌", key=f"del_pg_{i}"):
            pg_sheet.delete_rows(i + 2)
            st.cache_data.clear()
            st.rerun()

        if col4.button("✏️", key=f"edit_pg_{i}"):
            st.session_state[f"edit_pg_{i}"] = True

        if st.session_state.get(f"edit_pg_{i}", False):
            new_name = st.text_input("New PG Name", value=row["pg_name"], key=f"pg_{i}")

            if st.button("Save PG", key=f"save_pg_{i}"):
                pg_sheet.update(f"B{i+2}", new_name.strip())
                st.cache_data.clear()
                st.rerun()

# -----------------------
# OWNER DASHBOARD
# -----------------------
elif st.session_state.role == "owner":

    owners_sheet, rooms_sheet, bookings_sheet = get_sheets()

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

    owner_pg_id = str(owner_data.iloc[0]["pg_id"]).strip()
    owner_pg_name = owner_data.iloc[0]["pg_name"]

    st.title(f"🏠 {owner_pg_name}")

    # AUTO ROOM
    if not rooms_df.empty:
        rooms_df["pg_id"] = rooms_df["pg_id"].astype(str).str.strip()

    owner_rooms = rooms_df[rooms_df["pg_id"] == owner_pg_id]

    if owner_rooms.empty:
        rooms_sheet.append_row([
            owner_pg_id,
            owner_pg_name,
            "101",
            0,
            2,
            2,
            2,
            pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        ])
        st.cache_data.clear()
        st.rerun()

    st.subheader("🛏 Rooms")
    st.dataframe(owner_rooms, use_container_width=True)

    # ADD ROOM
    st.subheader("➕ Add Room")

    room_no = st.text_input("Room Number")
    floor = st.number_input("Floor", min_value=0)

    sharing = st.selectbox("Sharing", [1,2,3,4])
    total_beds = st.number_input("Total Beds", min_value=1, max_value=sharing)
    available_beds = st.number_input("Available Beds", min_value=0, max_value=total_beds)

    if st.button("Add Room"):
        rooms_sheet.append_row([
            owner_pg_id,
            owner_pg_name,
            room_no,
            int(floor),
            int(sharing),
            int(available_beds),
            int(total_beds),
            pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        ])
        st.cache_data.clear()
        st.rerun()

    # BOOKINGS
    st.subheader("📋 Bookings")

    if not bookings_df.empty and "pg_id" in bookings_df.columns:
        owner_bookings = bookings_df[bookings_df["pg_id"] == owner_pg_id]
        st.dataframe(owner_bookings, use_container_width=True)
    else:
        st.info("No bookings yet")