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

required_cols = ["pg_id", "pg_name", "room_no", "floor", "sharing_type", "total_beds", "available_beds"]

for col in required_cols:
    if col not in df.columns:
        st.error(f"❌ Missing column: {col}")
        st.stop()

# -------- PG DROPDOWN --------
pg_unique = df.drop_duplicates(subset=["pg_id"])
pg_names = pg_unique["pg_name"].tolist()

selected_pg = st.selectbox("Select PG", pg_names)

pg_row = pg_unique[pg_unique["pg_name"] == selected_pg].iloc[0]
pg_id = pg_row["pg_id"]

# -------- ROOM DROPDOWN --------
pg_rooms = df[df["pg_id"] == pg_id]

room_options = pg_rooms["room_no"].astype(str).tolist()

selected_room = st.selectbox("Room Number", room_options)

room_data = pg_rooms[pg_rooms["room_no"].astype(str) == selected_room].iloc[0]

# -------- AUTO-FILL --------
floor = int(room_data["floor"])
st.write(f"Floor: {floor}")

# -------- SHARING FIX --------
sharing_text = str(room_data["sharing_type"])  # "3 Sharing"
sharing = int(sharing_text.split()[0])         # Extract 3

st.write(f"Sharing: {sharing} Sharing")

# -------- EDITABLE --------
total_beds = st.number_input(
    "Total Beds",
    min_value=1,
    max_value=sharing,
    value=min(int(room_data["total_beds"]), sharing)
)

available_beds = st.number_input(
    "Available Beds",
    min_value=0,
    max_value=total_beds,
    value=min(int(room_data["available_beds"]), total_beds)
)

# -------- SAVE --------
if st.button("Save Room"):

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
            result = ""
            while n > 0:
                n, r = divmod(n - 1, 26)
                result = chr(65 + r) + result
            return result

        total_letter = col_letter(total_col)
        avail_letter = col_letter(avail_col)

        # ✅ FIXED (2D list)
        sheet.update(f"{total_letter}{match_index}", [[int(total_beds)]])
        sheet.update(f"{avail_letter}{match_index}", [[int(available_beds)]])

        st.success("✅ Sheet1 Updated Successfully")

    else:
        st.error("❌ Room not found")

    st.cache_data.clear()
    st.rerun()