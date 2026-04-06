import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

st.set_page_config(page_title="PG Room Manager", layout="centered")

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

# ---------------- LOAD ----------------
@st.cache_data(ttl=60)
def load_data():
    client = get_client()
    df = pd.DataFrame(
        client.open_by_key(PG_DATA_ID).worksheet("Sheet1").get_all_records()
    )

    if not df.empty:
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    return df

df = load_data()

# ---------------- UI ----------------
st.title("🏠 PG Room Manager")

if df.empty:
    st.error("❌ Sheet1 is empty")
    st.stop()

required_cols = ["pg_id","pg_name","room_no","floor","sharing_type","total_beds","available_beds"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"❌ Missing column: {col}")
        st.stop()

# -------- PG SELECT --------
pg_unique = df.drop_duplicates(subset=["pg_id"])
pg_names = pg_unique["pg_name"].tolist()

selected_pg = st.selectbox("Select PG", pg_names)

pg_row = pg_unique[pg_unique["pg_name"] == selected_pg].iloc[0]
pg_id = pg_row["pg_id"]

pg_rooms = df[df["pg_id"] == pg_id]

# ---------------- DASHBOARD ----------------
st.subheader("📊 Dashboard")

total_rooms = len(pg_rooms)
total_beds_sum = int(pg_rooms["total_beds"].sum())
available_beds_sum = int(pg_rooms["available_beds"].sum())

occupied = total_beds_sum - available_beds_sum
occupancy = int((occupied / total_beds_sum) * 100) if total_beds_sum else 0

c1, c2, c3 = st.columns(3)
c1.metric("🏠 Rooms", total_rooms)
c2.metric("🛏 Beds", total_beds_sum)
c3.metric("📉 Occupancy", f"{occupancy}%")

st.progress(occupancy / 100)

# ---------------- ROOM LIST ----------------
st.subheader("🛏 Rooms")

for _, row in pg_rooms.iterrows():
    total = int(row["total_beds"])
    available = int(row["available_beds"])

    if available == 0:
        status = "🔴 FULL"
        color = "red"
    else:
        status = "🟢 Available"
        color = "green"

    c1, c2, c3 = st.columns([2,2,2])
    c1.markdown(f"**Room: {row['room_no']}**")
    c2.write(f"Floor: {row['floor']}")
    c3.markdown(
        f"<span style='color:{color};'>{available}/{total} Beds ({status})</span>",
        unsafe_allow_html=True
    )

# ---------------- UPDATE ROOM ----------------
st.subheader("➕ Update Room")

room_options = pg_rooms["room_no"].astype(str).tolist()
selected_room = st.selectbox("Room Number", room_options)

room_data = pg_rooms[pg_rooms["room_no"].astype(str) == selected_room].iloc[0]

# Auto-fill
floor = int(room_data["floor"])
st.write(f"Floor: {floor}")

sharing_text = str(room_data["sharing_type"])
sharing = int(sharing_text.split()[0])

st.write(f"Sharing: {sharing} Sharing")

# Check FULL
is_full = int(room_data["available_beds"]) == 0

# Editable
total_beds = st.number_input(
    "Total Beds",
    1,
    sharing,
    value=int(room_data["total_beds"]),
    disabled=is_full
)

available_beds = st.number_input(
    "Available Beds",
    0,
    total_beds,
    value=int(room_data["available_beds"]),
    disabled=is_full
)

if is_full:
    st.error("🚫 Room is FULL - Editing Disabled")

# ---------------- SAVE ----------------
if st.button("Save Room", disabled=is_full):

    if available_beds > total_beds:
        st.error("❌ Available beds cannot exceed total beds")
        st.stop()

    sheet = get_client().open_by_key(PG_DATA_ID).worksheet("Sheet1")

    all_data = sheet.get_all_records()
    df_sheet = pd.DataFrame(all_data)
    df_sheet.columns = df_sheet.columns.str.strip().str.lower().str.replace(" ", "_")

    match_index = None
    for i, r in df_sheet.iterrows():
        if str(r["pg_id"]) == str(pg_id) and str(r["room_no"]) == str(selected_room):
            match_index = i + 2
            break

    if match_index:
        headers = sheet.row_values(1)
        headers = [h.strip().lower().replace(" ", "_") for h in headers]

        total_col = headers.index("total_beds") + 1
        avail_col = headers.index("available_beds") + 1

        def col_letter(n):
            res = ""
            while n > 0:
                n, r = divmod(n - 1, 26)
                res = chr(65 + r) + res
            return res

        sheet.update(f"{col_letter(total_col)}{match_index}", [[int(total_beds)]])
        sheet.update(f"{col_letter(avail_col)}{match_index}", [[int(available_beds)]])

        st.success("✅ Updated Successfully")

    else:
        st.error("❌ Room not found")

    st.cache_data.clear()
    st.rerun()