import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# -----------------------
# AUTH
# -----------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_client():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scope
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"GCP Auth Error: {e}")
        st.stop()

# -----------------------
# LOAD DATA
# -----------------------
@st.cache_data(ttl=60)
def load_data():
    client = get_client()

    # ---------------- PG DATA ----------------
    try:
        pg_file = client.open_by_key(PG_DATA_ID)
        pg_sheet = pg_file.worksheet("Sheet1")
        pg_df = pd.DataFrame(pg_sheet.get_all_records())

        pg_df.columns = pg_df.columns.str.strip()
        pg_df["pg_id"] = pg_df["pg_id"].astype(str).str.strip()
        pg_df["pg_name"] = pg_df["pg_name"].astype(str).str.strip()

    except Exception as e:
        st.warning(f"PG Data Load Failed: {e}")
        pg_df = pd.DataFrame(columns=["pg_id", "pg_name"])

    # ---------------- APP DATA ----------------
    try:
        app_file = client.open_by_key(PG_APP_ID)

        try:
            owners_df = pd.DataFrame(app_file.worksheet("Owners").get_all_records())
        except:
            owners_df = pd.DataFrame(columns=["username", "password", "pg_id", "pg_name"])

        try:
            rooms_df = pd.DataFrame(app_file.worksheet("rooms").get_all_records())
        except:
            rooms_df = pd.DataFrame()

        try:
            bookings_df = pd.DataFrame(app_file.worksheet("Bookings").get_all_records())
        except:
            bookings_df = pd.DataFrame()

    except Exception as e:
        st.error(f"PG_APP connection failed ❌: {e}")
        owners_df = pd.DataFrame()
        rooms_df = pd.DataFrame()
        bookings_df = pd.DataFrame()

    return pg_df, owners_df, rooms_df, bookings_df

# -----------------------
# GET SHEETS (SAFE)
# -----------------------
def get_sheets():
    client = get_client()

    try:
        app_file = client.open_by_key(PG_APP_ID)
    except Exception as e:
        st.error(f"Sheet Access Error ❌: {e}")
        return None, None, None

    try:
        owners_sheet = app_file.worksheet("Owners")
    except:
        owners_sheet = None

    try:
        rooms_sheet = app_file.worksheet("rooms")
    except:
        rooms_sheet = None

    try:
        bookings_sheet = app_file.worksheet("Bookings")
    except:
        bookings_sheet = None

    return owners_sheet, rooms_sheet, bookings_sheet

pg_df, owners_df, rooms_df, bookings_df = load_data()
owners_sheet, rooms_sheet, bookings_sheet = get_sheets()

# -----------------------
# SESSION
# -----------------------
if "login" not in st.session_state:
    st.session_state.login = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "username" not in st.session_state:
    st.session_state.username = ""

# -----------------------
# LOGIN
# -----------------------
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
            if owners_df.empty:
                st.error("Owners data not loaded ❌")
                st.stop()

            owners_df["username"] = owners_df["username"].astype(str).str.strip().str.lower()
            owners_df["password"] = owners_df["password"].astype(str).str.strip()

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
                st.error("Invalid Owner ❌")

# -----------------------
# ADMIN DASHBOARD
# -----------------------
elif st.session_state.role == "admin":

    st.title("🛠 Admin Dashboard")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.subheader("➕ Create Owner")

    pg_names = pg_df["pg_name"].dropna().unique().tolist()
    selected_pg = st.selectbox("Select PG", pg_names)

    new_user = st.text_input("Owner Username")
    new_pass = st.text_input("Owner Password")

    if st.button("Create Owner"):
        if owners_sheet is None:
            st.error("Sheet not connected ❌")
        elif new_user and new_pass:
            try:
                pg_id = pg_df[pg_df["pg_name"] == selected_pg]["pg_id"].values[0]

                owners_sheet.append_row([
                    new_user.strip(),
                    new_pass.strip(),
                    pg_id,
                    selected_pg
                ])

                st.success("Owner Created ✅")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Enter all fields ❌")

    st.subheader("📋 Owners List")
    st.dataframe(owners_df, use_container_width=True)

# -----------------------
# OWNER DASHBOARD
# -----------------------
elif st.session_state.role == "owner":

    st.title("Owner Dashboard")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.dataframe(rooms_df)