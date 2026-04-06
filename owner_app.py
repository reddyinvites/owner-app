import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- CONFIG ----------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

st.set_page_config(page_title="PG Manager", layout="centered")

# ---------------- GOOGLE ----------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(creds)

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=60)
def load_data():
    client = get_client()

    try:
        pg_df = pd.DataFrame(
            client.open_by_key(PG_DATA_ID).worksheet("Sheet1").get_all_records()
        )
    except:
        pg_df = pd.DataFrame()

    if not pg_df.empty:
        pg_df.columns = pg_df.columns.str.strip().str.lower().str.replace(" ", "_")

    return pg_df

pg_df = load_data()

# ---------------- UI ----------------
st.title("🏠 PG Room Manager")

if pg_df.empty:
    st.error("❌ Sheet1 is empty")
    st.stop()

required_cols = ["pg_id", "pg_name", "room_no", "floor", "total_beds", "available_beds"]

for col in required_cols:
    if col not in pg_df.columns:
        st.error(f"❌ Missing column: {col}")
        st.stop()

pg_df = pg_df.dropna(subset=["pg_id", "pg_name"])

# -------- PG DROPDOWN --------
pg_unique = pg_df.drop_duplicates(subset=["pg_id"])
pg_display = pg_unique["pg_name"].tolist()

selected_pg_name = st.selectbox("Select PG", pg_display)

selected_pg_row = pg_unique[pg_unique["pg_name"] == selected_pg_name].iloc[0]

pg_id = selected_pg_row["pg_id"]
pg_name = selected_pg_row["pg_name"]

# -------- ROOM DROPDOWN --------
pg_rooms = pg_df[pg_df["pg_id"] == pg_id]

room_options = pg_rooms["room_no"].astype(str).unique().tolist()

new_room = st.selectbox("Room Number", room_options)

room_data = pg_rooms[pg_rooms["room_no"].astype(str) == str(new_room)].iloc[0]

# -------- AUTO FILL --------
new_floor = int(room_data["floor"])
st.write(f"Floor: {new_floor}")

# -------- SHARING --------
sharing = st.selectbox("Sharing", [1, 2, 3, 4, 5])

# -------- TOTAL BEDS --------
new_total = st.number_input(
    "Total Beds",
    min_value=1,
    max_value=int(sharing),
    value=min(int(room_data["total_beds"]), int(sharing))
)

# -------- AVAILABLE BEDS --------
new_available = st.number_input(
    "Available Beds",
    min_value=0,
    max_value=int(new_total),
    value=min(int(room_data["available_beds"]), int(new_total))
)

# -------- SAVE --------
if st.button("Save Room"):

    if new_total > sharing:
        st.error("❌ Total beds cannot exceed sharing")
        st.stop()

    if new_available > new_total:
        st.error("❌ Available beds cannot exceed total beds")
        st.stop()

    sheet = get_client().open_by_key(PG_DATA_ID).worksheet("Sheet1")

    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    match_index = None

    for i, r in df.iterrows():
        if str(r["pg_id"]) == str(pg_id) and str(r["room_no"]) == str(new_room):
            match_index = i + 2
            break

    if match_index:

        headers = sheet.row_values(1)
        headers = [h.strip().lower().replace(" ", "_") for h in headers]

        total_col = headers.index("total_beds") + 1
        avail_col = headers.index("available_beds") + 1

        def col_letter(n):
            string = ""
            while n > 0:
                n, r = divmod(n - 1, 26)
                string = chr(65 + r) + string
            return string

        total_letter = col_letter(total_col)
        avail_letter = col_letter(avail_col)

        sheet.update(f"{total_letter}{match_index}", int(new_total))
        sheet.update(f"{avail_letter}{match_index}", int(new_available))

        st.success("✅ Sheet1 Updated Successfully")

    else:
        st.error("❌ Room not found")

    st.cache_data.clear()
    st.rerun()