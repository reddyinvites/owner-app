import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

# ---------- FILE ID ----------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

file = client.open_by_key(PG_DATA_ID)

pg_sheet = file.worksheet("Sheet1")   # PG DATA
owners_sheet = file.worksheet("Owners")  # OWNERS

# ---------- LOAD DATA ----------
@st.cache_data(ttl=5)
def load():
    pg = pd.DataFrame(pg_sheet.get_all_records())
    owners = pd.DataFrame(owners_sheet.get_all_records())
    return pg, owners

pg_df, owners_df = load()

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

        if role == "Admin":
            if username == "admin" and password == "admin123":
                st.session_state.page = "admin"
                st.rerun()
            else:
                st.error("Invalid Admin Login")

        else:
            if not owners_df.empty:
                user = owners_df[
                    (owners_df["username"].astype(str).str.strip() == username.strip()) &
                    (owners_df["password"].astype(str).str.strip() == password.strip())
                ]

                if not user.empty:
                    st.session_state.page = "owner"
                    st.session_state.pg_id = user.iloc[0]["pg_id"]
                    st.rerun()
                else:
                    st.error("Invalid Owner Login")

# ================= ADMIN =================
elif st.session_state.page == "admin":

    st.header("🧑‍💼 Admin Dashboard")

    st.subheader("➕ Create Owner")

    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")

    # PG DROPDOWN
    if not pg_df.empty:
        pg_options = pg_df["pg_name"].dropna().tolist()
    else:
        pg_options = []

    selected_pg = st.selectbox("Select PG", pg_options)

    if st.button("Create Owner"):

        if new_user == "" or new_pass == "":
            st.error("All fields required")

        else:
            # GET PG ID FROM NAME
            pg_id = pg_df[pg_df["pg_name"] == selected_pg].iloc[0]["pg_id"]

            owners_sheet.append_row([new_user, new_pass, pg_id])

            st.success("Owner Created ✅")
            st.cache_data.clear()
            st.rerun()

    # SHOW OWNERS
    st.subheader("📋 Owners List")

    if not owners_df.empty:
        st.dataframe(owners_df)

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()

# ================= OWNER =================
elif st.session_state.page == "owner":

    st.header("🏠 Owner Dashboard")

    st.info(f"PG ID: {st.session_state.pg_id}")

    my_pg = pg_df[pg_df["pg_id"] == st.session_state.pg_id]

    if not my_pg.empty:
        st.dataframe(my_pg)

    if st.button("🚪 Logout"):
        st.session_state.page = "login"
        st.rerun()