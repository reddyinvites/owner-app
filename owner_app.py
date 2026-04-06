import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- CONFIG ----------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

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
@st.cache_data(ttl=120)
def load_data():
    client = get_client()

    # -------- SHEET1 --------
    try:
        sheet1 = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")
        pg_df = pd.DataFrame(sheet1.get_all_records())
        pg_df.columns = pg_df.columns.str.strip()

        auto_rooms = pd.DataFrame({
            "pg_id": pg_df["pg_id"],
            "pg_name": pg_df["pg_name"],
            "room_no": pg_df.get("room_no", "101"),
            "floor": pd.to_numeric(pg_df.get("floor", 0), errors="coerce").fillna(0),
            "sharing": pd.to_numeric(pg_df.get("sharing_type", 2), errors="coerce").fillna(2),
            "total_beds": pd.to_numeric(pg_df.get("total_beds", 2), errors="coerce").fillna(2),
            "available_beds": pd.to_numeric(pg_df.get("available_beds", 2), errors="coerce").fillna(2),
        })

    except:
        auto_rooms = pd.DataFrame()

    # -------- ROOMS SHEET --------
    try:
        rooms_df = pd.DataFrame(
            client.open_by_key(PG_APP_ID).worksheet("rooms").get_all_records()
        )
        rooms_df.columns = rooms_df.columns.str.strip()
    except:
        rooms_df = pd.DataFrame()

    # -------- MERGE --------
    final_rooms = pd.concat([auto_rooms, rooms_df], ignore_index=True)

    # -------- OWNERS --------
    try:
        owners_df = pd.DataFrame(
            client.open_by_key(PG_APP_ID).worksheet("Owners").get_all_records()
        )
        owners_df["username"] = owners_df["username"].str.lower().str.strip()
        owners_df["password"] = owners_df["password"].astype(str).str.strip()
        owners_df["pg_id"] = owners_df["pg_id"].astype(str).str.strip()
    except:
        owners_df = pd.DataFrame()

    return final_rooms, owners_df

rooms_df, owners_df = load_data()

# ---------------- SESSION ----------------
if "login" not in st.session_state:
    st.session_state.login = False
if "username" not in st.session_state:
    st.session_state.username = ""

# ---------------- LOGIN ----------------
if not st.session_state.login:

    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        user = owners_df[
            (owners_df["username"] == username.lower().strip()) &
            (owners_df["password"] == password.strip())
        ]

        if not user.empty:
            st.session_state.login = True
            st.session_state.username = username.lower().strip()
            st.rerun()
        else:
            st.error("Invalid Owner ❌")

# ---------------- OWNER DASHBOARD ----------------
else:

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    owner = owners_df[owners_df["username"] == st.session_state.username]

    pg_id = owner.iloc[0]["pg_id"]
    pg_name = owner.iloc[0]["pg_name"]

    st.title(f"🏠 {pg_name}")

    # FILTER ROOMS
    rooms_df["pg_id"] = rooms_df["pg_id"].astype(str).str.strip()
    owner_rooms = rooms_df[rooms_df["pg_id"] == pg_id]

    st.subheader("🛏 Rooms")

    for i, row in owner_rooms.iterrows():

        c1, c2, c3, c4 = st.columns([2,2,2,1])

        c1.write(f"Room: {row.get('room_no','')}")
        c2.write(f"Floor: {row.get('floor',0)}")
        c3.write(f"{row.get('available_beds',0)}/{row.get('total_beds',0)} Beds")

        # DELETE (only for rooms sheet rows)
        if c4.button("❌", key=f"del_{i}"):

            if i >= len(owner_rooms) - len(rooms_df):
                client = get_client()
                sheet = client.open_by_key(PG_APP_ID).worksheet("rooms")
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

            if st.button("Save", key=f"save_{i}"):

                client = get_client()
                sheet = client.open_by_key(PG_APP_ID).worksheet("rooms")

                sheet.update(f"D{i+2}:G{i+2}", [[
                    floor,
                    row.get("sharing",2),
                    total,
                    available
                ]])

                st.cache_data.clear()
                st.rerun()

    # ---------------- ADD ROOM ----------------
    st.subheader("➕ Add Room")

    new_room = st.text_input("Room Number")
    new_floor = st.number_input("Floor", 0)
    new_sharing = st.number_input("Sharing", 1)
    new_total = st.number_input("Total Beds", 1)
    new_available = st.number_input("Available Beds", 0, new_total)

    if st.button("Add Room"):

        client = get_client()
        sheet = client.open_by_key(PG_APP_ID).worksheet("rooms")

        sheet.append_row([
            pg_id,
            pg_name,
            new_room,
            new_floor,
            new_sharing,
            new_total,
            new_available,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ])

        st.success("Room Added ✅")
        st.cache_data.clear()
        st.rerun()