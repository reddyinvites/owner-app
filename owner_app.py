import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- CONFIG ----------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

st.set_page_config(page_title="PG Manager", layout="centered")

# ---------------- GOOGLE ----------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(creds)

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=60)
def load_data():
    client = get_client()

    rooms_df = pd.DataFrame(
        client.open_by_key(PG_APP_ID).worksheet("rooms").get_all_records()
    )

    owners_df = pd.DataFrame(
        client.open_by_key(PG_APP_ID).worksheet("Owners").get_all_records()
    )

    try:
        pg_df = pd.DataFrame(
            client.open_by_key(PG_DATA_ID).worksheet("Sheet1").get_all_records()
        )
    except:
        pg_df = pd.DataFrame()

    for df in [rooms_df, owners_df, pg_df]:
        if not df.empty:
            df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    if not owners_df.empty:
        owners_df["username"] = owners_df["username"].str.lower().str.strip()
        owners_df["password"] = owners_df["password"].astype(str).str.strip()
        owners_df["pg_id"] = owners_df["pg_id"].astype(str).str.strip()

    if not rooms_df.empty:
        rooms_df["pg_id"] = rooms_df["pg_id"].astype(str).str.strip()

    return rooms_df, owners_df, pg_df

# ---------------- UPDATE PG SUMMARY ----------------
def update_pg_summary(pg_id, pg_name):
    client = get_client()

    rooms_sheet = client.open_by_key(PG_APP_ID).worksheet("rooms")
    pg_sheet = client.open_by_key(PG_DATA_ID).worksheet("Sheet1")

    rooms = pd.DataFrame(rooms_sheet.get_all_records())

    if rooms.empty:
        total_beds = 0
        available_beds = 0
    else:
        rooms.columns = rooms.columns.str.strip().str.lower().str.replace(" ", "_")
        rooms["pg_id"] = rooms["pg_id"].astype(str)

        pg_rooms = rooms[rooms["pg_id"] == str(pg_id)]

        total_beds = int(pg_rooms["total_beds"].sum())
        available_beds = int(pg_rooms["available_beds"].sum())

    pg_sheet.append_row([
        pg_id,
        pg_name,
        total_beds,
        available_beds
    ])

# ---------------- INIT ----------------
rooms_df, owners_df, pg_df = load_data()

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

    st.subheader("🏠 PG List")
    st.dataframe(pg_df, use_container_width=True)

    st.subheader("🛏 Manage Rooms")

    for i, row in rooms_df.iterrows():

        c1, c2, c3, c4 = st.columns([2,2,2,1])

        c1.write(row["room_no"])
        c2.write(f"{row['available_beds']}/{row['total_beds']}")
        c3.write(row["pg_name"])

        if c4.button("❌", key=f"admin_del_{i}"):
            sheet = get_client().open_by_key(PG_APP_ID).worksheet("rooms")
            sheet.delete_rows(i + 2)

            update_pg_summary(row["pg_id"], row["pg_name"])

            st.cache_data.clear()
            st.rerun()

# ---------------- OWNER ----------------
elif st.session_state.role == "owner":

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    owner = owners_df[owners_df["username"] == st.session_state.username]

    pg_id_owner = owner.iloc[0]["pg_id"]
    pg_name_owner = owner.iloc[0]["pg_name"]

    st.title(f"🏠 {pg_name_owner}")

    owner_rooms = rooms_df[rooms_df["pg_id"] == pg_id_owner]

    st.subheader("🛏 Rooms")

    for i, row in owner_rooms.iterrows():

        c1, c2, c3, c4 = st.columns([2,2,2,1])

        c1.write(f"Room: {row['room_no']}")
        c2.write(f"Floor: {row['floor']}")
        c3.write(f"{row['available_beds']}/{row['total_beds']} Beds")

        if c4.button("❌", key=f"del_{i}"):
            sheet = get_client().open_by_key(PG_APP_ID).worksheet("rooms")
            sheet.delete_rows(i + 2)

            update_pg_summary(pg_id_owner, pg_name_owner)

            st.cache_data.clear()
            st.rerun()

    # -------- ADD ROOM --------
    st.subheader("➕ Add Room")

    if pg_df.empty:
        st.error("❌ Sheet1 is empty")
        st.stop()

    required_cols = ["pg_id", "pg_name", "room_no", "floor", "total_beds", "available_beds"]

    for col in required_cols:
        if col not in pg_df.columns:
            st.error(f"❌ Missing column: {col}")
            st.stop()

    pg_df = pg_df.dropna(subset=["pg_id", "pg_name"])

    pg_unique = pg_df.drop_duplicates(subset=["pg_id"])
    pg_display = pg_unique["pg_name"].tolist()

    selected_pg_name = st.selectbox("Select PG", pg_display)

    selected_pg_row = pg_unique[pg_unique["pg_name"] == selected_pg_name].iloc[0]

    pg_id = selected_pg_row["pg_id"]
    pg_name = selected_pg_row["pg_name"]

    pg_rooms = pg_df[pg_df["pg_id"] == pg_id]

    room_options = pg_rooms["room_no"].dropna().astype(str).unique().tolist()
    floor_options = pg_rooms["floor"].dropna().unique().tolist()
    total_options = pg_rooms["total_beds"].dropna().unique().tolist()
    avail_options = pg_rooms["available_beds"].dropna().unique().tolist()

    new_room = st.selectbox("Room Number", room_options)
    new_floor = st.selectbox("Floor", floor_options)
    new_total = st.selectbox("Total Beds", total_options)
    new_available = st.selectbox("Available Beds", avail_options)

    if st.button("Add Room"):

        sheet = get_client().open_by_key(PG_APP_ID).worksheet("rooms")

        sheet.append_row([
            pg_id,
            pg_name,
            new_room,
            new_floor,
            "",  # sharing removed
            new_total,
            new_available,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ])

        update_pg_summary(pg_id, pg_name)

        st.success("Room Added ✅")
        st.cache_data.clear()
        st.rerun()