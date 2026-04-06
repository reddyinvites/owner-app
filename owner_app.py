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

    try:
        sheet = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")
        df = pd.DataFrame(sheet.get_all_records())
        df.columns = df.columns.str.strip()
    except:
        df = pd.DataFrame()

    # CLEAN DATA
    if not df.empty:
        df["pg_id"] = df["pg_id"].astype(str).str.strip()

    return df

df = load_data()

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
            # OWNER LOGIN FROM SHEET
            user = df[
                (df["pg_name"].str.lower() == username.lower())  # simple login
            ]

            if not user.empty:
                st.session_state.login = True
                st.session_state.role = "owner"
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid Owner ❌")

# ---------------- ADMIN ----------------
elif st.session_state.role == "admin":

    st.title("🛠 Admin Dashboard")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.dataframe(df, use_container_width=True)

# ---------------- OWNER ----------------
elif st.session_state.role == "owner":

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    owner_df = df[df["pg_name"].str.lower() == st.session_state.username.lower()]

    if owner_df.empty:
        st.error("No data found ❌")
        st.stop()

    pg_id = owner_df.iloc[0]["pg_id"]
    pg_name = owner_df.iloc[0]["pg_name"]

    st.title(f"🏠 {pg_name}")

    # ---------------- ROOMS ----------------
    st.subheader("🛏 Rooms")

    for i, row in owner_df.iterrows():

        c1, c2, c3, c4 = st.columns([2,2,2,1])

        c1.write(f"Room: {row.get('room_no','')}")
        c2.write(f"Floor: {row.get('floor',0)}")
        c3.write(f"{row.get('available_beds',0)}/{row.get('total_beds',0)} Beds")

        # DELETE
        if c4.button("❌", key=f"del_{i}"):
            client = get_client()
            sheet = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")
            sheet.delete_rows(i + 2)

            st.cache_data.clear()
            st.rerun()

        # EDIT
        if st.button("✏️ Edit", key=f"edit_{i}"):
            st.session_state[f"edit_{i}"] = True

        if st.session_state.get(f"edit_{i}", False):

            floor = st.number_input("Floor", value=int(row.get("floor",0)), key=f"f{i}")
            total = st.number_input("Total Beds", value=int(row.get("total_beds",0)), key=f"t{i}")
            available = st.number_input("Available Beds", value=int(row.get("available_beds",0)), key=f"a{i}")

            if st.button("Save", key=f"s{i}"):
                client = get_client()
                sheet = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")

                sheet.update(f"E{i+2}:I{i+2}", [[
                    floor,
                    row.get("room_no",""),
                    row.get("sharing_type",2),
                    total,
                    available
                ]])

                st.cache_data.clear()
                st.rerun()

    # ---------------- ADD ROOM ----------------
    st.subheader("➕ Add Room")

    new_floor = st.number_input("Floor", 0)
    new_room = st.text_input("Room Number")
    new_sharing = st.number_input("Sharing", 1)
    new_total = st.number_input("Total Beds", 1)
    new_available = st.number_input("Available Beds", 0, new_total)

    if st.button("Add Room"):

        client = get_client()
        sheet = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")

        sheet.append_row([
            pg_id,
            pg_name,
            "",
            "",
            new_floor,
            new_room,
            new_sharing,
            new_total,
            new_available,
            ""
        ])

        st.success("Room Added ✅")
        st.cache_data.clear()
        st.rerun()