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


# -------- SAFE HEADER --------
headers = [
    "pg_name", "room_no", "floor",
    "sharing", "available_beds", "last_updated"
]

try:
    existing = sheet.row_values(1)
except:
    existing = []

if not existing:
    sheet.append_row(headers)


# -------- LOAD DATA --------
data = sheet.get_all_records()
df = pd.DataFrame(data)


# -------- FORM --------
st.subheader("➕ Add / Update Room")

# -------- PG SELECT --------
existing_pgs = df["pg_name"].dropna().unique().tolist() if not df.empty else []

pg_option = st.selectbox("Select PG", ["➕ Add New PG"] + existing_pgs)

if pg_option == "➕ Add New PG":
    pg_name = st.text_input("Enter New PG Name")
else:
    pg_name = pg_option

# -------- ROOM INPUT --------
room_no = st.text_input("Room Number (e.g. 101, 201)")
st.caption("💡 Tip: 101 = Floor 1, 201 = Floor 2")

floor = st.number_input("Floor", min_value=1, max_value=20, step=1)

sharing = st.selectbox("Sharing Type", [1, 2, 3, 4, 5, 6])

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
                str(row["pg_name"]).lower() == pg_name.lower() and
                str(row["room_no"]) == str(room_no)
            ):
                # UPDATE
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
            # ADD NEW
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

    # get unique PGs
    pgs = df["pg_name"].dropna().unique()

    for pg in pgs:

        st.markdown(f"### 🏠 {pg}")

        pg_df = df[df["pg_name"] == pg].copy()

        # convert room_no to number for proper sorting
        pg_df["room_no"] = pd.to_numeric(pg_df["room_no"], errors="coerce")

        # sort by floor and room
        pg_df = pg_df.sort_values(by=["floor", "room_no"])

        st.dataframe(pg_df, use_container_width=True)

        st.markdown("---")

else:
    st.info("No rooms added yet")