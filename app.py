import streamlit as st
from supabase import create_client, Client

BLOCK_SIZE = 40

# ---------------- SUPABASE CLIENT ----------------
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()


# ---------------- HELPER FUNCTIONS ----------------
def parse_qids(content: str) -> list[int]:
    """Parses text with commas, spaces, or newlines into a list of integers."""
    if not content:
        return []
    normalized = content.replace("\n", ",").replace(" ", ",").replace("\t", ",")
    return [int(x.strip()) for x in normalized.split(",") if x.strip().isdigit()]


def add_qids_to_db(qids: list[int]):
    """Adds new questions to Supabase, ignoring already added ones."""
    # Deduplicate while preserving order
    seen = set()
    unique_qids = [q for q in qids if not (q in seen or seen.add(q))]
    
    records = [{"qid": q, "is_answered": False} for q in unique_qids]
    
    # Insert in batches of 500 to avoid payload limits
    CHUNK_SIZE = 500
    for i in range(0, len(records), CHUNK_SIZE):
        chunk = records[i : i + CHUNK_SIZE]
        supabase.table("questions").upsert(
            chunk, on_conflict="qid", ignore_duplicates=True
        ).execute()


def get_next_block(limit: int = 40) -> list[int]:
    """Fetches the next batch of unanswered questions in order of insertion."""
    res = (
        supabase.table("questions")
        .select("qid")
        .eq("is_answered", False)
        .order("id", desc=False)
        .limit(limit)
        .execute()
    )
    return [row["qid"] for row in res.data]


def mark_block_as_answered(qids: list[int]):
    """Marks the specified QIDs as answered in Supabase."""
    supabase.table("questions").update({"is_answered": True}).in_("qid", qids).execute()


def get_stats():
    """Fetches total, answered, and remaining counts."""
    total = supabase.table("questions").select("*", count="exact", head=True).execute().count or 0
    answered = (
        supabase.table("questions")
        .select("*", count="exact", head=True)
        .eq("is_answered", True)
        .execute()
        .count or 0
    )
    remaining = total - answered
    return total, answered, remaining


# ---------------- STREAMLIT PAGE SETUP ----------------
st.set_page_config(page_title="UWorld QID Bank", page_icon="🎯", layout="centered")
st.title("🎯 UWorld Question Bank")

# ---------------- METRICS ----------------
total_count, answered_count, remaining_count = get_stats()

col1, col2, col3 = st.columns(3)
col1.metric("Total in Bank", total_count)
col2.metric("Answered", answered_count)
col3.metric("Remaining", remaining_count)

st.divider()

# ---------------- NEXT BLOCK SECTION ----------------
next_block = get_next_block(BLOCK_SIZE)

if not next_block:
    if total_count == 0:
        st.info("👈 Your question bank is empty! Paste your QIDs in the sidebar to get started.")
    else:
        st.success("🎉 You've answered all questions in your bank!")
else:
    block_csv = ",".join(map(str, next_block))
    st.subheader(f"📦 Next Block ({len(next_block)} Questions)")
    st.caption("Click the copy button on the top right of the box below:")
    
    st.code(block_csv, language=None)

    if st.button(f"✅ Mark these {len(next_block)} as Answered", type="primary", use_container_width=True):
        mark_block_as_answered(next_block)
        st.success("Saved! Loading next block...")
        st.rerun()

# ---------------- SIDEBAR: INPUT DIRECTLY ON WEB ----------------
with st.sidebar:
    st.header("📥 Add Questions")
    st.caption("Paste QIDs directly here (separated by commas, spaces, or newlines):")
    
    raw_pasted = st.text_area("Paste QIDs:", height=200, placeholder="e.g. 1042, 1045, 1092, 1093...")
    
    if st.button("➕ Add to Supabase", use_container_width=True):
        parsed = parse_qids(raw_pasted)
        if parsed:
            with st.spinner("Saving questions to Supabase..."):
                add_qids_to_db(parsed)
            st.success(f"Added {len(parsed)} questions!")
            st.rerun()
        else:
            st.warning("Please paste valid numbers.")
