import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Owner Availability", layout="centered")

st.title("🏠 Owner - Update PG Availability")

# -------- GOOGLE SHEETS CONNECT --------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

# ✅ NEW SHEET CONNECT
sheet = client.open_by_key(
    "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"
).worksheet("Sheet1")


# -------- LOAD DATA --------
data = sheet.get_all_records()
df = pd.DataFrame(data)

# -------- INPUT --------
pg_name = st.text_input("PG Name")
available = st.number_input("Available Beds", min_value=0, step=1)

# -------- UPDATE --------
if st.button("Update Availability"):

    if pg_name.strip() == "":
        st.error("⚠️ Enter PG name")
    else:

        found = False

        for i, row in enumerate(data):

            # column safe check
            if "pg_name" in row and row["pg_name"].lower() == pg_name.lower():

                # update existing row
                sheet.update_cell(i+2, 2, int(available))  # available_beds
                sheet.update_cell(i+2, 3, datetime.now().strftime("%Y-%m-%d %H:%M"))

                st.success("✅ Availability Updated")
                found = True
                break

        if not found:
            # add new row
            sheet.append_row([
                pg_name,
                int(available),
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])

            st.success("✅ New PG Added")

        st.rerun()


# -------- DISPLAY --------
st.subheader("📊 Current Availability")

if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info("No data yet")