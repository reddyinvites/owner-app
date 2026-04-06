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

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# -----------------------
# CACHE CLIENT (IMPORTANT)
# -----------------------
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(creds)

# -----------------------
# LOAD EVERYTHING ONCE
# -----------------------
@st.cache_data(ttl=300)
def load_data():
    client = get_client()

    # PG DATA
    try:
        pg_file = client.open_by_key(PG_DATA_ID)
        pg_sheet = pg_file.worksheet("Sheet1")
        pg_df = pd.DataFrame(pg_sheet.get_all_records())
    except:
        pg_df = pd.DataFrame(columns=["pg_id", "pg_name"])
        pg_sheet = None

    # APP DATA
    try:
        app_file = client.open_by_key(PG_APP_ID)

        owners_sheet = app_file.worksheet("Owners")
        rooms_sheet = app_file.worksheet("rooms")
        bookings_sheet = app_file.worksheet("Bookings")

        owners_df = pd.DataFrame(owners_sheet.get_all_records())
        rooms_df = pd.DataFrame(rooms_sheet.get_all_records())
        bookings_df = pd.DataFrame(bookings_sheet.get_all_records())

    except:
        owners_df = pd.DataFrame()
        rooms_df = pd.DataFrame()
        bookings_df = pd.DataFrame()
        owners_sheet = rooms_sheet = bookings_sheet = None

    return (
        pg_df, owners_df, rooms_df, bookings_df,
        pg_sheet, owners_sheet, rooms_sheet, bookings_sheet
    )

# -----------------------
# LOAD
# -----------------------
pg_df, owners_df, rooms_df, bookings_df, pg_sheet, owners_sheet, rooms_sheet, bookings_sheet = load_data()

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
            owners_df["username"] = owners_df["username"].astype(str).str.lower().str.strip()
            owners_df["password"] = owners_df["password"].astype(str).str.strip()

            user = owners_df[
                (owners_df["username"] == username.lower().strip()) &
                (owners_df["password"] == password.strip())
            ]

            if not user.empty:
                st.session_state.login = True
                st.session_state.role = "owner"
                st.session_state.username = username.lower().strip()
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

    # CREATE OWNER
    st.subheader("➕ Create Owner")

    pg_names = pg_df.get("pg_name", pd.Series()).dropna().unique().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    new_user = st.text_input("Owner Username")
    new_pass = st.text_input("Owner Password")

    if st.button("Create Owner"):
        if new_user and new_pass and owners_sheet:
            pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

            owners_sheet.append_row([
                new_user.strip(),
                new_pass.strip(),
                pg_id,
                selected_pg
            ])

            st.cache_data.clear()
            st.rerun()

    # OWNERS LIST
    st.subheader("📋 Owners List")

    for i, row in owners_df.iterrows():
        c1, c2, c3, c4, c5, c6 = st.columns([2,2,2,2,1,1])

        c1.write(row.get("username",""))
        c2.write(row.get("password",""))
        c3.write(row.get("pg_id",""))
        c4.write(row.get("pg_name",""))

        if c5.button("❌", key=f"del_owner_{i}"):
            owners_sheet.delete_rows(i + 2)
            st.cache_data.clear()
            st.rerun()

        if c6.button("✏️", key=f"edit_owner_{i}"):
            st.session_state[f"edit_owner_{i}"] = True

        if st.session_state.get(f"edit_owner_{i}", False):
            u = st.text_input("Username", value=row["username"], key=f"u{i}")
            p = st.text_input("Password", value=row["password"], key=f"p{i}")

            if st.button("Save", key=f"s{i}"):
                owners_sheet.update(f"A{i+2}:D{i+2}", [[u, p, row["pg_id"], row["pg_name"]]])
                st.cache_data.clear()
                st.rerun()

    # PG LIST
    st.subheader("🏠 All PGs")

    for i, row in pg_df.iterrows():
        c1, c2, c3, c4 = st.columns([3,2,1,1])

        c1.write(row.get("pg_name",""))
        c2.write(row.get("pg_id",""))

        if c3.button("❌", key=f"del_pg_{i}"):
            pg_sheet.delete_rows(i + 2)
            st.cache_data.clear()
            st.rerun()

        if c4.button("✏️", key=f"edit_pg_{i}"):
            st.session_state[f"edit_pg_{i}"] = True

        if st.session_state.get(f"edit_pg_{i}", False):
            name = st.text_input("PG Name", value=row["pg_name"], key=f"pg{i}")

            if st.button("Save PG", key=f"spg{i}"):
                pg_sheet.update(f"B{i+2}", name)
                st.cache_data.clear()
                st.rerun()

# -----------------------
# OWNER DASHBOARD
# -----------------------
elif st.session_state.role == "owner":

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    owners_df["username"] = owners_df["username"].astype(str).str.lower().str.strip()

    owner = owners_df[owners_df["username"] == st.session_state.username]

    if owner.empty:
        st.error("Owner not found ❌")
        st.stop()

    pg_id = str(owner.iloc[0]["pg_id"])
    pg_name = owner.iloc[0]["pg_name"]

    st.title(f"🏠 {pg_name}")

    if not rooms_df.empty:
        rooms_df["pg_id"] = rooms_df["pg_id"].astype(str)

    owner_rooms = rooms_df[rooms_df["pg_id"] == pg_id]

    # AUTO ROOM
    if owner_rooms.empty and rooms_sheet:
        rooms_sheet.append_row([pg_id, pg_name, "101", 0, 2, 2, 2])
        st.cache_data.clear()
        st.rerun()

    st.subheader("🛏 Rooms")
    st.dataframe(owner_rooms, use_container_width=True)

    # ADD ROOM
    st.subheader("➕ Add Room")

    r = st.text_input("Room No")
    f = st.number_input("Floor", 0)
    s = st.selectbox("Sharing", [1,2,3,4])
    t = st.number_input("Total Beds", 1, s)
    a = st.number_input("Available Beds", 0, t)

    if st.button("Add Room") and rooms_sheet:
        rooms_sheet.append_row([pg_id, pg_name, r, f, s, a, t])
        st.cache_data.clear()
        st.rerun()

    # BOOKINGS
    st.subheader("📋 Bookings")

    if not bookings_df.empty:
        st.dataframe(bookings_df[bookings_df["pg_id"] == pg_id])
    else:
        st.info("No bookings")