import os
import streamlit as st
from supabase import create_client, Client

INPUT_FILE = "input_qids.txt"
DEFAULT_BLOCK_SIZE = 40

# ---------------- SUPABASE SETUP ----------------
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["https://lukcwwvchxjjjlnquvyw.supabase.co"]
    key = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx1a2N3d3ZjaHhqampsbnF1dnl3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk4MzA3MTYsImV4cCI6MjEwNTQwNjcxNn0.NzULUOYIBmbWrOzYa3_ceOJlSPUxkWJUPHRl05BPld0"]
    return create_client(url, key)

supabase = init_supabase()


def get_answered_qids_from_db() -> set:
    """Fetches all answered QIDs from Supabase."""
    try:
        # Fetching up to 50,000 records to bypass default PostgREST 1,000 limit
        response = supabase.table("answered_qids").select("qid").limit(50000).execute()
        return {row["qid"] for row in response.data}
    except Exception as e:
        st.error(f"Error fetching from Supabase: {e}")
        return set()


def mark_qids_as_answered_in_db(qids: list):
    """Inserts/upserts a list of answered QIDs into Supabase."""
    try:
        records = [{"qid": qid} for qid in qids]
        supabase.table("answered_qids").upsert(records).execute()
    except Exception as e:
        st.error(f"Error saving to Supabase: {e}")


# ---------------- FILE HELPERS ----------------
def parse_qids(content: str) -> list[int]:
    if not content:
        return []
    normalized = content.replace("\n", ",").replace(" ", ",").replace("\t", ",")
    return [int(x.strip()) for x in normalized.split(",") if x.strip().isdigit()]


def load_input_file(filepath: str) -> list[int]:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return parse_qids(f.read())
    return []


# ---------------- PAGE CONFIG & LOAD DATA ----------------
st.set_page_config(page_title="UWorld QID Tracker", page_icon="🎯", layout="centered")

st.title("🎯 UWorld QID Block Generator")
st.caption("Connected live to Supabase for persistent tracking.")

# Read input questions
raw_input = load_input_file(INPUT_FILE)
seen = set()
unique_input_qids = [x for x in raw_input if not (x in seen or seen.add(x))]

# Fetch answered from Supabase
answered_qids = get_answered_qids_from_db()
unanswered_qids = [qid for qid in unique_input_qids if qid not in answered_qids]

# ---------------- METRICS ----------------
col1, col2, col3 = st.columns(3)
col1.metric("Total in List", len(unique_input_qids))
col2.metric("Answered (DB)", len(answered_qids))
col3.metric("Remaining", len(unanswered_qids))

st.divider()

# ---------------- BLOCK DISPLAY ----------------
if not unique_input_qids:
    st.warning(f"⚠️ `{INPUT_FILE}` is empty or missing. Please add your question IDs.")
elif not unanswered_qids:
    st.success("🎉 You've answered all questions in your input list!")
else:
    current_block = unanswered_qids[:DEFAULT_BLOCK_SIZE]
    block_csv = ",".join(map(str, current_block))

    st.subheader(f"📦 Next Block ({len(current_block)} Questions)")
    st.info("Hover over the box below and click the **copy button** on the top right:")

    st.code(block_csv, language=None)

    if st.button(f"✅ Mark these {len(current_block)} as Answered in Supabase", type="primary", use_container_width=True):
        mark_qids_as_answered_in_db(current_block)
        st.success(f"Saved! {len(current_block)} questions pushed to Supabase.")
        st.rerun()

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Supabase Info")
    st.write(f"Connected to table: `answered_qids`")
    st.write(f"Total synced QIDs: **{len(answered_qids)}**")
