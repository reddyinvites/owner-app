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

# ---------- FILE IDs ----------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"   # pg_data
PG_APP_ID = "👉 PUT pg_availability ID HERE"  # NEW FILE

# ---------- CONNECT ----------
pg_file = client.open_by_key(PG_DATA_ID)
pg_sheet = pg_file.worksheet("Sheet1")

app_file = client.open_by_key(PG_APP_ID)
owners_sheet = app_file.worksheet("Owners")

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

user = st.text_input("Username")
pwd = st.text_input("Password", type="password")

if st.button("Login"):

    if role == "Admin":
        if user == "admin" and pwd == "admin123":
            st.success("Admin Login Success")
        else:
            st.error("Wrong Admin")

    else:
        u = owners_df[
            (owners_df["username"] == user) &
            (owners_df["password"] == pwd)
        ]

        if not u.empty:
            st.success("Owner Login Success")
            st.write("PG ID:", u.iloc[0]["pg_id"])
        else:
            st.error("Invalid Owner")