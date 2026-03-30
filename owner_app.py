import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="PG Management System")

st.title("🏠 PG Management System")

# ---------- GOOGLE AUTH ----------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

# ---------- FILE IDs ----------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

# ---------- CONNECT ----------
try:
    pg_file = client.open_by_key(PG_DATA_ID)
    pg_sheet = pg_file.worksheet("Sheet1")
    st.success("✅ PG DATA Connected")

    pg_df = pd.DataFrame(pg_sheet.get_all_records())

except:
    st.error("❌ PG DATA Connection Failed")
    st.stop()

# ---------- SESSION ----------
if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= LOGIN =================
if st.session_state.page == "login":

    st.subheader("🔐 Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # ADMIN LOGIN
        if role == "Admin":
            if username == "admin" and password == "admin123":
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("Invalid Admin Login")

        # OWNER LOGIN (use pg_name as username)
        else:
            if not pg_df.empty:
                user = pg_df[
                    pg_df["pg_name"].astype(str).str.strip() == username.strip()
                ]

                if not user.empty:
                    st.session_state.page = "owner"
                    st.session_state.pg_id = user.iloc[0]["pg_id"]
                    st.session_state.pg_name = user.iloc[0]["pg_name"]
                    st.rerun()
                else:
                    st.error("Owner not found")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    st.subheader("📊 PG List")

    if not pg_df.empty:
        st.dataframe(pg_df)
    else:
        st.info("No PG data")

    # ADD NEW PG
    st.subheader("➕ Add PG")

    pg_name = st.text_input("PG Name")
    location = st.text_input("Location")
    owner_name = st.text_input("Owner Name")
    owner_number = st.text_input("Owner Number")

    if st.button("Add PG"):

        if pg_name == "" or location == "":
            st.error("Fill all fields")
        else:
            new_id = "PG" + str(len(pg_df) + 1).zfill(3)

            pg_sheet.append_row([
                new_id,
                pg_name,
                location,
                owner_name,
                owner_number,
                ""
            ])

            st.success("PG Added ✅")
            st.rerun()

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    st.info(f"PG ID: {st.session_state.pg_id}")
    st.info(f"PG Name: {st.session_state.pg_name}")

    # SHOW PG DETAILS
    my_pg = pg_df[pg_df["pg_id"] == st.session_state.pg_id]

    if not my_pg.empty:
        st.dataframe(my_pg)

    st.subheader("🛏 Update Sharing JSON")

    sharing = st.text_area("Sharing JSON")

    if st.button("Update"):

        index = pg_df[pg_df["pg_id"] == st.session_state.pg_id].index[0] + 2

        pg_sheet.update_cell(index, 6, sharing)

        st.success("Updated ✅")
        st.rerun()

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()