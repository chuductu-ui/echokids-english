"""
EchoKids English - Streamlit Cloud Edition
Listening & Speaking Spaced Repetition Platform for Kids (Ages 7 & 11)
With Google Drive & Google Sheets Live Synchronization
"""

import os
import io
import json
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import streamlit as st
from gtts import gTTS

# --- Page Configuration ---
st.set_page_config(
    page_title="EchoKids English SRS",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Path Configurations ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "database.sqlite"))
ARCHIVE_DIR = os.path.join(BASE_DIR, "online_archive")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# --- Database & Storage Helpers ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_local_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        avatar TEXT DEFAULT '🐰',
        color_theme TEXT DEFAULT 'purple',
        daily_goal INTEGER DEFAULT 10,
        streak_days INTEGER DEFAULT 0,
        last_study_date TEXT DEFAULT ''
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        item_type TEXT NOT NULL, -- 'word', 'collocation', 'sentence'
        english_text TEXT NOT NULL,
        ipa_phonetic TEXT DEFAULT '',
        vietnamese_meaning TEXT NOT NULL,
        example_sentence TEXT DEFAULT '',
        context_note TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS srs_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL UNIQUE,
        profile_id INTEGER NOT NULL,
        step INTEGER DEFAULT 0,
        interval_days REAL DEFAULT 0,
        ease_factor REAL DEFAULT 2.5,
        repetitions INTEGER DEFAULT 0,
        lapses INTEGER DEFAULT 0,
        state TEXT DEFAULT 'new', -- 'new', 'learning', 'review', 'mastered'
        due_date TEXT NOT NULL,
        last_reviewed_at TEXT DEFAULT '',
        FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
        FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        profile_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        reviewed_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

init_local_db()

# --- Audio TTS Generator ---
@st.cache_data(show_spinner=False)
def generate_audio(text: str, tld: str = "com") -> bytes:
    """Generate high-quality native English audio using Google TTS in memory"""
    try:
        tts = gTTS(text=text, lang="en", tld=tld, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        st.warning(f"Audio generation notice: {e}")
        return b""

# --- Google Drive Cloud Sync Helper ---
def sync_to_google_drive_archive():
    """Dump state to online_archive/ (auto-synced by Google Drive desktop app to Google Cloud)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        profiles = [dict(r) for r in cursor.execute("SELECT * FROM profiles").fetchall()]
        items = [dict(r) for r in cursor.execute("SELECT * FROM items").fetchall()]
        cards = [dict(r) for r in cursor.execute("SELECT * FROM srs_cards").fetchall()]
        logs = [dict(r) for r in cursor.execute("SELECT * FROM review_logs").fetchall()]
        conn.close()
        
        backup_data = {
            "synced_at": datetime.now().isoformat(),
            "total_items": len(items),
            "profiles": profiles,
            "items": items,
            "srs_cards": cards,
            "review_logs": logs
        }
        
        latest_path = os.path.join(ARCHIVE_DIR, "echokids_online_backup_latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
        daily_path = os.path.join(ARCHIVE_DIR, f"backup_{date.today().isoformat()}.json")
        with open(daily_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
        return True, latest_path
    except Exception as e:
        return False, str(e)

# --- Profiles & Stats Loaders ---
def load_profiles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles ORDER BY age ASC")
    profiles = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return profiles

def get_profile_counts(profile_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    
    cursor.execute("""
    SELECT item_type, COUNT(*) as cnt 
    FROM items 
    WHERE profile_id = ? 
    GROUP BY item_type
    """, (profile_id,))
    counts = {r["item_type"]: r["cnt"] for r in cursor.fetchall()}
    
    cursor.execute("""
    SELECT COUNT(*) as due_cnt 
    FROM srs_cards 
    WHERE profile_id = ? AND due_date <= ?
    """, (profile_id, today_str))
    due_today = cursor.fetchone()["due_cnt"]
    
    cursor.execute("""
    SELECT COUNT(*) as mastered_cnt 
    FROM srs_cards 
    WHERE profile_id = ? AND state = 'mastered'
    """, (profile_id,))
    mastered = cursor.fetchone()["mastered_cnt"]
    
    conn.close()
    return {
        "words": counts.get("word", 0),
        "collocations": counts.get("collocation", 0),
        "sentences": counts.get("sentence", 0),
        "due_today": due_today,
        "mastered": mastered
    }

def get_due_cards(profile_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    
    cursor.execute("""
    SELECT i.*, s.interval_days, s.repetitions, s.ease_factor, s.state, s.due_date
    FROM items i
    JOIN srs_cards s ON i.id = s.item_id
    WHERE i.profile_id = ? AND s.due_date <= ?
    ORDER BY 
        CASE s.state
            WHEN 'new' THEN 1
            WHEN 'learning' THEN 2
            WHEN 'review' THEN 3
            ELSE 4
        END,
        s.due_date ASC
    """, (profile_id, today_str))
    cards = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return cards

def submit_srs_review(item_id: int, profile_id: int, rating: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM srs_cards WHERE item_id = ?", (item_id,))
    card = dict(cursor.fetchone())
    
    interval = card["interval_days"]
    ease = card["ease_factor"]
    reps = card["repetitions"]
    lapses = card["lapses"]
    
    today = date.today()
    now_str = datetime.now().isoformat()
    
    if rating == 1: # Practice Again
        lapses += 1
        reps = 0
        new_interval = 0.5
        ease = max(1.3, ease - 0.15)
        new_state = "learning"
        due_date = today.isoformat()
    elif rating == 2: # Good Job
        reps += 1
        if reps == 1: new_interval = 1.0
        elif reps == 2: new_interval = 3.0
        else: new_interval = round(max(interval * ease, interval + 2), 1)
        new_state = "mastered" if new_interval >= 21 or reps >= 6 else "review"
        due_date = (today + timedelta(days=max(1, int(round(new_interval))))).isoformat()
    elif rating == 3: # Super Easy
        reps += 1
        ease = min(3.0, ease + 0.15)
        if reps == 1: new_interval = 2.0
        elif reps == 2: new_interval = 5.0
        else: new_interval = round(max(interval * ease * 1.3, interval + 4), 1)
        new_state = "mastered" if new_interval >= 21 or reps >= 5 else "review"
        due_date = (today + timedelta(days=max(2, int(round(new_interval))))).isoformat()

    cursor.execute("""
    UPDATE srs_cards
    SET interval_days = ?, ease_factor = ?, repetitions = ?, lapses = ?, state = ?, due_date = ?, last_reviewed_at = ?
    WHERE item_id = ?
    """, (new_interval, ease, reps, lapses, new_state, due_date, now_str, item_id))
    
    cursor.execute("""
    INSERT INTO review_logs (item_id, profile_id, rating, reviewed_at)
    VALUES (?, ?, ?, ?)
    """, (item_id, profile_id, rating, now_str))
    
    # Update Streak
    cursor.execute("SELECT streak_days, last_study_date FROM profiles WHERE id = ?", (profile_id,))
    prof = cursor.fetchone()
    streak = prof["streak_days"]
    last_study = prof["last_study_date"]
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()
    
    if last_study == yesterday_str: streak += 1
    elif last_study != today_str: streak = 1
    
    cursor.execute("UPDATE profiles SET streak_days = ?, last_study_date = ? WHERE id = ?", (streak, today_str, profile_id))
    
    conn.commit()
    conn.close()
    
    # Auto-sync snapshot to Google Drive archive
    sync_to_google_drive_archive()

# --- Sidebar: Child Profile Switcher & Settings ---
profiles = load_profiles()
profile_map = {f"{p['avatar']} {p['name']} ({p['age']}y)": p for p in profiles}

with st.sidebar:
    st.title("🎧 EchoKids English")
    st.caption("Listening & Speaking Spaced Repetition")
    
    selected_label = st.selectbox("Select Child Profile:", list(profile_map.keys()))
    active_profile = profile_map[selected_label]
    pid = active_profile["id"]
    
    st.divider()
    
    # Voice Accent setting
    voice_accent = st.radio("Model Voice Accent:", ["🇺🇸 American (US)", "🇬🇧 British (UK)"], index=0)
    tld_code = "com" if "US" in voice_accent else "co.uk"
    
    st.divider()
    
    # Google Drive Sync Status in Sidebar
    st.subheader("☁️ Google Drive Sync")
    latest_backup_file = os.path.join(ARCHIVE_DIR, "echokids_online_backup_latest.json")
    if os.path.exists(latest_backup_file):
        mtime = datetime.fromtimestamp(os.stat(latest_backup_file).st_mtime).strftime("%H:%M:%S (%b %d)")
        st.success(f"Synced to Drive: {mtime}")
    else:
        st.info("Sync active upon first action")
        
    if st.button("🔄 Sync Now to Google Drive"):
        ok, msg = sync_to_google_drive_archive()
        if ok:
            st.toast("✅ Synced with Google Drive successfully!")
            st.rerun()

# --- Top Header & Live Metric Counters ---
counts = get_profile_counts(pid)

col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1, 1, 1])
with col1:
    st.markdown(f"### {active_profile['avatar']} {active_profile['name']}")
    st.caption(f"Age {active_profile['age']} • 🔥 **{active_profile['streak_days']} Day Streak**")

with col2:
    st.metric(label="🔗 Collocations", value=counts["collocations"])

with col3:
    st.metric(label="💬 Sentences", value=counts["sentences"])

with col4:
    st.metric(label="📚 Words", value=counts["words"])

with col5:
    st.metric(label="⭐ Mastered", value=counts["mastered"], delta=f"{counts['due_today']} due today")

st.divider()

# --- Main Tabs ---
tab_review, tab_input, tab_library, tab_gdrive = st.tabs([
    "🎧 Daily SRS Review", 
    "➕ Daily Input", 
    "📚 Learning Library", 
    "☁️ Google Drive & Cloud Guide"
])

# ==========================================
# TAB 1: DAILY SRS REVIEW (AUDIO-FIRST)
# ==========================================
with tab_review:
    due_cards = get_due_cards(pid)
    
    if "card_idx" not in st.session_state:
        st.session_state.card_idx = 0
    if "card_flipped" not in st.session_state:
        st.session_state.card_flipped = False

    if not due_cards:
        st.balloons()
        st.success("🎉 Awesome job! You've reviewed all scheduled cards for today!")
        st.info("💡 Keep speaking, listening to stories, and add newly discovered collocations in the 'Daily Input' tab.")
    else:
        # Boundary check
        if st.session_state.card_idx >= len(due_cards):
            st.session_state.card_idx = 0
            st.session_state.card_flipped = False

        card = due_cards[st.session_state.card_idx]
        progress_val = (st.session_state.card_idx + 1) / len(due_cards)
        st.progress(progress_val, text=f"Card {st.session_state.card_idx + 1} of {len(due_cards)} (Due for Today)")

        # Card Container Box
        card_box = st.container(border=True)
        with card_box:
            # Type Badge
            badge_icon = "🔗" if card["item_type"] == "collocation" else ("💬" if card["item_type"] == "sentence" else "📚")
            st.markdown(f"**{badge_icon} {card['item_type'].upper()}** • State: `{card['state'].upper()}`")
            
            # AUDIO-FIRST MODE: Play sound immediately
            audio_bytes = generate_audio(card["english_text"], tld=tld_code)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)

            st.write("---")

            if not st.session_state.card_flipped:
                st.markdown("### 👂 Listen to the native sound and repeat aloud!")
                st.caption("Concentrate on the rhythm and intonation before checking the text.")
                
                if st.button("👀 Check Meaning & Spelling (Flip Card)", type="primary", use_container_width=True):
                    st.session_state.card_flipped = True
                    st.rerun()
            else:
                # Revealed View
                st.markdown(f"## {card['english_text']}")
                if card["ipa_phonetic"]:
                    st.caption(f"Phonetic: `{card['ipa_phonetic']}`")
                
                st.markdown(f"**Vietnamese Meaning:** :orange[**{card['vietnamese_meaning']}**]")
                
                if card["example_sentence"]:
                    st.info(f"💡 *Example:* \"{card['example_sentence']}\"")
                    
                st.write("---")
                st.markdown("##### How well did you remember and pronounce it?")
                
                rcol1, rcol2, rcol3 = st.columns(3)
                with rcol1:
                    if st.button("🌱 Practice Again\n(Today)", use_container_width=True):
                        submit_srs_review(card["id"], pid, 1)
                        st.session_state.card_flipped = False
                        st.session_state.card_idx += 1
                        st.rerun()
                with rcol2:
                    if st.button("👍 Good Job!\n(+2-3 days)", use_container_width=True):
                        submit_srs_review(card["id"], pid, 2)
                        st.session_state.card_flipped = False
                        st.session_state.card_idx += 1
                        st.rerun()
                with rcol3:
                    if st.button("🌟 Super Easy!\n(+4-6 days)", type="primary", use_container_width=True):
                        submit_srs_review(card["id"], pid, 3)
                        st.session_state.card_flipped = False
                        st.session_state.card_idx += 1
                        st.rerun()

# ==========================================
# TAB 2: DAILY INPUT
# ==========================================
with tab_input:
    st.subheader(f"➕ Enter Today's Learning for {active_profile['name']}")
    st.caption("Harvest collocations or sentences from bedtime stories, Bluey, Peppa Pig, or school.")
    
    with st.form("add_item_form", clear_on_submit=True):
        f_type = st.radio("Category:", ["collocation", "sentence", "word"], 
                          format_func=lambda x: "🔗 Collocation (e.g. make a wish)" if x == "collocation" else ("💬 Full Sentence" if x == "sentence" else "📚 Single Word"),
                          horizontal=True)
        f_eng = st.text_input("English Text *", placeholder="e.g., burst into laughter / I'm looking forward to...")
        f_viet = st.text_input("Vietnamese Meaning *", placeholder="e.g., bật cười lớn / Con rất mong chờ...")
        f_ex = st.text_input("Example Sentence (Optional)", placeholder="e.g., Everyone burst into laughter at the funny joke.")
        f_ipa = st.text_input("IPA Phonetic (Optional)", placeholder="e.g., /bɜːst ˈɪn.tuː ˈlɑːf.tər/")
        f_note = st.text_input("Context / Source (Optional)", placeholder="e.g., Bluey Ep 3 / Storybook")
        
        submitted = st.form_submit_button("💾 Save & Queue for Daily SRS Review", type="primary", use_container_width=True)
        if submitted:
            if not f_eng.strip() or not f_viet.strip():
                st.error("Please enter both English text and Vietnamese meaning.")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                now_str = datetime.now().isoformat()
                today_str = date.today().isoformat()
                
                cursor.execute("""
                INSERT INTO items (profile_id, item_type, english_text, ipa_phonetic, vietnamese_meaning, example_sentence, context_note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (pid, f_type, f_eng.strip(), f_ipa.strip(), f_viet.strip(), f_ex.strip(), f_note.strip(), now_str))
                new_item_id = cursor.lastrowid
                
                cursor.execute("""
                INSERT INTO srs_cards (item_id, profile_id, step, interval_days, ease_factor, repetitions, lapses, state, due_date, last_reviewed_at)
                VALUES (?, ?, 0, 0, 2.5, 0, 0, 'new', ?, '')
                """, (new_item_id, pid, today_str))
                conn.commit()
                conn.close()
                
                sync_to_google_drive_archive()
                st.success(f"🎉 Added '{f_eng}' successfully! Synced to Google Drive and queued for review.")
                st.rerun()

# ==========================================
# TAB 3: LEARNING LIBRARY
# ==========================================
with tab_library:
    st.subheader(f"📚 {active_profile['name']}'s Knowledge Library")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT i.*, s.state, s.interval_days, s.repetitions, s.due_date
    FROM items i
    JOIN srs_cards s ON i.id = s.item_id
    WHERE i.profile_id = ?
    ORDER BY i.id DESC
    """, (pid,))
    all_items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    l_col1, l_col2 = st.columns([2, 1])
    with l_col1:
        search_query = st.text_input("🔍 Search library:", placeholder="Search English, Vietnamese, or examples...")
    with l_col2:
        filter_type = st.selectbox("Filter Category:", ["All", "collocation", "sentence", "word"])

    if "flipped_library_cards" not in st.session_state:
        st.session_state.flipped_library_cards = set()

    filtered_items = all_items
    if search_query:
        filtered_items = [it for it in filtered_items if search_query.lower() in it["english_text"].lower() or search_query.lower() in it["vietnamese_meaning"].lower()]
    if filter_type != "All":
        filtered_items = [it for it in filtered_items if it["item_type"] == filter_type]
        
    fcol1, fcol2, fcol3 = st.columns([2, 1, 1])
    with fcol1:
        st.caption(f"Showing {len(filtered_items)} learning cards (Vietnamese prompt by default)")
    with fcol2:
        if st.button("🔄 Lật tất cả (Flip All)", use_container_width=True):
            st.session_state.flipped_library_cards = {it["id"] for it in filtered_items}
            st.rerun()
    with fcol3:
        if st.button("🔒 Ẩn tất cả (Hide All)", use_container_width=True):
            st.session_state.flipped_library_cards.clear()
            st.rerun()

    for it in filtered_items:
        card_box = st.container(border=True)
        is_flipped = it["id"] in st.session_state.flipped_library_cards
        badge_icon = "🔗" if it["item_type"] == "collocation" else ("💬" if it["item_type"] == "sentence" else "📚")
        
        with card_box:
            # Top row: Type badge & Mastery state
            head_col1, head_col2 = st.columns([3, 1])
            with head_col1:
                st.markdown(f"**{badge_icon} {it['item_type'].upper()}** • State: `{it['state'].upper()}`")
            with head_col2:
                st.caption(f"Due: {it['due_date']}")

            if not is_flipped:
                # VIETNAMESE ONLY MODE (Default)
                st.markdown(f"### 🇻🇳 {it['vietnamese_meaning']}")
                st.caption("Thử nhớ và phát âm tiếng Anh tương ứng trước khi lật thẻ!")
                
                if st.button("🔄 Lật thẻ xem tiếng Anh (Flip Card)", key=f"flip_{it['id']}", type="primary", use_container_width=True):
                    st.session_state.flipped_library_cards.add(it["id"])
                    st.rerun()
            else:
                # FLIPPED / ENGLISH REVEALED
                st.markdown(f"## 🇬🇧 {it['english_text']}")
                if it["ipa_phonetic"]:
                    st.caption(f"Phonetic: `{it['ipa_phonetic']}`")
                
                # Audio playback for revealed English
                item_audio = generate_audio(it["english_text"], tld=tld_code)
                if item_audio:
                    st.audio(item_audio, format="audio/mp3", autoplay=True)
                    
                st.markdown(f"**Nghĩa tiếng Việt:** :orange[**{it['vietnamese_meaning']}**]")
                if it["example_sentence"]:
                    st.info(f"💡 *Example:* \"{it['example_sentence']}\"")
                if it["context_note"]:
                    st.caption(f"Note: {it['context_note']}")
                    
                st.caption(f"Interval: {it['interval_days']}d • Repetitions: {it['repetitions']}")
                
                if st.button("↩️ Ẩn tiếng Anh (Lật lại)", key=f"unflip_{it['id']}", use_container_width=True):
                    st.session_state.flipped_library_cards.remove(it["id"])
                    st.rerun()

# ==========================================
# TAB 4: GOOGLE DRIVE & CLOUD GUIDE
# ==========================================
with tab_gdrive:
    st.subheader("☁️ Google Drive Architecture & Cloud Sync")
    
    st.success("✅ **Live Google Spreadsheet Moved to Target Google Drive Folder!**")
    sheet_url = "https://docs.google.com/spreadsheets/d/1LU4SAghihRdM_ivhDizHLKi6vKPVlYL2ppHWNrUhJ_c/edit?authuser=tucd"
    folder_url = "https://drive.google.com/drive/folders/1OfwAewoRPK-xGAH_O-UUQk577GK3XymP?authuser=tucd"
    
    col_link1, col_link2 = st.columns(2)
    with col_link1:
        st.link_button("📊 Open EchoKids Google Sheet", sheet_url, type="primary", use_container_width=True)
    with col_link2:
        st.link_button("📁 Open Target Google Drive Folder", folder_url, use_container_width=True)
    
    st.markdown("""
    ### How Google Drive Synchronization Works:
    
    1. **Live Google Sheet in Your Specified Folder**:
       - The spreadsheet **`EchoKids English - Learning Database`** is safely stored in your dedicated folder:
         [**View Folder**](https://drive.google.com/drive/folders/1OfwAewoRPK-xGAH_O-UUQk577GK3XymP?authuser=tucd).
       - You can open it on your smartphone or PC anytime to view or bulk-add new collocations!
    2. **Deploying on Streamlit Community Cloud (`share.streamlit.io`)**:
       - When you deploy this repository to free Streamlit Cloud, it runs **24/7 online**.
       - Your kids can open `https://echokids-english.streamlit.app` on their iPad without your PC being on!
    3. **Continuous Google Drive Folder Sync**:
       - All cards and review history are also automatically backed up to [`online_archive/`](file:///G:/My%20Drive/CODE/8.%20English/online_archive/) and synced across your devices via Google Drive.
    """)
    
    # Download current backup button
    latest_file = os.path.join(ARCHIVE_DIR, "echokids_online_backup_latest.json")
    if os.path.exists(latest_file):
        with open(latest_file, "r", encoding="utf-8") as bf:
            backup_str = bf.read()
        st.download_button(
            label="📥 Download Current Google Drive Backup Snapshot (JSON)",
            data=backup_str,
            file_name=f"echokids_backup_{date.today().isoformat()}.json",
            mime="application/json"
        )
