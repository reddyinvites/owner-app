import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("🏠 PG Management System")

# ---------- AUTH ----------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

# ---------- ONE FILE ----------
FILE_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

file = client.open_by_key(FILE_ID)

# ✅ ALL SHEETS FROM SAME FILE
pg_sheet = file.worksheet("Sheet1")   # PG DATA
owners_sheet = file.worksheet("Owners")  # Owners
rooms_sheet = file.worksheet("rooms")  # Rooms

# ---------- LOAD ----------
@st.cache_data(ttl=5)
def load():
    pg = pd.DataFrame(pg_sheet.get_all_records())
    owners = pd.DataFrame(owners_sheet.get_all_records())
    return pg, owners

pg_df, owners_df = load()

# ---------- LOGIN ----------
st.subheader("Login")

role = st.selectbox("Role", ["Admin", "Owner"])

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):

    if role == "Admin":
        if username == "admin" and password == "admin123":
            st.success("Admin Login ✅")
        else:
            st.error("Wrong Admin")

    else:
        user = owners_df[
            (owners_df["username"].astype(str).str.strip() == username.strip()) &
            (owners_df["password"].astype(str).str.strip() == password.strip())
        ]

        if not user.empty:
            st.success("Owner Login ✅")
            st.write("PG ID:", user.iloc[0]["pg_id"])
        else:
            st.error("Invalid Owner")