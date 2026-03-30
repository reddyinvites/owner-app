import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------
# CONFIG
# -----------------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"
PG_APP_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

# -----------------------
# AUTH
# -----------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

# -----------------------
# LOAD DATA
# -----------------------
def load_data():
    pg_file = client.open_by_key(PG_DATA_ID)
    pg_sheet = pg_file.worksheet("Sheet1")
    pg_df = pd.DataFrame(pg_sheet.get_all_records())

    app_file = client.open_by_key(PG_APP_ID)
    owners_sheet = app_file.worksheet("Owners")
    owners_df = pd.DataFrame(owners_sheet.get_all_records())

    return pg_df, owners_df, owners_sheet

pg_df, owners_df, owners_sheet = load_data()

# -----------------------
# UI
# -----------------------
st.title("🏠 PG Management System")
st.success("Connected Successfully ✅")

# -----------------------
# SELECT PG
# -----------------------
pg_names = pg_df["pg_name"].dropna().unique().tolist()
selected_pg = st.selectbox("Select PG", pg_names)

pg_id = None
if selected_pg:
    row = pg_df[pg_df["pg_name"] == selected_pg]
    if not row.empty:
        pg_id = row.iloc[0]["pg_id"]

# -----------------------
# CREATE OWNER
# -----------------------
st.subheader("➕ Create Owner")

username = st.text_input("Username")
password = st.text_input("Password")

if st.button("Create Owner"):

    if username and password and pg_id:

        # ❗ Duplicate check
        if not owners_df.empty and username in owners_df["username"].values:
            st.error("Username already exists ❌")

        else:
            try:
                new_row = [
                    str(username),
                    str(password),
                    str(pg_id),
                    str(selected_pg)
                ]

                owners_sheet.append_row(
                    new_row,
                    value_input_option="USER_ENTERED"
                )

                st.success("Owner Created ✅")
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    else:
        st.error("Fill all fields")

# -----------------------
# OWNERS LIST
# -----------------------
st.subheader("📋 Owners List")

if not owners_df.empty:
    st.dataframe(owners_df)

    # -----------------------
    # DELETE OWNER
    # -----------------------
    st.subheader("❌ Delete Owner")

    selected_user = st.selectbox(
        "Select Owner",
        owners_df["username"].tolist()
    )

    if st.button("Delete Owner"):

        try:
            cell = owners_sheet.find(selected_user)

            if cell:
                owners_sheet.delete_rows(cell.row)
                st.success("Deleted Successfully ✅")
                st.rerun()

        except:
            st.error("User not found")

else:
    st.info("No owners available")