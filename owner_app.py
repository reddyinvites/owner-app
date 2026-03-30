import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

st.set_page_config(page_title="PG Management System", layout="wide")

st.title("🏠 PG Management System")

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp"], scope
)

client = gspread.authorize(creds)

SHEET_ID = "1GbSoVjomgzl52VD8KB2fK1wmQIIYxUlkI4ADgnYYvxw"

try:
    spreadsheet = client.open_by_key(SHEET_ID)

    # ✅ FIXED (no more 404)
    sheet = spreadsheet.worksheet("Sheet1")

    st.success("✅ Connected to Google Sheet")

except Exception as e:
    st.error("❌ Connection Error")
    st.write(e)
    st.stop()

# ---------------- LOAD DATA ----------------
@st.cache_data(ttl=30)
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

# ---------------- GENERATE PG ID ----------------
def generate_pg_id(df):
    if df.empty or "pg_id" not in df.columns:
        return "PG001"

    existing = df["pg_id"].dropna().astype(str)

    nums = []
    for x in existing:
        if x.startswith("PG"):
            try:
                nums.append(int(x.replace("PG","")))
            except:
                pass

    if not nums:
        return "PG001"

    return f"PG{max(nums)+1:03d}"

# ---------------- FORM ----------------
with st.form("pg_form"):

    st.subheader("➕ Add PG")

    name = st.text_input("PG Name")
    location = st.text_input("Location")
    owner_name = st.text_input("Owner Name")
    owner_number = st.text_input("Owner Number")

    food_type = st.selectbox("Food Type", ["Veg","Non-Veg","Mixed"])
    laundry = st.selectbox("Laundry", ["Yes","No"])

    metro_dist = st.number_input("Metro Distance", 0)
    bus_dist = st.number_input("Bus Distance", 0)
    rail_dist = st.number_input("Rail Distance", 0)

    clean = st.slider("Cleanliness", 1, 10)
    food_rating = st.slider("Food", 1, 10)
    safety = st.slider("Safety", 1, 10)
    value = st.slider("Value", 1, 10)
    crowd = st.slider("Crowd", 1, 10)

    notes = st.text_area("Notes")

    preview = st.form_submit_button("👁 Preview")
    save = st.form_submit_button("💾 Save")

# ---------------- PREVIEW ----------------
if preview:
    rating = round((clean + food_rating + safety + value + crowd)/5,1)

    st.subheader("🔍 Preview")
    st.json({
        "name": name,
        "location": location,
        "rating": rating
    })

    st.session_state.preview = True

# ---------------- SAVE ----------------
if save:

    if "preview" not in st.session_state:
        st.error("⚠️ Click Preview first")
        st.stop()

    pg_id = generate_pg_id(df)

    rating = round((clean + food_rating + safety + value + crowd)/5,1)

    new_row = [
        pg_id,
        name,
        location,
        owner_name,
        owner_number,
        food_type,
        laundry,
        metro_dist,
        bus_dist,
        rail_dist,
        clean,
        food_rating,
        safety,
        value,
        crowd,
        rating,
        notes,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]

    sheet.append_row(new_row)

    st.success(f"✅ Saved! PG ID: {pg_id}")

    # ✅ CLEAR FORM
    st.session_state.clear()
    st.rerun()

# ---------------- DISPLAY ----------------
st.subheader("📊 PG Table")

if df.empty:
    st.warning("No data found")
else:
    df.columns = df.columns.str.lower().str.strip()

    show_cols = [c for c in ["pg_id","pg_name","location","food_type","laundry","rating"] if c in df.columns]

    st.dataframe(df[show_cols], use_container_width=True)

# ---------------- ACTIONS ----------------
st.subheader("⚙️ Actions")

if not df.empty:

    selected = st.selectbox("Select PG", df.index)

    row = df.loc[selected]

    col1, col2 = st.columns(2)

    # DELETE
    if col1.button("🗑 Delete"):
        sheet.delete_rows(selected + 2)
        st.success("Deleted")
        st.rerun()

    # EDIT
    if col2.button("✏️ Edit"):
        st.session_state.edit_index = selected

# ---------------- EDIT FULL ----------------
if "edit_index" in st.session_state:

    i = st.session_state.edit_index
    row = df.loc[i]

    st.subheader("✏️ Edit PG (FULL)")

    new_name = st.text_input("PG Name", row.get("pg_name",""))
    new_location = st.text_input("Location", row.get("location",""))
    new_owner = st.text_input("Owner Name", row.get("owner_name",""))
    new_number = st.text_input("Owner Number", row.get("owner_number",""))

    new_food = st.selectbox("Food Type", ["Veg","Non-Veg","Mixed"])
    new_laundry = st.selectbox("Laundry", ["Yes","No"])

    new_clean = st.slider("Cleanliness", 1, 10, int(row.get("cleanliness",1)))
    new_food_rating = st.slider("Food", 1, 10, int(row.get("food_rating",1)))
    new_safety = st.slider("Safety", 1, 10, int(row.get("safety",1)))
    new_value = st.slider("Value", 1, 10, int(row.get("value",1)))
    new_crowd = st.slider("Crowd", 1, 10, int(row.get("crowd",1)))

    new_notes = st.text_area("Notes", row.get("notes",""))

    if st.button("💾 Update"):

        rating = round((new_clean + new_food_rating + new_safety + new_value + new_crowd)/5,1)

        updated_row = [
            row["pg_id"],
            new_name,
            new_location,
            new_owner,
            new_number,
            new_food,
            new_laundry,
            row.get("metro_dist",0),
            row.get("bus_dist",0),
            row.get("rail_dist",0),
            new_clean,
            new_food_rating,
            new_safety,
            new_value,
            new_crowd,
            rating,
            new_notes,
            row.get("timestamp","")
        ]

        sheet.update(f"A{i+2}:R{i+2}", [updated_row])

        st.success("Updated!")
        del st.session_state.edit_index
        st.rerun()

    if st.button("❌ Cancel"):
        del st.session_state.edit_index
        st.rerun()