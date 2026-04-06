import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ---------------- CLIENT ----------------
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(creds)

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=300)
def load_data():
    client = get_client()

    # -------- SHEET1 --------
    try:
        sheet1 = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")
        pg_df = pd.DataFrame(sheet1.get_all_records())
        pg_df.columns = pg_df.columns.str.strip()
    except:
        pg_df = pd.DataFrame()

    # -------- ROOMS FROM SHEET1 --------
    if not pg_df.empty:
        rooms_df = pd.DataFrame({
            "pg_id": pg_df["pg_id"].astype(str).str.strip(),
            "pg_name": pg_df["pg_name"],
            "room_no": [f"10{i+1}" for i in range(len(pg_df))],
            "floor": pd.to_numeric(pg_df.get("floor", 0), errors="coerce").fillna(0).astype(int),
            "sharing": 2,
            "available_beds": 2,
            "total_beds": 2
        })
    else:
        rooms_df = pd.DataFrame()

    # -------- OTHER DATA --------
    try:
        app = client.open_by_key(PG_APP_ID)

        owners_df = pd.DataFrame(app.worksheet("Owners").get_all_records())
        bookings_df = pd.DataFrame(app.worksheet("Bookings").get_all_records())

        if not owners_df.empty:
            owners_df["username"] = owners_df["username"].astype(str).str.lower().str.strip()
            owners_df["pg_id"] = owners_df["pg_id"].astype(str).str.strip()

    except:
        owners_df = pd.DataFrame()
        bookings_df = pd.DataFrame()

    return pg_df, owners_df, rooms_df, bookings_df

# ---------------- LOAD ----------------
pg_df, owners_df, rooms_df, bookings_df = load_data()

# ---------------- SESSION ----------------
if "login" not in st.session_state:
    st.session_state.login = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "username" not in st.session_state:
    st.session_state.username = ""

# ---------------- LOGIN ----------------
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

# ---------------- ADMIN ----------------
elif st.session_state.role == "admin":

    st.title("🛠 Admin Dashboard")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.subheader("➕ Create Owner")

    pg_names = pg_df["pg_name"].dropna().unique().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    new_user = st.text_input("Owner Username")
    new_pass = st.text_input("Owner Password")

    if st.button("Create Owner") and new_user and new_pass:
        client = get_client()
        sheet = client.open_by_key(PG_APP_ID).worksheet("Owners")

        pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

        sheet.append_row([new_user.strip(), new_pass.strip(), pg_id, selected_pg])

        st.cache_data.clear()
        st.rerun()

    st.subheader("📋 Owners List")
    st.dataframe(owners_df, use_container_width=True)

# ---------------- OWNER ----------------
elif st.session_state.role == "owner":

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    owner = owners_df[owners_df["username"] == st.session_state.username]

    if owner.empty:
        st.error("Owner not found ❌")
        st.stop()

    pg_id = str(owner.iloc[0]["pg_id"]).strip()
    pg_name = owner.iloc[0]["pg_name"]

    st.title(f"🏠 {pg_name}")

    # -------- ROOMS --------
    owner_rooms = rooms_df[rooms_df["pg_id"] == pg_id]

    st.subheader("🛏 Rooms")
    st.dataframe(owner_rooms, use_container_width=True)

    # -------- ADD ROOM --------
    st.subheader("➕ Add Room")

    new_floor = st.number_input("Floor", 0)
    new_room = st.text_input("Room Number")

    if st.button("Add Room"):

        client = get_client()
        sheet = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")

        sheet.append_row([
            pg_id,
            pg_name,
            "",  # location
            "",  # phone
            new_floor
        ])

        st.success("Room Added ✅")
        st.cache_data.clear()
        st.rerun()

    # -------- BOOKINGS --------
    st.subheader("📋 Bookings")

    if not bookings_df.empty:
        st.dataframe(bookings_df[bookings_df["pg_id"] == pg_id])
    else:
        st.info("No bookings")