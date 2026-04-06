import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
PG_DATA_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

st.set_page_config(page_title="PG System", layout="centered")

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
    sheet = client.open_by_key(PG_DATA_ID)

    # -------- ROOMS --------
    df = pd.DataFrame(sheet.worksheet("Sheet1").get_all_records())
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # -------- OWNERS --------
    owners_ws = sheet.worksheet("Owners")
    raw = owners_ws.get_all_values()

    if len(raw) <= 1:
        owners = pd.DataFrame(columns=["username","password","pg_id","pg_name"])
    else:
        headers = [h.strip().lower().replace(" ", "_") for h in raw[0]]
        owners = pd.DataFrame(raw[1:], columns=headers)

        # CLEAN DATA (VERY IMPORTANT)
        owners["username"] = owners["username"].astype(str).str.strip().str.lower()
        owners["password"] = owners["password"].astype(str).str.replace("\n","").str.strip()
        owners["pg_id"] = owners["pg_id"].astype(str).str.strip()
        owners["pg_name"] = owners["pg_name"].astype(str).str.strip()

    return df, owners

df, owners_df = load_data()

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
                st.error("❌ Invalid Admin")

        else:
            # 🔥 FINAL LOGIN FIX
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
                st.error("❌ Invalid Owner")

# =====================================================
# AFTER LOGIN
# =====================================================
else:

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if df.empty:
        st.error("❌ Sheet1 empty")
        st.stop()

    pg_unique = df.drop_duplicates(subset=["pg_id"])
    pg_names = pg_unique["pg_name"].tolist()

    # OWNER VIEW
    if st.session_state.role == "owner":
        owner_row = owners_df[
            owners_df["username"] == st.session_state.username
        ].iloc[0]

        selected_pg = owner_row["pg_name"]
        pg_id = owner_row["pg_id"]

        st.write(f"🏠 PG: {selected_pg}")

    else:
        selected_pg = st.selectbox("Select PG", pg_names)
        pg_row = pg_unique[pg_unique["pg_name"] == selected_pg].iloc[0]
        pg_id = pg_row["pg_id"]

    pg_rooms = df[df["pg_id"] == pg_id]

    # MENU
    if st.session_state.role == "admin":
        menu = st.sidebar.radio("📂 Menu", ["Admin Dashboard", "Room Manager"])
    else:
        menu = "Room Manager"

    # ---------------- ADMIN ----------------
    if menu == "Admin Dashboard":

        st.title("🛠 Admin Dashboard")

        st.subheader("🏠 PG Summary")
        summary = pg_rooms.groupby("pg_name")[["total_beds","available_beds"]].sum().reset_index()
        st.dataframe(summary)

        st.subheader("📋 All Rooms")
        st.dataframe(pg_rooms)

        st.subheader("➕ Create Owner")

        selected_pg_owner = st.selectbox("Select PG", pg_names)
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password")

        if st.button("Create Owner"):

            sheet = get_client().open_by_key(PG_DATA_ID).worksheet("Owners")

            pg_row = pg_unique[pg_unique["pg_name"] == selected_pg_owner].iloc[0]

            sheet.append_row([
                new_user.strip().lower(),
                new_pass.strip(),
                str(pg_row["pg_id"]),
                selected_pg_owner
            ])

            st.success("✅ Owner Created")

    # ---------------- ROOM MANAGER ----------------
    elif menu == "Room Manager":

        st.title("🏠 Room Manager")

        st.subheader("🛏 Rooms")

        for _, row in pg_rooms.iterrows():
            total = int(row["total_beds"])
            avail = int(row["available_beds"])

            if avail == 0:
                st.error(f"Room {row['room_no']} → FULL")
            else:
                st.success(f"Room {row['room_no']} → {avail}/{total} Available")