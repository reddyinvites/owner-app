import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
PG_DATA_ID = "1y60dTYBKgkOi7J37jtGK4BkkmUoZF8yD4P5J3xA5q6Q"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

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

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=60)
def load_data():
    client = get_client()
    sheet = client.open_by_key(PG_DATA_ID)

    # Sheet1
    df = pd.DataFrame(sheet.worksheet("Sheet1").get_all_records())

    # Owners SAFE LOAD
    try:
        owners_ws = sheet.worksheet("Owners")
    except:
        owners_ws = sheet.add_worksheet(title="Owners", rows=1000, cols=4)
        owners_ws.append_row(["username","password","pg_id","pg_name"])

    owners = pd.DataFrame(owners_ws.get_all_records())

    # -------- CLEAN --------
    if not df.empty:
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    if not owners.empty:
        owners.columns = [str(c).strip().lower().replace(" ", "_") for c in owners.columns]

        # ensure required columns exist
        for col in ["username","password","pg_id","pg_name"]:
            if col not in owners.columns:
                owners[col] = ""

        owners["username"] = owners["username"].astype(str).str.strip().str.lower()
        owners["password"] = owners["password"].astype(str).str.strip()
        owners["pg_id"] = owners["pg_id"].astype(str).str.strip()
        owners["pg_name"] = owners["pg_name"].astype(str).str.strip()

    return df, owners

df, owners_df = load_data()

# ---------------- SESSION ----------------
if "login" not in st.session_state:
    st.session_state.login = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "username" not in st.session_state:
    st.session_state.username = ""

# ---------------- LOGIN ----------------
if not st.session_state.login:

    st.title("🔐 Login")

    role = st.selectbox("Login as", ["Admin", "Owner"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if role == "Admin":
            if username == ADMIN_USER and password == ADMIN_PASS:
                st.session_state.login = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("❌ Invalid Admin")

        else:
            if owners_df.empty:
                st.error("❌ Owners sheet empty")
                st.stop()

            if "username" not in owners_df.columns or "password" not in owners_df.columns:
                st.error(f"❌ Column issue: {owners_df.columns.tolist()}")
                st.stop()

            user = owners_df[
                (owners_df["username"] == username.strip().lower()) &
                (owners_df["password"] == password.strip())
            ]

            if not user.empty:
                st.session_state.login = True
                st.session_state.role = "owner"
                st.session_state.username = username.strip().lower()
                st.rerun()
            else:
                st.error("❌ Invalid Owner")

# =====================================================
# 🔐 AFTER LOGIN
# =====================================================
else:

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if df.empty:
        st.error("❌ Sheet empty")
        st.stop()

    pg_unique = df.drop_duplicates(subset=["pg_id"])
    pg_names = pg_unique["pg_name"].tolist()

    # OWNER → only their PG
    if st.session_state.role == "owner":
        owner_row = owners_df[
            owners_df["username"] == st.session_state.username
        ].iloc[0]

        selected_pg = owner_row["pg_name"]
        pg_id = owner_row["pg_id"]

        st.write(f"🏠 PG: {selected_pg}")

    else:
        selected_pg = st.selectbox("Select PG", pg_names)
        pg_row = pg_unique[pg_unique["pg_name"] == selected_pg].iloc[0]
        pg_id = pg_row["pg_id"]

    pg_rooms = df[df["pg_id"] == pg_id]

    # MENU
    if st.session_state.role == "admin":
        menu = st.sidebar.radio("📂 Menu", ["Admin Dashboard", "Room Manager"])
    else:
        menu = "Room Manager"

    # =====================================================
    # 🛠 ADMIN DASHBOARD
    # =====================================================
    if menu == "Admin Dashboard":

        st.title("🛠 Admin Dashboard")

        st.subheader("🏠 PG Summary")
        summary = pg_rooms.groupby("pg_name")[["total_beds","available_beds"]].sum().reset_index()
        st.dataframe(summary, use_container_width=True)

        st.subheader("📋 All Rooms")
        st.dataframe(pg_rooms, use_container_width=True)

        st.subheader("➕ Create Owner")

        selected_pg_owner = st.selectbox("Select PG", pg_names, key="owner_pg")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password")

        if st.button("Create Owner"):

            sheet_file = get_client().open_by_key(PG_DATA_ID)

            try:
                sheet = sheet_file.worksheet("Owners")
            except:
                sheet = sheet_file.add_worksheet(title="Owners", rows=1000, cols=4)
                sheet.append_row(["username","password","pg_id","pg_name"])

            pg_row = pg_unique[pg_unique["pg_name"] == selected_pg_owner].iloc[0]

            sheet.append_row([
                new_user.strip().lower(),
                new_pass.strip(),
                str(pg_row["pg_id"]),
                selected_pg_owner
            ])

            st.success("✅ Owner Created")

    # =====================================================
    # 🏠 ROOM MANAGER
    # =====================================================
    elif menu == "Room Manager":

        st.title("🏠 Room Manager")

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

        st.subheader("🛏 Rooms")

        for _, row in pg_rooms.iterrows():

            total = int(row["total_beds"])
            avail = int(row["available_beds"])

            if avail == 0:
                status = "🔴 FULL"
                color = "red"
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

        st.subheader("➕ Update Room")

        room_options = pg_rooms["room_no"].astype(str).tolist()
        selected_room = st.selectbox("Room Number", room_options)

        room_data = pg_rooms[pg_rooms["room_no"].astype(str) == selected_room].iloc[0]

        floor = int(room_data["floor"])
        st.write(f"Floor: {floor}")

        sharing = int(str(room_data["sharing_type"]).split()[0])
        st.write(f"Sharing: {sharing} Sharing")

        is_full = int(room_data["available_beds"]) == 0

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
            df_sheet.columns = [str(c).strip().lower().replace(" ", "_") for c in df_sheet.columns]

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