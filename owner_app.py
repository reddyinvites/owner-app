import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Owner Room Control", layout="centered")

st.title("🏠 Owner - Manage Rooms")

# -------- GOOGLE SHEETS CONNECT --------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

sheet = client.open_by_key(
    "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"
).worksheet("Sheet1")


# -------- ENSURE HEADERS --------
headers = [
    "pg_name", "room_no", "floor",
    "sharing", "available_beds", "last_updated"
]

existing = sheet.row_values(1)

if existing != headers:
    sheet.clear()
    sheet.append_row(headers)

# -------- LOAD DATA --------
data = sheet.get_all_records()
df = pd.DataFrame(data)

# -------- FORM --------
st.subheader("➕ Add / Update Room")

pg_name = st.text_input("PG Name")
room_no = st.text_input("Room Number (e.g. 101)")
floor = st.number_input("Floor", min_value=1, max_value=20, step=1)
sharing = st.selectbox("Sharing Type", [1,2,3,4,5,6])
available = st.number_input("Available Beds", min_value=0, max_value=sharing)

# -------- VALIDATION --------
if available > sharing:
    st.error("❌ Available beds cannot exceed sharing")

# -------- SAVE --------
if st.button("💾 Save / Update"):

    if pg_name.strip() == "" or room_no.strip() == "":
        st.error("⚠️ Enter PG name & Room number")

    else:
        found = False

        for i, row in enumerate(data):
            if (
                row["pg_name"].lower() == pg_name.lower() and
                str(row["room_no"]) == str(room_no)
            ):
                # UPDATE EXISTING
                sheet.update(f"A{i+2}:F{i+2}", [[
                    pg_name,
                    room_no,
                    int(floor),
                    int(sharing),
                    int(available),
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ]])
                st.success("✅ Room Updated")
                found = True
                break

        if not found:
            # ADD NEW ROOM
            sheet.append_row([
                pg_name,
                room_no,
                int(floor),
                int(sharing),
                int(available),
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])
            st.success("✅ New Room Added")

        st.rerun()


# -------- DISPLAY --------
st.subheader("📊 Room Data")

if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info("No rooms added yet")