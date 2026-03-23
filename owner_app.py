import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Owner Availability", layout="centered")

st.title("🏠 Owner - Update PG Availability")

# -------- CONNECT GOOGLE SHEETS --------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

# 👉 YOUR SHEET ID (change if needed)
sheet = client.open_by_key("1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q").sheet1


# -------- LOAD DATA --------
data = sheet.get_all_records()
df = pd.DataFrame(data)

# -------- INPUT --------
pg_name = st.text_input("PG Name")
available = st.number_input("Available Beds", min_value=0, step=1)

# -------- UPDATE --------
if st.button("Update Availability"):

    if pg_name.strip() == "":
        st.error("Enter PG name")
    else:

        found = False

        for i, row in enumerate(data):

            if row["pg_name"].lower() == pg_name.lower():

                # update existing
                sheet.update_cell(i+2, 2, int(available))
                sheet.update_cell(i+2, 3, datetime.now().strftime("%Y-%m-%d %H:%M"))

                st.success("✅ Availability Updated")
                found = True
                break

        if not found:
            # add new PG
            sheet.append_row([
                pg_name,
                int(available),
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])
            st.success("✅ New PG Added")

        st.rerun()


# -------- SHOW DATA --------
st.subheader("📊 Current Availability")

if not df.empty:
    st.dataframe(df)
else:
    st.info("No data yet")
