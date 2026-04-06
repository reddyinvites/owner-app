import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

st.set_page_config(page_title="PG System", layout="centered")

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

@st.cache_data(ttl=60)
def load_data():
    df = pd.DataFrame(
        get_client().open_by_key(PG_DATA_ID).worksheet("Sheet1").get_all_records()
    )
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

df = load_data()

# ---------------- LOGIN MOCK ----------------
# Replace with your real login
role = st.sidebar.selectbox("Login As", ["Admin", "Owner"])

# ---------------- MENU ----------------
if role == "Admin":
    menu = st.sidebar.radio("📂 Menu", ["Admin Dashboard", "Room Manager"])
else:
    menu = "Room Manager"

# ---------------- COMMON ----------------
if df.empty:
    st.error("❌ Sheet1 empty")
    st.stop()

pg_unique = df.drop_duplicates(subset=["pg_id"])
pg_names = pg_unique["pg_name"].tolist()

selected_pg = st.selectbox("Select PG", pg_names)
pg_id = pg_unique[pg_unique["pg_name"] == selected_pg].iloc[0]["pg_id"]

pg_rooms = df[df["pg_id"] == pg_id]

# =====================================================
# 🛠 ADMIN DASHBOARD (OLD SYSTEM KEPT)
# =====================================================
if menu == "Admin Dashboard":

    st.title("🛠 Admin Dashboard")

    st.subheader("🏠 PG Summary")

    summary = pg_rooms.groupby("pg_name")[["total_beds", "available_beds"]].sum().reset_index()

    st.dataframe(summary, use_container_width=True)

    st.subheader("📋 All Rooms")

    st.dataframe(pg_rooms, use_container_width=True)

# =====================================================
# 🏠 ROOM MANAGER (NEW SYSTEM)
# =====================================================
elif menu == "Room Manager":

    st.title("🏠 Room Manager")

    # -------- DASHBOARD --------
    st.subheader("📊 Dashboard")

    total_rooms = len(pg_rooms)
    total_beds = int(pg_rooms["total_beds"].sum())
    available = int(pg_rooms["available_beds"].sum())

    occupied = total_beds - available
    occupancy = int((occupied / total_beds) * 100) if total_beds else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("🏠 Rooms", total_rooms)
    c2.metric("🛏 Beds", total_beds)
    c3.metric("📉 Occupancy", f"{occupancy}%")

    st.progress(occupancy / 100)

    # -------- ROOMS --------
    st.subheader("🛏 Rooms")

    for _, row in pg_rooms.iterrows():

        total = int(row["total_beds"])
        avail = int(row["available_beds"])

        if avail == total:
            status = "🔴 FULL"
            color = "red"
        elif avail == 0:
            status = "⚪ Empty"
            color = "gray"
        else:
            status = "🟢 Available"
            color = "green"

        c1, c2, c3 = st.columns([2,2,2])
        c1.write(f"Room: {row['room_no']}")
        c2.write(f"Floor: {row['floor']}")
        c3.markdown(
            f"<span style='color:{color}'>{avail}/{total} Beds ({status})</span>",
            unsafe_allow_html=True
        )

    # -------- UPDATE ROOM --------
    st.subheader("➕ Update Room")

    room_options = pg_rooms["room_no"].astype(str).tolist()
    selected_room = st.selectbox("Room Number", room_options)

    room_data = pg_rooms[pg_rooms["room_no"].astype(str) == selected_room].iloc[0]

    floor = int(room_data["floor"])
    st.write(f"Floor: {floor}")

    sharing = int(str(room_data["sharing_type"]).split()[0])
    st.write(f"Sharing: {sharing} Sharing")

    is_full = int(room_data["available_beds"]) == int(room_data["total_beds"])

    total_input = st.number_input(
        "Total Beds",
        1,
        sharing,
        value=int(room_data["total_beds"]),
        disabled=is_full
    )

    avail_input = st.number_input(
        "Available Beds",
        0,
        total_input,
        value=int(room_data["available_beds"]),
        disabled=is_full
    )

    if is_full:
        st.error("🚫 Room FULL - Editing Disabled")

    if st.button("Save Room", disabled=is_full):

        sheet = get_client().open_by_key(PG_DATA_ID).worksheet("Sheet1")

        data = sheet.get_all_records()
        df_sheet = pd.DataFrame(data)
        df_sheet.columns = df_sheet.columns.str.strip().str.lower().str.replace(" ", "_")

        for i, r in df_sheet.iterrows():
            if str(r["pg_id"]) == str(pg_id) and str(r["room_no"]) == selected_room:

                headers = sheet.row_values(1)
                headers = [h.strip().lower().replace(" ", "_") for h in headers]

                total_col = headers.index("total_beds") + 1
                avail_col = headers.index("available_beds") + 1

                def col_letter(n):
                    s = ""
                    while n > 0:
                        n, r = divmod(n - 1, 26)
                        s = chr(65 + r) + s
                    return s

                sheet.update(f"{col_letter(total_col)}{i+2}", [[int(total_input)]])
                sheet.update(f"{col_letter(avail_col)}{i+2}", [[int(avail_input)]])

                st.success("✅ Updated Successfully")
                st.cache_data.clear()
                st.rerun()