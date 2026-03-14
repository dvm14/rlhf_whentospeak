import streamlit as st
import json
import csv
import os
import random
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from contextlib import contextmanager

# ── Config ────────────────────────────────────────────────────────────────────
SCENARIOS_FILE = "scenarios.json"
DATABASE_URL   = st.secrets["DATABASE_URL"]

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VoiceIQ — Preference Lab",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background-color: #0c0c0f; color: #e8e6e3; }
.stApp { background-color: #0c0c0f; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1400px; }

.hero { text-align: center; padding: 2.5rem 0 1.5rem; border-bottom: 1px solid #1e1e24; margin-bottom: 2rem; }
.hero-title { font-family: 'Syne', sans-serif; font-size: 2.4rem; font-weight: 800; letter-spacing: -0.02em; color: #f0ede8; margin: 0; }
.hero-title span { color: #c8f04a; }
.hero-sub { font-size: 0.95rem; color: #6b6b7a; margin-top: 0.5rem; font-weight: 300; letter-spacing: 0.02em; }

.progress-wrap { background: #1a1a22; border-radius: 4px; height: 4px; margin: 0 0 0.4rem; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #c8f04a, #7fffb2); border-radius: 4px; transition: width 0.5s ease; }
.progress-label { font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #4a4a58; text-align: right; margin-bottom: 1.6rem; letter-spacing: 0.06em; }

.context-card { background: #13131a; border: 1px solid #1e1e2a; border-left: 3px solid #c8f04a; border-radius: 10px; padding: 1.2rem 1.5rem; margin-bottom: 2rem; font-size: 0.92rem; line-height: 1.65; color: #b8b6b0; }
.context-label { font-family: 'DM Mono', monospace; font-size: 0.68rem; letter-spacing: 0.1em; color: #c8f04a; text-transform: uppercase; margin-bottom: 0.5rem; }

.conv-card { background: #111118; border: 1px solid #1c1c26; border-radius: 12px; padding: 1.4rem; height: 100%; }
.conv-header { font-family: 'Syne', sans-serif; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #4a4a58; margin-bottom: 1.2rem; padding-bottom: 0.7rem; border-bottom: 1px solid #1a1a22; }

.turn { margin-bottom: 0.85rem; }
.turn-speaker { font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.06em; margin-bottom: 0.25rem; font-weight: 500; }
.turn-human .turn-speaker { color: #6b9fff; }
.turn-va .turn-speaker { color: #c8f04a; }
.turn-silent .turn-speaker { color: #3a3a48; }
.turn-text { font-size: 0.9rem; line-height: 1.6; color: #d0cec9; padding-left: 0.75rem; border-left: 2px solid #1e1e2a; }
.turn-va .turn-text { color: #e8ffc8; border-left-color: #c8f04a40; background: #c8f04a08; border-radius: 0 6px 6px 0; padding: 0.4rem 0.75rem; }
.turn-silent .turn-text { color: #3a3a48; font-style: italic; font-size: 0.82rem; }

.stButton > button { font-family: 'Syne', sans-serif !important; font-weight: 700 !important; letter-spacing: 0.04em !important; border-radius: 8px !important; transition: all 0.2s !important; border: 1px solid #2a2a38 !important; }
.stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 4px 20px rgba(200,240,74,0.12) !important; }

.metric-row { display: flex; gap: 1rem; margin: 2rem 0 1rem; justify-content: center; flex-wrap: wrap; }
.metric-chip { background: #13131a; border: 1px solid #1e1e24; border-radius: 8px; padding: 0.6rem 1.2rem; text-align: center; min-width: 90px; }
.metric-val { font-family: 'Syne', sans-serif; font-size: 1.4rem; font-weight: 800; color: #c8f04a; }
.metric-lbl { font-family: 'DM Mono', monospace; font-size: 0.65rem; letter-spacing: 0.08em; color: #4a4a58; text-transform: uppercase; }

.toast { background: #1a2a0a; border: 1px solid #c8f04a40; border-radius: 8px; padding: 0.8rem 1.2rem; color: #c8f04a; font-size: 0.88rem; text-align: center; margin-top: 1rem; }
.toast-skip { background: #1a1a22; border-color: #3a3a48; color: #6b6b7a; }
.all-done { text-align: center; padding: 3rem; }
.all-done-title { font-family: 'Syne', sans-serif; font-size: 1.8rem; font-weight: 800; color: #c8f04a; }

.stDownloadButton > button { background: #13131a !important; border: 1px solid #2a2a38 !important; color: #e8e6e3 !important; font-family: 'DM Mono', monospace !important; font-size: 0.78rem !important; letter-spacing: 0.04em !important; }
.stDownloadButton > button:hover { border-color: #c8f04a !important; color: #c8f04a !important; }
</style>
""", unsafe_allow_html=True)


# ── Database ──────────────────────────────────────────────────────────────────
@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    id           SERIAL PRIMARY KEY,
                    timestamp    TEXT NOT NULL,
                    scenario_id  TEXT NOT NULL,
                    labeler      TEXT,
                    prompt       TEXT,
                    chosen       TEXT,
                    rejected     TEXT,
                    skipped      INTEGER DEFAULT 0,
                    meta_json    TEXT
                )
            """)


def get_labeled_ids() -> set:
    """Scenario IDs with at least one non-skipped label globally."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT scenario_id FROM preferences WHERE skipped = 0")
            rows = cur.fetchall()
    return {r["scenario_id"] for r in rows}


def get_labeled_ids_by(labeler: str) -> set:
    """All scenario IDs this labeler has acted on (including skips)."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT scenario_id FROM preferences WHERE labeler = %s",
                (labeler,)
            )
            rows = cur.fetchall()
    return {r["scenario_id"] for r in rows}


def save_record(record: dict):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO preferences
                    (timestamp, scenario_id, labeler, prompt, chosen, rejected, skipped, meta_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                record["timestamp"],
                record["scenario_id"],
                record.get("labeler", ""),
                record["prompt"],
                record.get("chosen", ""),
                record.get("rejected", ""),
                1 if record.get("skipped") else 0,
                json.dumps(record.get("metadata", {})),
            ))


def export_jsonl() -> str:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM preferences ORDER BY id")
            rows = cur.fetchall()
    lines = [json.dumps({
        "timestamp":   r["timestamp"],
        "scenario_id": r["scenario_id"],
        "labeler":     r["labeler"],
        "prompt":      r["prompt"],
        "chosen":      r["chosen"],
        "rejected":    r["rejected"],
        "skipped":     bool(r["skipped"]),
        "metadata":    json.loads(r["meta_json"] or "{}"),
    }) for r in rows]
    return "\n".join(lines)


def export_csv() -> str:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM preferences WHERE skipped = 0 ORDER BY id")
            rows = cur.fetchall()
    if not rows:
        return ""
    import io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "timestamp", "scenario_id", "labeler", "prompt", "chosen", "rejected"
    ])
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r[k] for k in ["timestamp", "scenario_id", "labeler", "prompt", "chosen", "rejected"]})
    return buf.getvalue()


# ── Scenario helpers ──────────────────────────────────────────────────────────
@st.cache_data
def load_scenarios():
    if not os.path.exists(SCENARIOS_FILE):
        st.error(f"`{SCENARIOS_FILE}` not found — make sure it's in the same folder.")
        st.stop()
    with open(SCENARIOS_FILE, encoding="utf-8") as f:
        return json.load(f)


def format_conversation(turns: list) -> str:
    html = ""
    for turn in turns:
        speaker, text = turn["speaker"], turn["text"]
        is_va     = speaker == "Voice Assistant"
        is_silent = is_va and text is None
        css       = "turn-silent" if is_silent else ("turn-va" if is_va else "turn-human")
        display   = "(stays silent)" if is_silent else text
        html += f'<div class="turn {css}"><div class="turn-speaker">{speaker}</div><div class="turn-text">{display}</div></div>'
    return html


def serialize_conversation(turns: list) -> str:
    return "\n".join(
        f"{t['speaker']}: {'(silent)' if t['text'] is None else t['text']}"
        for t in turns
    )


# ── Init ──────────────────────────────────────────────────────────────────────
init_db()
scenarios    = load_scenarios()
all_ids      = [s["id"] for s in scenarios]
scenario_map = {s["id"]: s for s in scenarios}

# ── Labeler login ─────────────────────────────────────────────────────────────
if "labeler" not in st.session_state:
    st.session_state.labeler = None

if not st.session_state.labeler:
    st.markdown("""
    <div class="hero">
        <div class="hero-title">🎙️ Voice<span>IQ</span> Preference Lab</div>
        <div class="hero-sub">Help train voice assistants to know when to speak — and when to listen</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### Who are you?")
    st.caption("Enter your name or any identifier. This lets the app track which scenarios you've already seen so you never repeat one.")
    name_input = st.text_input("Your name / ID", placeholder="e.g. diya, labeler_03…")
    if st.button("Start Labeling →", type="primary") and name_input.strip():
        st.session_state.labeler = name_input.strip()
        st.rerun()
    st.stop()

labeler = st.session_state.labeler

# ── Build queue for this user ─────────────────────────────────────────────────
# Freshly compute which IDs this user hasn't touched yet
labeled_globally = get_labeled_ids()
labeled_by_me    = get_labeled_ids_by(labeler)

# Priority 1: no one has labeled yet  →  most valuable
# Priority 2: others labeled, I haven't  →  useful for inter-rater reliability
unseen_by_anyone = [i for i in all_ids if i not in labeled_globally and i not in labeled_by_me]
seen_by_others   = [i for i in all_ids if i in labeled_globally     and i not in labeled_by_me]

if "queue" not in st.session_state:
    random.shuffle(unseen_by_anyone)
    random.shuffle(seen_by_others)
    st.session_state.queue       = unseen_by_anyone + seen_by_others
    st.session_state.current_idx = 0
    st.session_state.saved       = False

# All done?
if st.session_state.current_idx >= len(st.session_state.queue):
    st.markdown("""
    <div class="hero"><div class="hero-title">🎙️ Voice<span>IQ</span> Preference Lab</div></div>
    <div class="all-done">
        <div class="all-done-title">🎉 All done!</div>
        <p style="color:#6b6b7a;margin-top:0.5rem">You've labeled every available scenario. Check back when new ones are added.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

current_id = st.session_state.queue[st.session_state.current_idx]
scenario   = scenario_map[current_id]

# Global progress
total_done = len(labeled_globally)
total      = len(all_ids)
pct        = int(total_done / total * 100) if total else 0

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
    <div class="hero-title">🎙️ Voice<span>IQ</span> Preference Lab</div>
    <div class="hero-sub">Logged in as <strong style="color:#c8f04a">{labeler}</strong> &nbsp;·&nbsp; Help train voice assistants to know when to speak — and when to listen</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="progress-wrap"><div class="progress-fill" style="width:{pct}%"></div></div>
<div class="progress-label">{total_done} / {total} SCENARIOS LABELED GLOBALLY</div>
""", unsafe_allow_html=True)

# ── Context ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="context-card">
    <div class="context-label">📍 Scenario Context</div>
    {scenario["context"]}
</div>
""", unsafe_allow_html=True)

# ── Normalize: speaking option always left, silent always right ───────────────
def has_va_speech(turns: list) -> bool:
    return any(t["speaker"] == "Voice Assistant" and t["text"] for t in turns)

opt_a_speaks = has_va_speech(scenario["option_a"])
# If option_a is the speaking one, left=a/right=b; otherwise swap
left_turns  = scenario["option_a"] if opt_a_speaks else scenario["option_b"]
right_turns = scenario["option_b"] if opt_a_speaks else scenario["option_a"]

# ── Conversations ─────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2, gap="medium")
with col_a:
    st.markdown(f'<div class="conv-card"><div class="conv-header">🗣️ Assistant Speaks</div>{format_conversation(left_turns)}</div>', unsafe_allow_html=True)
with col_b:
    st.markdown(f'<div class="conv-card"><div class="conv-header">🔇 Assistant Silent</div>{format_conversation(right_turns)}</div>', unsafe_allow_html=True)

# ── Buttons ───────────────────────────────────────────────────────────────────
st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
btn1, btn2, btn3 = st.columns([3, 3, 1])
with btn1:
    choose_speak = st.button("👈  Prefer Assistant Speaks", use_container_width=True, disabled=st.session_state.saved)
with btn2:
    choose_silent = st.button("Prefer Assistant Silent  👉", use_container_width=True, disabled=st.session_state.saved)
with btn3:
    skip = st.button("⏭ Skip", use_container_width=True, disabled=st.session_state.saved)


def make_record(chosen_turns, rejected_turns, skipped=False):
    return {
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "scenario_id": scenario["id"],
        "labeler":     labeler,
        "prompt":      scenario["context"],
        "chosen":      serialize_conversation(chosen_turns) if chosen_turns else "",
        "rejected":    serialize_conversation(rejected_turns) if rejected_turns else "",
        "skipped":     skipped,
        "metadata": {
            "option_a_has_va_speech": opt_a_speaks,
            "option_b_has_va_speech": not opt_a_speaks,
        },
    }


if choose_speak and not st.session_state.saved:
    save_record(make_record(left_turns, right_turns))
    st.session_state.saved = True
    st.markdown('<div class="toast">✓ Saved — Assistant Speaks preferred</div>', unsafe_allow_html=True)

if choose_silent and not st.session_state.saved:
    save_record(make_record(right_turns, left_turns))
    st.session_state.saved = True
    st.markdown('<div class="toast">✓ Saved — Assistant Silent preferred</div>', unsafe_allow_html=True)

if skip and not st.session_state.saved:
    save_record(make_record(None, None, skipped=True))
    st.session_state.saved = True
    st.markdown('<div class="toast toast-skip">⏭ Skipped</div>', unsafe_allow_html=True)

# ── Next ──────────────────────────────────────────────────────────────────────
if st.session_state.saved:
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    if st.button("Next Scenario →", type="primary"):
        st.session_state.current_idx += 1
        st.session_state.saved = False
        st.rerun()

# ── Stats & export ────────────────────────────────────────────────────────────
st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
st.markdown("---")

with get_db() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM preferences WHERE skipped=0")
        total_labels = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM preferences WHERE labeler=%s AND skipped=0", (labeler,))
        my_labels = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(DISTINCT labeler) AS n FROM preferences")
        num_labelers = cur.fetchone()["n"]

st.markdown(f"""
<div class="metric-row">
    <div class="metric-chip"><div class="metric-val">{total_labels}</div><div class="metric-lbl">Total Labels</div></div>
    <div class="metric-chip"><div class="metric-val">{my_labels}</div><div class="metric-lbl">My Labels</div></div>
    <div class="metric-chip"><div class="metric-val">{num_labelers}</div><div class="metric-lbl">Labelers</div></div>
    <div class="metric-chip"><div class="metric-val">{total_done}/{total}</div><div class="metric-lbl">Coverage</div></div>
</div>
""", unsafe_allow_html=True)

dl1, dl2 = st.columns(2)
with dl1:
    jsonl_data = export_jsonl()
    if jsonl_data:
        st.download_button("⬇ Download JSONL (all)", jsonl_data.encode(), file_name="preference_data.jsonl", mime="application/jsonl", use_container_width=True)
with dl2:
    csv_data = export_csv()
    if csv_data:
        st.download_button("⬇ Download CSV (labeled only)", csv_data.encode(), file_name="preference_data.csv", mime="text/csv", use_container_width=True)
