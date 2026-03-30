import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="PG Management System", layout="centered")
st.title("🏠 PG Management System")

# ---------------- GOOGLE SHEETS ----------------
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
    spreadsheet = client.open_by_key(SHEET_ID)
    room_sheet = spreadsheet.worksheet("Sheet1")
    owner_sheet = spreadsheet.worksheet("Owners")
    st.success("✅ Connected")
except Exception as e:
    st.error("❌ Sheet Connection Failed")
    st.write(e)
    st.stop()

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=30)
def load_data():
    room_df = pd.DataFrame(room_sheet.get_all_records())
    owner_df = pd.DataFrame(owner_sheet.get_all_records())
    return room_df, owner_df

room_df, owner_df = load_data()

# ---------------- GENERATE UNIQUE PG ID ----------------
def generate_pg_id():
    if owner_df.empty or "pg_id" not in owner_df.columns:
        return "PG001"

    ids = owner_df["pg_id"].astype(str)
    nums = [int(i.replace("PG","")) for i in ids if i.startswith("PG")]

    return f"PG{max(nums)+1:03d}" if nums else "PG001"

# ---------------- SESSION ----------------
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
                    st.session_state.pg = user.iloc[0]["pg_id"]
                    st.rerun()
                else:
                    st.error("Invalid owner login")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    menu = st.radio("Menu", ["➕ Create Owner", "📋 Owners List"])

    # -------- CREATE OWNER --------
    if menu == "➕ Create Owner":

        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        auto_pg_id = generate_pg_id()
        st.info(f"Auto PG ID: {auto_pg_id}")

        if st.button("Create Owner"):

            if new_user.strip() == "" or new_pass.strip() == "":
                st.error("All fields required")

            else:
                if not owner_df.empty:
                    users = owner_df["username"].astype(str).str.strip().tolist()
                    if new_user.strip() in users:
                        st.error("❌ Username already exists")
                        st.stop()

                owner_sheet.append_row([new_user, new_pass, auto_pg_id])

                st.balloons()
                st.success(f"🎉 Owner Created! PG ID: {auto_pg_id}")

                st.cache_data.clear()
                st.rerun()

    # -------- OWNER LIST --------
    elif menu == "📋 Owners List":

        if not owner_df.empty:
            for i, row in owner_df.iterrows():

                col1, col2, col3, col4 = st.columns([2,2,2,1])

                col1.write(row["username"])
                col2.write(row["password"])
                col3.write(row["pg_id"])

                if col4.button("❌", key=f"del_{i}"):
                    owner_sheet.delete_rows(i+2)
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.info("No owners")

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    owner = st.session_state.owner
    pg = st.session_state.pg

    st.info(f"PG ID: {pg}")

    # FILTER DATA
    if not room_df.empty:
        my_df = room_df[room_df["owner_id"].astype(str) == owner]
    else:
        my_df = pd.DataFrame()

    st.subheader("➕ Add Room")

    room = st.text_input("Room No")
    floor = st.number_input("Floor", min_value=1, step=1)
    sharing = st.selectbox("Sharing", [1,2,