import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="PG Management System", layout="centered")

st.title("🏠 PG Management System")

# -------- GOOGLE SHEETS --------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

SHEET_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

try:
    sheet = client.open_by_key(SHEET_ID)
    room_sheet = sheet.worksheet("Sheet1")
    owner_sheet = sheet.worksheet("Owners")
    st.success("✅ Connected to Google Sheet")
except Exception as e:
    st.error(f"❌ ERROR: {e}")
    st.stop()

# -------- CACHE --------
@st.cache_data(ttl=30)
def load_data():
    room_df = pd.DataFrame(room_sheet.get_all_records())
    owner_df = pd.DataFrame(owner_sheet.get_all_records())
    return room_df, owner_df

room_df, owner_df = load_data()

# -------- REFRESH --------
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# -------- SESSION --------
if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= LOGIN =================
if st.session_state.page == "login":

    st.subheader("🔐 Login")

    role = st.selectbox("Login as", ["Owner", "Admin"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if role == "Admin":
            if username == "admin" and password == "admin123":
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("Invalid admin login")

        else:
            if not owner_df.empty:
                owner_df.columns = owner_df.columns.str.strip()

                user = owner_df[
                    (owner_df["username"].astype(str).str.strip() == username.strip()) &
                    (owner_df["password"].astype(str).str.strip() == password.strip())
                ]

                if not user.empty:
                    st.session_state.page = "owner"
                    st.session_state.owner = username.strip()
                    st.session_state.pg = user.iloc[0]["pg_name"]
                    st.rerun()
                else:
                    st.error("Invalid owner login")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    menu = st.radio("Menu", ["➕ Create Owner", "📋 Owners List", "📊 PG Dashboard"])

    if menu == "➕ Create Owner":

        new_pg = st.text_input("PG Name")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        if st.button("Create"):
            owner_sheet.append_row([new_user, new_pass, new_pg])
            st.success("Owner Created")
            st.cache_data.clear()
            st.rerun()

    elif menu == "📋 Owners List":

        if not owner_df.empty:

            for i, row in owner_df.iterrows():
                col1, col2, col3, col4 = st.columns([2,2,2,1])

                col1.write(row["username"])
                col2.write(row["password"])
                col3.write(row["pg_name"])

                if col4.button("❌", key=f"del_{i}"):
                    owner_sheet.delete_rows(i+2)
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.info("No owners")

    elif menu == "📊 PG Dashboard":

        if not room_df.empty:
            for pg in room_df["pg_name"].unique():
                st.markdown(f"## 🏠 {pg}")
                pg_df = room_df[room_df["pg_name"] == pg]

                for f in pg_df["floor"].unique():
                    st.markdown(f"### Floor {f}")
                    st.dataframe(pg_df[pg_df["floor"] == f])

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    owner = st.session_state.owner
    pg = st.session_state.pg

    st.info(f"PG: {pg}")

    if not room_df.empty:
        my_df = room_df[room_df["owner_id"].astype(str) == owner]
    else:
        my_df = pd.DataFrame()

    # -------- ADD ROOM --------
st.subheader("➕ Add Room")

room = st.text_input("Room No")
floor = st.number_input("Floor", min_value=1, step=1)

sharing = st.selectbox("Sharing", [1,2,3,4,5])

# ✅ ALWAYS CORRECT NOW
st.success(f"Max beds allowed: {sharing}")

beds = st.number_input(
    "Available Beds",
    min_value=0,
    step=1
)

if st.button("Save"):

    if room.strip() == "":
        st.error("Enter Room Number")

    elif beds > sharing:
        st.error(f"❌ Beds ({beds}) cannot exceed Sharing ({sharing})")

    else:
        room_sheet.append_row([
            pg,
            room,
            floor,
            sharing,
            beds,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            owner
        ])

        st.success("✅ Room Added")
        st.cache_data.clear()
        st.rerun()

    # -------- DISPLAY --------
    st.subheader("📊 My Rooms")

    if not my_df.empty:

        for f in my_df["floor"].unique():
            st.markdown(f"### Floor {f}")
            st.dataframe(my_df[my_df["floor"] == f])

    else:
        st.info("No rooms added")

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()