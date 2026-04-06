import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- CONFIG ----------------
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# ---------------- UI STYLE ----------------
st.set_page_config(page_title="PG Manager", layout="centered")

st.markdown("""
<style>
.big-title {
    font-size:28px;
    font-weight:700;
}
.sub-title {
    font-size:20px;
    font-weight:600;
}
</style>
""", unsafe_allow_html=True)

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
@st.cache_data(ttl=120)
def load_data():
    client = get_client()

    rooms_df = pd.DataFrame(
        client.open_by_key(PG_APP_ID).worksheet("rooms").get_all_records()
    )

    owners_df = pd.DataFrame(
        client.open_by_key(PG_APP_ID).worksheet("Owners").get_all_records()
    )

    if not rooms_df.empty:
        rooms_df.columns = rooms_df.columns.str.strip()
        rooms_df["pg_id"] = rooms_df["pg_id"].astype(str).str.strip()

    if not owners_df.empty:
        owners_df.columns = owners_df.columns.str.strip()
        owners_df["username"] = owners_df["username"].astype(str).str.lower().str.strip()
        owners_df["password"] = owners_df["password"].astype(str).str.strip()
        owners_df["pg_id"] = owners_df["pg_id"].astype(str).str.strip()

    return rooms_df, owners_df

rooms_df, owners_df = load_data()

# ---------------- SESSION ----------------
if "login" not in st.session_state:
    st.session_state.login = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "username" not in st.session_state:
    st.session_state.username = ""

# ---------------- LOGIN ----------------
if not st.session_state.login:

    st.markdown('<p class="big-title">🔐 Login</p>', unsafe_allow_html=True)

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

# ---------------- ADMIN DASHBOARD ----------------
elif st.session_state.role == "admin":

    st.markdown('<p class="big-title">🛠 Admin Dashboard</p>', unsafe_allow_html=True)

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.markdown('<p class="sub-title">📊 Rooms Data</p>', unsafe_allow_html=True)
    st.dataframe(rooms_df, use_container_width=True)

    st.markdown('<p class="sub-title">👤 Owners</p>', unsafe_allow_html=True)
    st.dataframe(owners_df, use_container_width=True)

# ---------------- OWNER DASHBOARD ----------------
elif st.session_state.role == "owner":

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    owner = owners_df[owners_df["username"] == st.session_state.username]

    if owner.empty:
        st.error("Owner not found ❌")
        st.stop()

    pg_id = owner.iloc[0]["pg_id"]
    pg_name = owner.iloc[0]["pg_name"]

    st.markdown(f'<p class="big-title">🏠 {pg_name}</p>', unsafe_allow_html=True)

    # FILTER ROOMS
    owner_rooms = rooms_df[rooms_df["pg_id"] == pg_id]

    st.markdown('<p class="sub-title">🛏 Rooms</p>', unsafe_allow_html=True)

    for i, row in owner_rooms.iterrows():

        c1, c2, c3, c4 = st.columns([2,2,2,1])

        c1.write(f"Room: {row['room_no']}")
        c2.write(f"Floor: {row['floor']}")
        c3.write(f"{row['available_beds']}/{row['total_beds']} Beds")

        # DELETE
        if c4.button("❌", key=f"del_{i}"):
            client = get_client()
            sheet = client.open_by_key(PG_APP_ID).worksheet("rooms")
            sheet.delete_rows(i + 2)

            st.cache_data.clear()
            st.rerun()

        # EDIT
        if st.button("✏️ Edit", key=f"edit_{i}"):
            st.session_state[f"edit_{i}"] = True

        if st.session_state.get(f"edit_{i}", False):

            floor = st.number_input("Floor", value=int(row["floor"]), key=f"f{i}")
            sharing = st.number_input("Sharing", value=int(row["sharing"]), key=f"s{i}")
            total = st.number_input("Total Beds", value=int(row["total_beds"]), key=f"t{i}")
            available = st.number_input("Available Beds", value=int(row["available_beds"]), key=f"a{i}")

            if st.button("Save", key=f"save_{i}"):

                client = get_client()
                sheet = client.open_by_key(PG_APP_ID).worksheet("rooms")

                sheet.update(f"D{i+2}:G{i+2}", [[
                    floor,
                    sharing,
                    total,
                    available
                ]])

                st.cache_data.clear()
                st.rerun()

    # ---------------- ADD ROOM ----------------
    st.markdown('<p class="sub-title">➕ Add Room</p>', unsafe_allow_html=True)

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