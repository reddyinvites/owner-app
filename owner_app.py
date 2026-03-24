import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Owner Dashboard", layout="centered")

st.title("🏠 Owner - Manage Rooms")

# -------- OWNER LOGIN CONFIG --------
users = {
    "gents_pg": {
        "password": "gents@123",
        "pg": "Amulya Gents PG"
    },
    "female_pg": {
        "password": "female@123",
        "pg": "Amulya Female Pgs"
    }
}

# -------- SESSION --------
if "login" not in st.session_state:
    st.session_state.login = False

# -------- LOGIN SCREEN --------
if not st.session_state.login:
    st.subheader("🔐 Owner Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state.login = True
            st.session_state.user = username
            st.success("✅ Login successful")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

    st.stop()

# -------- CURRENT OWNER --------
owner = st.session_state.user
owner_pg = users[owner]["pg"]

st.success(f"👤 Logged in: {owner}")
st.info(f"🏠 PG: {owner_pg}")

# -------- GOOGLE SHEETS CONNECT --------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

sheet = client.open_by_key(
    "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"
).worksheet("Sheet1")

# -------- HEADERS --------
headers = [
    "pg_name", "room_no", "floor",
    "sharing", "available_beds", "last_updated"
]

try:
    existing = sheet.row_values(1)
except:
    existing = []

if not existing:
    sheet.append_row(headers)

# -------- LOAD DATA --------
data = sheet.get_all_records()
df = pd.DataFrame(data)

# -------- FILTER OWNER DATA --------
if not df.empty:
    df = df[df["pg_name"] == owner_pg]

# -------- ADD / UPDATE ROOM --------
st.subheader("➕ Add / Update Room")

room_no = st.text_input("Room Number (e.g. 101, 201)")
st.caption("💡 Tip: 101=Floor1, 201=Floor2")

floor = st.number_input("Floor", min_value=1, max_value=20, step=1)
sharing = st.selectbox("Sharing Type", [1,2,3,4,5,6])
available = st.number_input("Available Beds", min_value=0, max_value=sharing)

if st.button("💾 Save / Update"):

    if room_no.strip() == "":
        st.error("⚠️ Enter room number")

    else:
        all_data = sheet.get_all_records()
        found = False

        for i, row in enumerate(all_data):
            if (
                row["pg_name"] == owner_pg and
                str(row["room_no"]) == str(room_no)
            ):
                # UPDATE
                sheet.update(f"A{i+2}:F{i+2}", [[
                    owner_pg,
                    room_no,
                    int(floor),
                    int(sharing),
                    int(available),
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ]])
                st.success("✅ Room Updated")
                found = True
                break

        if not found:
            # ADD NEW
            sheet.append_row([
                owner_pg,
                room_no,
                int(floor),
                int(sharing),
                int(available),
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])
            st.success("✅ New Room Added")

        st.rerun()

# -------- DISPLAY --------
st.subheader("📊 Room Data")

if not df.empty:

    df["floor"] = df["floor"].astype(int)
    df["room_no"] = df["room_no"].astype(int)

    df = df.sort_values(by=["floor", "room_no"])

    floors = df["floor"].unique()

    for f in floors:
        st.markdown(f"### 🏢 Floor {f}")
        floor_df = df[df["floor"] == f]
        st.dataframe(floor_df, use_container_width=True)

else:
    st.info("No rooms added yet")

# -------- LOGOUT --------
if st.button("🚪 Logout"):
    st.session_state.login = False
    st.rerun()