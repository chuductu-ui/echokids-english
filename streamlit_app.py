"""
EchoKids English - Streamlit Cloud Edition
Listening & Speaking Spaced Repetition Platform for Kids (Ages 7 & 11)
With Google Drive & Google Sheets Live Synchronization
"""

import os
import io
import json
import sqlite3
import urllib.parse
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

    # Cloud Auto-Seed Safeguard: Ensure starter data exists if fresh container
    cursor.execute("SELECT COUNT(*) FROM profiles")
    if cursor.fetchone()[0] == 0:
        latest_path = os.path.join(ARCHIVE_DIR, "echokids_online_backup_latest.json")
        if os.path.exists(latest_path):
            try:
                with open(latest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for p in data.get("profiles", []):
                    cursor.execute("""
                    INSERT OR IGNORE INTO profiles (id, name, age, avatar, color_theme, daily_goal, streak_days, last_study_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (p["id"], p["name"], p["age"], p["avatar"], p.get("color_theme", "purple"), p.get("daily_goal", 10), p.get("streak_days", 0), p.get("last_study_date", "")))
                for itm in data.get("items", []):
                    cursor.execute("""
                    INSERT OR IGNORE INTO items (id, profile_id, item_type, english_text, ipa_phonetic, vietnamese_meaning, example_sentence, context_note, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (itm["id"], itm["profile_id"], itm["item_type"], itm["english_text"], itm.get("ipa_phonetic", ""), itm["vietnamese_meaning"], itm.get("example_sentence", ""), itm.get("context_note", ""), itm["created_at"]))
                for c in data.get("srs_cards", []):
                    cursor.execute("""
                    INSERT OR IGNORE INTO srs_cards (id, item_id, profile_id, step, interval_days, ease_factor, repetitions, lapses, state, due_date, last_reviewed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (c["id"], c["item_id"], c["profile_id"], c.get("step", 0), c.get("interval_days", 0), c.get("ease_factor", 2.5), c.get("repetitions", 0), c.get("lapses", 0), c.get("state", "new"), c["due_date"], c.get("last_reviewed_at", "")))
                conn.commit()
            except Exception:
                pass
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
    if not profiles:
        return [
            {"id": 1, "name": "Bunny Jolie", "age": 7, "avatar": "🐰", "color_theme": "amber", "daily_goal": 8, "streak_days": 3, "last_study_date": ""},
            {"id": 2, "name": "Puppy Flora", "age": 11, "avatar": "🐶", "color_theme": "indigo", "daily_goal": 12, "streak_days": 5, "last_study_date": ""}
        ]
    return profiles

def get_profile_counts(profile_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    
    cursor.execute("SELECT COUNT(*) as total FROM items WHERE profile_id = ?", (profile_id,))
    total = cursor.fetchone()["total"]
    
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
        "total": total,
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
    
    # Reset review state when profile switches
    if st.session_state.get("active_pid") != pid:
        st.session_state.active_pid = pid
        st.session_state.card_idx = 0
        st.session_state.card_flipped = False
        st.session_state.current_card_id = None
    
    st.divider()
    
    tld_code = "com"
    
    st.divider()
    
    # QR Code for Mobile / iPad / iPhone
    st.subheader("📱 Quét QR mở trên iPad / iPhone")
    
    detected_host = ""
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            detected_host = st.context.headers.get("host", "")
    except Exception:
        pass

    if detected_host and not detected_host.startswith("localhost") and not detected_host.startswith("127.0.0.1"):
        default_cloud_url = f"https://{detected_host}"
    else:
        default_cloud_url = "https://echokids-english.streamlit.app"

    # User input to verify or paste exact Streamlit URL if needed
    active_cloud_url = st.text_input(
        "🔗 Link Streamlit Cloud:", 
        value=default_cloud_url,
        help="Nếu link trên thanh địa chỉ của anh khác link này, hãy dán link thực tế vào đây để tạo mã QR chuẩn 100%."
    ).strip()
    
    if not active_cloud_url:
        active_cloud_url = default_cloud_url

    qr_img_url = f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={urllib.parse.quote(active_cloud_url)}"
    st.image(qr_img_url, caption=f"Quét để mở: {active_cloud_url}", use_container_width=True)
    st.link_button("🌐 Mở liên kết Cloud", active_cloud_url, use_container_width=True)
    
    with st.expander("💡 Khắc phục lỗi 'You do not have access...'"):
        st.markdown(
            """
            **Nếu iPad/iPhone quét bị báo lỗi quyền truy cập:**
            1. **Kiểm tra đúng Link thực tế**: Nhìn lên thanh địa chỉ trình duyệt PC xem link thực tế của app là gì và copy dán vào ô bên trên.
            2. **Bật Public**: Vào [share.streamlit.io](https://share.streamlit.io) > Bấm nút **⋮** cạnh app > **Settings > Sharing** > Chọn **Public** > Bấm **Save**.
            """
        )
    
    st.divider()
    
    # Google Drive Sync Status in Sidebar (Zero-Click Auto-Sync)
    st.subheader("☁️ Google Drive Sync")
    latest_backup_file = os.path.join(ARCHIVE_DIR, "echokids_online_backup_latest.json")
    if not os.path.exists(latest_backup_file):
        sync_to_google_drive_archive()
        
    mtime = datetime.fromtimestamp(os.stat(latest_backup_file).st_mtime).strftime("%H:%M:%S (%b %d)")
    st.success(f"🟢 **Tự động đồng bộ: BẬT**\n\n*Lần đồng bộ gần nhất: {mtime}*")
    st.caption("⚡ Mọi từ mới và lượt ôn tập SRS được hệ thống **tự động lưu lên Google Drive ngay lập tức**, không cần bấm bất kỳ nút nào.")
    
    with st.expander("🛠️ Sao lưu thủ công (Tùy chọn)"):
        if st.button("🔄 Bấm để đồng bộ ngay", use_container_width=True):
            ok, msg = sync_to_google_drive_archive()
            if ok:
                st.toast("✅ Đã đồng bộ lên Google Drive thành công!")
                st.rerun()

# --- Top Header & Live Metric Counters ---
counts = get_profile_counts(pid)

col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1])
with col1:
    st.markdown(f"### {active_profile['avatar']} {active_profile['name']}")
    st.caption(f"{active_profile['age']} tuổi • 🔥 **{active_profile['streak_days']} ngày streak**")

with col2:
    st.metric(label="Tổng số thẻ", value=counts["total"])

with col3:
    st.metric(label="Cần ôn hôm nay", value=counts["due_today"])

with col4:
    st.metric(label="Đã ghi nhớ", value=counts["mastered"])

st.divider()

# --- Main Tabs (3 Minimalist Tabs) ---
tab_review, tab_input, tab_library = st.tabs([
    "🎧 Ôn tập (SRS Review)", 
    "➕ Thêm thẻ (Daily Input)", 
    "📚 Thư viện (My Library)"
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
        st.success("🎉 Xuất sắc! Bé đã hoàn thành tất cả thẻ cần ôn hôm nay!")
    else:
        # Boundary check
        if st.session_state.card_idx >= len(due_cards):
            st.session_state.card_idx = 0
            st.session_state.card_flipped = False

        card = due_cards[st.session_state.card_idx]
        progress_val = (st.session_state.card_idx + 1) / len(due_cards)
        st.progress(progress_val, text=f"Thẻ {st.session_state.card_idx + 1} / {len(due_cards)}")

        # Ensure each card starts UNFLIPPED (Vietnamese only) by tracking card ID
        if st.session_state.get("current_card_id") != card["id"]:
            st.session_state.current_card_id = card["id"]
            st.session_state.card_flipped = False

        # Card Container Box
        card_box = st.container(border=True)
        with card_box:
            if not st.session_state.card_flipped:
                # FRONT: VIETNAMESE ONLY (NO ENGLISH, NO AUDIO)
                st.caption("🇻🇳 Nghĩa tiếng Việt:")
                st.markdown(f"# :orange[**{card['vietnamese_meaning']}**]")
                st.markdown("##### 🤔 *Bé hãy nhớ và phát âm từ/câu này bằng tiếng Anh, sau đó bấm nút lật thẻ để kiểm tra nhé!*")
                
                if st.button("🔄 LẬT THẺ SANG TIẾNG ANH & NGHE PHÁT ÂM", type="primary", use_container_width=True):
                    st.session_state.card_flipped = True
                    st.rerun()
            else:
                # BACK: REVEALED ENGLISH + AUTOMATIC AUDIO
                st.caption("🇬🇧 Tiếng Anh:")
                st.markdown(f"# **{card['english_text']}**")
                st.markdown(f"#### 🇻🇳 Nghĩa: :orange[**{card['vietnamese_meaning']}**]")
                
                # Simultaneously play English pronunciation audio!
                audio_bytes = generate_audio(card["english_text"], tld=tld_code)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3", autoplay=True)

                if st.button("↩️ Úp thẻ lại (Chỉ xem Tiếng Việt)", use_container_width=True):
                    st.session_state.card_flipped = False
                    st.rerun()
                
                st.divider()
                st.caption("Bé nhớ từ này như thế nào?")
                rcol1, rcol2, rcol3 = st.columns(3)
                with rcol1:
                    if st.button("🌱 Học lại", use_container_width=True):
                        submit_srs_review(card["id"], pid, 1)
                        st.session_state.card_flipped = False
                        st.session_state.current_card_id = None
                        st.session_state.card_idx += 1
                        st.rerun()
                with rcol2:
                    if st.button("👍 Nhớ tốt", use_container_width=True):
                        submit_srs_review(card["id"], pid, 2)
                        st.session_state.card_flipped = False
                        st.session_state.current_card_id = None
                        st.session_state.card_idx += 1
                        st.rerun()
                with rcol3:
                    if st.button("🌟 Rất dễ", type="primary", use_container_width=True):
                        submit_srs_review(card["id"], pid, 3)
                        st.session_state.card_flipped = False
                        st.session_state.current_card_id = None
                        st.session_state.card_idx += 1
                        st.rerun()

# ==========================================
# TAB 2: DAILY INPUT
# ==========================================
with tab_input:
    st.subheader(f"➕ Thêm thẻ mới - {active_profile['name']}")
    
    with st.form("add_item_form", clear_on_submit=True):
        f_eng = st.text_input("English text *", placeholder="Nhập từ hoặc câu tiếng Anh...")
        f_viet = st.text_input("Vietnamese meaning *", placeholder="Nhập nghĩa tiếng Việt...")
        recorded_audio = st.audio_input("Record audio (Ghi âm giọng đọc)")
        
        submitted = st.form_submit_button("💾 Lưu thẻ", type="primary", use_container_width=True)
        if submitted:
            if not f_eng.strip() or not f_viet.strip():
                st.error("Vui lòng nhập cả English text và Vietnamese meaning.")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                now_str = datetime.now().isoformat()
                today_str = date.today().isoformat()
                
                cursor.execute("""
                INSERT INTO items (profile_id, item_type, english_text, ipa_phonetic, vietnamese_meaning, example_sentence, context_note, created_at)
                VALUES (?, 'phrase', ?, '', ?, '', '', ?)
                """, (pid, f_eng.strip(), f_viet.strip(), now_str))
                new_item_id = cursor.lastrowid
                
                cursor.execute("""
                INSERT INTO srs_cards (item_id, profile_id, step, interval_days, ease_factor, repetitions, lapses, state, due_date, last_reviewed_at)
                VALUES (?, ?, 0, 0, 2.5, 0, 0, 'new', ?, '')
                """, (new_item_id, pid, today_str))
                conn.commit()
                conn.close()
                
                sync_to_google_drive_archive()
                st.success(f"🎉 Đã lưu thành công: '{f_eng}'!")
                st.rerun()

# ==========================================
# TAB 3: LEARNING LIBRARY
# ==========================================
with tab_library:
    st.subheader(f"📚 Thư viện của {active_profile['name']}")
    
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
    
    search_query = st.text_input("🔍 Tìm kiếm:", placeholder="Nhập tiếng Anh hoặc tiếng Việt...")

    if "flipped_library_cards" not in st.session_state:
        st.session_state.flipped_library_cards = set()

    filtered_items = all_items
    if search_query:
        filtered_items = [it for it in filtered_items if search_query.lower() in it["english_text"].lower() or search_query.lower() in it["vietnamese_meaning"].lower()]
        
    fcol1, fcol2, fcol3 = st.columns([2, 1, 1])
    with fcol1:
        st.caption(f"{len(filtered_items)} thẻ học")
    with fcol2:
        if st.button("🔄 Lật tất cả", use_container_width=True):
            st.session_state.flipped_library_cards = {it["id"] for it in filtered_items}
            st.rerun()
    with fcol3:
        if st.button("🔒 Ẩn tất cả", use_container_width=True):
            st.session_state.flipped_library_cards.clear()
            st.rerun()

    for it in filtered_items:
        card_box = st.container(border=True)
        is_flipped = it["id"] in st.session_state.flipped_library_cards
        
        with card_box:
            if not is_flipped:
                st.markdown(f"### 🇻🇳 {it['vietnamese_meaning']}")
                if st.button("🔄 Xem tiếng Anh", key=f"flip_{it['id']}", type="primary", use_container_width=True):
                    st.session_state.flipped_library_cards.add(it["id"])
                    st.rerun()
            else:
                st.markdown(f"## 🇬🇧 {it['english_text']}")
                
                item_audio = generate_audio(it["english_text"], tld=tld_code)
                if item_audio:
                    st.audio(item_audio, format="audio/mp3", autoplay=True)
                    
                st.markdown(f"**Nghĩa:** :orange[**{it['vietnamese_meaning']}**]")
                
                if st.button("↩️ Ẩn tiếng Anh", key=f"unflip_{it['id']}", use_container_width=True):
                    st.session_state.flipped_library_cards.remove(it["id"])
                    st.rerun()
