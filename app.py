"""
EchoKids English - Listening & Speaking Spaced Repetition Platform
Designed for Kids (Ages 7 & 11) to master English Words, Collocations, and Sentences
"""

import os
import sys
import socket
import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Database & Archive paths (supports local Google Drive and cloud environments like Render/HuggingFace)
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.sqlite"))
ARCHIVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "online_archive")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

app = FastAPI(
    title="EchoKids English SRS",
    description="Listening & Speaking Spaced Repetition Platform for Kids",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Profiles Table
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
    
    # 2. Items Table (Words, Collocations, Sentences)
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
    
    # 3. SRS Cards Table
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
    
    # 4. Review Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        profile_id INTEGER NOT NULL,
        rating INTEGER NOT NULL, -- 1: Again, 2: Good, 3: Super Easy
        reviewed_at TEXT NOT NULL,
        FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
        FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    
    # Check if default profiles exist
    cursor.execute("SELECT COUNT(*) FROM profiles")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO profiles (name, age, avatar, color_theme, daily_goal, streak_days, last_study_date)
        VALUES ('Bunny Jolie', 7, '🐰', 'amber', 8, 3, ?)
        """, (date.today().isoformat(),))
        kid1_id = cursor.lastrowid
        
        cursor.execute("""
        INSERT INTO profiles (name, age, avatar, color_theme, daily_goal, streak_days, last_study_date)
        VALUES ('Puppy Flora', 11, '🐶', 'indigo', 12, 5, ?)
        """, (date.today().isoformat(),))
        kid2_id = cursor.lastrowid
        conn.commit()
        
        # Do not auto-seed sample items so children start fresh
        # seed_starter_items(conn, kid1_id, kid2_id)
        
    conn.close()

def seed_starter_items(conn: sqlite3.Connection, kid1_id: int, kid2_id: int):
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    
    # Sample items for Kid 1 (Age 7) - Visual, sensory, daily routines, playful
    kid1_samples = [
        # Words
        ("word", "giggle", "/ˈɡɪɡ.əl/", "cười khúc khích", "The baby started to giggle.", "Sound of playful laughter"),
        ("word", "whisper", "/ˈwɪs.pər/", "thì thầm, nói nhỏ", "Can you whisper a secret to me?", "Speaking quietly"),
        ("word", "clumsy", "/ˈklʌm.zi/", "vụng về, lóng ngóng", "The little puppy is so clumsy and cute.", "Physical movement"),
        ("word", "curious", "/ˈkjʊə.ri.əs/", "tò mò, thích khám phá", "Cats are very curious animals.", "Desire to know"),
        # Collocations
        ("collocation", "brush teeth", "/brʌʃ tiːθ/", "đánh răng", "Remember to brush your teeth before bedtime.", "Night & morning routine"),
        ("collocation", "make a mess", "/meɪk ə mes/", "bày bừa, làm bừa bộn", "The puppies made a big mess in the living room.", "Common house action"),
        ("collocation", "tell a story", "/tel ə ˈstɔː.ri/", "kể chuyện", "Dad, will you tell a story tonight?", "Bedtime routine"),
        ("collocation", "catch a ball", "/kætʃ ə bɔːl/", "bắt bóng", "He can run fast and catch a ball.", "Outdoor sport"),
        ("collocation", "fall asleep", "/fɔːl əˈsliːp/", "chìm vào giấc ngủ", "I fall asleep with my teddy bear.", "Bedtime"),
        ("collocation", "tie shoes", "/taɪ ʃuːz/", "buộc dây giày", "I learned how to tie my shoes today!", "Milestone skill"),
        # Sentences
        ("sentence", "Could I have some water, please?", "", "Con có thể xin một cốc nước được không ạ?", "Could I have some water, please? I'm thirsty.", "Polite request"),
        ("sentence", "Look at the colorful butterfly!", "", "Nhìn chú bướm nhiều màu sắc kìa!", "Look at the colorful butterfly in the garden!", "Excited observation"),
        ("sentence", "I feel super happy today!", "", "Hôm nay con cảm thấy cực kỳ vui vẻ!", "I feel super happy today because we're going to the park.", "Expressing feeling"),
        ("sentence", "Can we play hide and seek?", "", "Chúng mình chơi trốn tìm được không?", "Can we play hide and seek together?", "Invitation to play")
    ]
    
    # Sample items for Kid 2 (Age 11) - Natural idioms, conversational chunks, expressive discourse
    kid2_samples = [
        # Words
        ("word", "reluctant", "/rɪˈlʌk.tənt/", "ngập ngừng, miễn cưỡng", "He was reluctant to admit his mistake.", "Hesitation"),
        ("word", "fascinating", "/ˈfæs.ɪ.neɪ.tɪŋ/", "cực kỳ thú vị, lôi cuốn", "Space exploration is a fascinating topic.", "Deep interest"),
        ("word", "perseverance", "/ˌpɜː.sɪˈvɪə.rəns/", "sự kiên trì, bền bỉ", "Success requires patience and perseverance.", "Character trait"),
        ("word", "spontaneous", "/spɒnˈteɪ.ni.əs/", "tự phát, ngẫu hứng", "We took a spontaneous trip to the beach.", "Unplanned action"),
        # Collocations
        ("collocation", "burst into tears", "/bɜːst ˈɪn.tuː tɪəz/", "bật khóc nức nở", "She burst into tears when she heard the touching story.", "Emotional release"),
        ("collocation", "make an excuse", "/meɪk ən ɪkˈskjuːs/", "kiếm cớ, viện lý do", "Don't make an excuse, just apologize sincerely.", "Behavior"),
        ("collocation", "keep a promise", "/kiːp ə ˈprɒm.ɪs/", "giữ lời hứa", "A trustworthy person always keeps a promise.", "Integrity"),
        ("collocation", "take for granted", "/teɪk fɔː ˈɡrɑːn.tɪd/", "coi là điều hiển nhiên", "Never take your friends and family for granted.", "Deep mindset"),
        ("collocation", "pay attention", "/peɪ əˈten.ʃən/", "chú ý, tập trung", "Please pay attention to the teacher's instructions.", "Classroom & life"),
        ("collocation", "have a blast", "/hæv ə blɑːst/", "có một khoảng thời gian cực vui", "We had a blast at the science museum!", "Conversational excitement"),
        ("collocation", "lose your temper", "/luːz jɔː ˈtem.pər/", "mất bình tĩnh, nổi nóng", "Take a deep breath before you lose your temper.", "Self-control"),
        # Sentences
        ("sentence", "I'm really looking forward to the weekend.", "", "Mình thực sự rất mong chờ đến cuối tuần.", "I'm really looking forward to the weekend camping trip.", "Anticipation"),
        ("sentence", "It never crossed my mind that she was joking.", "", "Mình chưa từng nghĩ là bạn ấy đang đùa.", "It never crossed my mind that she was joking with me.", "Surprise / reflection"),
        ("sentence", "Could you explain how this works in more detail?", "", "Bạn/Thầy có thể giải thích chi tiết hơn cách này hoạt động không ạ?", "Could you explain how this works in more detail, please?", "Academic curiosity"),
        ("sentence", "Don't jump to conclusions before checking the facts.", "", "Đừng vội kết luận trước khi kiểm tra sự thật.", "Don't jump to conclusions before checking the facts carefully.", "Critical thinking")
    ]
    
    # Insert Kid 1 items
    for idx, (itype, eng, ipa, viet, ex, note) in enumerate(kid1_samples):
        cursor.execute("""
        INSERT INTO items (profile_id, item_type, english_text, ipa_phonetic, vietnamese_meaning, example_sentence, context_note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (kid1_id, itype, eng, ipa, viet, ex, note, today_str))
        item_id = cursor.lastrowid
        # Distribute due dates (some today, some tomorrow, some already learned)
        is_due = (idx % 3 == 0 or idx % 4 == 0)
        due_d = today_str if is_due else (date.today() + timedelta(days=(idx % 5) + 1)).isoformat()
        state = "review" if idx > 4 else "learning"
        rep = 2 if state == "review" else 0
        cursor.execute("""
        INSERT INTO srs_cards (item_id, profile_id, step, interval_days, ease_factor, repetitions, lapses, state, due_date, last_reviewed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, kid1_id, 0, 1.0, 2.5, rep, 0, state, due_d, yesterday_str if rep > 0 else ""))
        
    # Insert Kid 2 items
    for idx, (itype, eng, ipa, viet, ex, note) in enumerate(kid2_samples):
        cursor.execute("""
        INSERT INTO items (profile_id, item_type, english_text, ipa_phonetic, vietnamese_meaning, example_sentence, context_note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (kid2_id, itype, eng, ipa, viet, ex, note, today_str))
        item_id = cursor.lastrowid
        is_due = (idx % 2 == 0)
        due_d = today_str if is_due else (date.today() + timedelta(days=(idx % 4) + 1)).isoformat()
        state = "review" if idx > 5 else "learning"
        rep = 3 if state == "review" else 1
        cursor.execute("""
        INSERT INTO srs_cards (item_id, profile_id, step, interval_days, ease_factor, repetitions, lapses, state, due_date, last_reviewed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, kid2_id, 0, 2.0, 2.5, rep, 0, state, due_d, yesterday_str if rep > 0 else ""))
        
    conn.commit()

# --- Pydantic Models ---
class ProfileCreate(BaseModel):
    name: str
    age: int
    avatar: Optional[str] = "🐰"
    color_theme: Optional[str] = "purple"
    daily_goal: Optional[int] = 10

class ItemCreate(BaseModel):
    profile_id: int
    item_type: Optional[str] = "phrase"
    english_text: str
    ipa_phonetic: Optional[str] = ""
    vietnamese_meaning: str
    example_sentence: Optional[str] = ""
    context_note: Optional[str] = ""

class ItemUpdate(BaseModel):
    item_type: Optional[str] = None
    english_text: Optional[str] = None
    ipa_phonetic: Optional[str] = None
    vietnamese_meaning: Optional[str] = None
    example_sentence: Optional[str] = None
    context_note: Optional[str] = None

class ReviewSubmission(BaseModel):
    item_id: int
    profile_id: int
    rating: int = Field(..., ge=1, le=3, description="1: Again (Need practice), 2: Good, 3: Super Easy")

# Initialize DB on startup
init_db()

def archive_backup_snapshot():
    """Automatically dump full database state to online_archive/ (synced by Google Drive to the cloud)"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles")
        profiles = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM items")
        items = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM srs_cards")
        cards = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM review_logs")
        logs = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        data = {
            "snapshot_timestamp": datetime.now().isoformat(),
            "total_items": len(items),
            "profiles": profiles,
            "items": items,
            "srs_cards": cards,
            "review_logs": logs
        }
        latest_file = os.path.join(ARCHIVE_DIR, "echokids_online_backup_latest.json")
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        daily_file = os.path.join(ARCHIVE_DIR, f"backup_{date.today().isoformat()}.json")
        with open(daily_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Archive warning: {e}")

# Initial snapshot on startup
archive_backup_snapshot()

# --- API Endpoints ---

@app.get("/api/archive/status")
def get_archive_status():
    latest_file = os.path.join(ARCHIVE_DIR, "echokids_online_backup_latest.json")
    if os.path.exists(latest_file):
        stat = os.stat(latest_file)
        return {
            "status": "online_synced",
            "last_archived": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "archive_dir": ARCHIVE_DIR,
            "file_size_bytes": stat.st_size
        }
    return {"status": "pending"}

@app.get("/api/archive/download")
def download_archive():
    latest_file = os.path.join(ARCHIVE_DIR, "echokids_online_backup_latest.json")
    if os.path.exists(latest_file):
        return FileResponse(latest_file, media_type="application/json", filename="echokids_cloud_backup.json")
    raise HTTPException(status_code=404, detail="No archive found")

@app.get("/api/profiles")
def list_profiles():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles ORDER BY age ASC")
    profiles = [dict(row) for row in cursor.fetchall()]
    
    # Attach quick counts to each profile
    today_str = date.today().isoformat()
    for p in profiles:
        pid = p["id"]
        # Count words, collocations, sentences
        cursor.execute("""
        SELECT item_type, COUNT(*) as cnt 
        FROM items 
        WHERE profile_id = ? 
        GROUP BY item_type
        """, (pid,))
        type_counts = {row["item_type"]: row["cnt"] for row in cursor.fetchall()}
        p["count_words"] = type_counts.get("word", 0)
        p["count_collocations"] = type_counts.get("collocation", 0)
        p["count_sentences"] = type_counts.get("sentence", 0)
        p["total_items"] = sum(type_counts.values())
        
        # Count due today
        cursor.execute("""
        SELECT COUNT(*) as due_cnt 
        FROM srs_cards 
        WHERE profile_id = ? AND due_date <= ?
        """, (pid, today_str))
        p["due_today"] = cursor.fetchone()["due_cnt"]
        
        # Count mastered
        cursor.execute("""
        SELECT COUNT(*) as mastered_cnt 
        FROM srs_cards 
        WHERE profile_id = ? AND state = 'mastered'
        """, (pid,))
        p["mastered_items"] = cursor.fetchone()["mastered_cnt"]
        
    conn.close()
    return profiles

@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = dict(row)
    
    # Detailed category breakdown
    cursor.execute("""
    SELECT i.item_type, s.state, COUNT(*) as cnt
    FROM items i
    JOIN srs_cards s ON i.id = s.item_id
    WHERE i.profile_id = ?
    GROUP BY i.item_type, s.state
    """, (profile_id,))
    
    breakdown = {
        "word": {"new": 0, "learning": 0, "review": 0, "mastered": 0, "total": 0},
        "collocation": {"new": 0, "learning": 0, "review": 0, "mastered": 0, "total": 0},
        "sentence": {"new": 0, "learning": 0, "review": 0, "mastered": 0, "total": 0}
    }
    
    for r in cursor.fetchall():
        itype = r["item_type"]
        state = r["state"]
        cnt = r["cnt"]
        if itype in breakdown:
            breakdown[itype][state] = cnt
            breakdown[itype]["total"] += cnt
            
    profile["breakdown"] = breakdown
    
    # Total reviews completed today
    today_str = date.today().isoformat()
    cursor.execute("""
    SELECT COUNT(*) as reviewed_today
    FROM review_logs
    WHERE profile_id = ? AND reviewed_at LIKE ?
    """, (profile_id, f"{today_str}%"))
    profile["reviewed_today"] = cursor.fetchone()["reviewed_today"]
    
    conn.close()
    return profile

@app.post("/api/items")
def add_item(item: ItemCreate):
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify profile exists
    cursor.execute("SELECT id FROM profiles WHERE id = ?", (item.profile_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")
        
    now_str = datetime.now().isoformat()
    today_str = date.today().isoformat()
    
    # Insert Item
    cursor.execute("""
    INSERT INTO items (profile_id, item_type, english_text, ipa_phonetic, vietnamese_meaning, example_sentence, context_note, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item.profile_id,
        item.item_type.lower(),
        item.english_text.strip(),
        item.ipa_phonetic.strip() if item.ipa_phonetic else "",
        item.vietnamese_meaning.strip(),
        item.example_sentence.strip() if item.example_sentence else "",
        item.context_note.strip() if item.context_note else "",
        now_str
    ))
    item_id = cursor.lastrowid
    
    # Automatically deploy SRS card for this item (Due today for initial imprint!)
    cursor.execute("""
    INSERT INTO srs_cards (item_id, profile_id, step, interval_days, ease_factor, repetitions, lapses, state, due_date, last_reviewed_at)
    VALUES (?, ?, 0, 0, 2.5, 0, 0, 'new', ?, '')
    """, (item_id, item.profile_id, today_str))
    
    conn.commit()
    conn.close()
    
    # Automatically snapshot archive to online_archive (synced by Google Drive)
    archive_backup_snapshot()
    
    return {"status": "success", "item_id": item_id, "message": f"Added {item.item_type} successfully and queued for SRS review!"}

@app.get("/api/items")
def list_items(
    profile_id: Optional[int] = Query(None),
    item_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
    SELECT i.*, s.state, s.interval_days, s.repetitions, s.due_date, s.ease_factor
    FROM items i
    JOIN srs_cards s ON i.id = s.item_id
    WHERE 1=1
    """
    params = []
    
    if profile_id:
        query += " AND i.profile_id = ?"
        params.append(profile_id)
    if item_type:
        query += " AND i.item_type = ?"
        params.append(item_type)
    if state:
        query += " AND s.state = ?"
        params.append(state)
    if search:
        query += " AND (i.english_text LIKE ? OR i.vietnamese_meaning LIKE ? OR i.example_sentence LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
        
    query += " ORDER BY i.id DESC"
    cursor.execute(query, params)
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

@app.delete("/api/items/{item_id}")
def delete_item(item_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM srs_cards WHERE item_id = ?", (item_id,))
    cursor.execute("DELETE FROM review_logs WHERE item_id = ?", (item_id,))
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    archive_backup_snapshot()
    return {"status": "success", "message": "Item deleted"}

@app.get("/api/srs/due")
def get_due_items(profile_id: int, limit: int = 30):
    conn = get_db()
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    
    cursor.execute("""
    SELECT i.*, s.id as card_id, s.state, s.interval_days, s.repetitions, s.due_date, s.ease_factor, s.lapses
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
    LIMIT ?
    """, (profile_id, today_str, limit))
    
    due_items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return due_items

@app.post("/api/srs/review")
def review_item(rev: ReviewSubmission):
    """
    Execute kid-friendly Spaced Repetition (SM-2 tuned for children)
    Rating 1: Again (Need practice) - gentle reminder, short interval
    Rating 2: Good - solid recall, moderate interval expansion
    Rating 3: Super Easy - confident pronunciation/recall, rapid interval expansion
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM srs_cards WHERE item_id = ?", (rev.item_id,))
    card = cursor.fetchone()
    if not card:
        conn.close()
        raise HTTPException(status_code=404, detail="SRS Card not found")
        
    card = dict(card)
    interval = card["interval_days"]
    ease = card["ease_factor"]
    reps = card["repetitions"]
    lapses = card["lapses"]
    
    now = datetime.now()
    today = date.today()
    
    if rev.rating == 1: # Practice Again
        lapses += 1
        reps = 0
        new_interval = 0.5 # Review later today / tomorrow
        ease = max(1.3, ease - 0.15)
        new_state = "learning"
        due_date = today.isoformat() # Keep active in today's session
    elif rev.rating == 2: # Good Job
        reps += 1
        if reps == 1:
            new_interval = 1.0
        elif reps == 2:
            new_interval = 3.0
        else:
            new_interval = round(max(interval * ease, interval + 2), 1)
            
        new_state = "mastered" if new_interval >= 21 or reps >= 6 else "review"
        due_date = (today + timedelta(days=max(1, int(round(new_interval))))).isoformat()
    elif rev.rating == 3: # Super Easy
        reps += 1
        ease = min(3.0, ease + 0.15)
        if reps == 1:
            new_interval = 2.0
        elif reps == 2:
            new_interval = 5.0
        else:
            new_interval = round(max(interval * ease * 1.3, interval + 4), 1)
            
        new_state = "mastered" if new_interval >= 21 or reps >= 5 else "review"
        due_date = (today + timedelta(days=max(2, int(round(new_interval))))).isoformat()
        
    # Update card
    cursor.execute("""
    UPDATE srs_cards
    SET interval_days = ?, ease_factor = ?, repetitions = ?, lapses = ?, state = ?, due_date = ?, last_reviewed_at = ?
    WHERE item_id = ?
    """, (new_interval, ease, reps, lapses, new_state, due_date, now.isoformat(), rev.item_id))
    
    # Log review
    cursor.execute("""
    INSERT INTO review_logs (item_id, profile_id, rating, reviewed_at)
    VALUES (?, ?, ?, ?)
    """, (rev.item_id, rev.profile_id, rev.rating, now.isoformat()))
    
    # Update study streak
    cursor.execute("SELECT streak_days, last_study_date FROM profiles WHERE id = ?", (rev.profile_id,))
    prof = cursor.fetchone()
    streak = prof["streak_days"]
    last_study = prof["last_study_date"]
    
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()
    
    if last_study == yesterday_str:
        streak += 1
    elif last_study != today_str:
        streak = 1
        
    cursor.execute("UPDATE profiles SET streak_days = ?, last_study_date = ? WHERE id = ?", (streak, today_str, rev.profile_id))
    
    conn.commit()
    conn.close()
    
    archive_backup_snapshot()
    
    return {
        "status": "success",
        "new_state": new_state,
        "new_interval": new_interval,
        "due_date": due_date,
        "streak_days": streak
    }

@app.get("/api/stats/dashboard")
def get_dashboard_stats():
    """
    Comprehensive aggregated dashboard for parent monitoring
    """
    conn = get_db()
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    
    # Overall summary
    cursor.execute("""
    SELECT 
        COUNT(DISTINCT i.id) as total_items,
        SUM(CASE WHEN i.item_type = 'word' THEN 1 ELSE 0 END) as total_words,
        SUM(CASE WHEN i.item_type = 'collocation' THEN 1 ELSE 0 END) as total_collocations,
        SUM(CASE WHEN i.item_type = 'sentence' THEN 1 ELSE 0 END) as total_sentences,
        SUM(CASE WHEN s.state = 'mastered' THEN 1 ELSE 0 END) as total_mastered,
        SUM(CASE WHEN s.due_date <= ? THEN 1 ELSE 0 END) as total_due_today
    FROM items i
    JOIN srs_cards s ON i.id = s.item_id
    """, (today_str,))
    overview = dict(cursor.fetchone())
    
    # Child by child breakdown
    cursor.execute("SELECT id, name, age, avatar, color_theme, streak_days FROM profiles ORDER BY age ASC")
    profiles = [dict(r) for r in cursor.fetchall()]
    
    kids_stats = []
    for p in profiles:
        pid = p["id"]
        cursor.execute("""
        SELECT 
            i.item_type,
            COUNT(*) as total,
            SUM(CASE WHEN s.state = 'mastered' THEN 1 ELSE 0 END) as mastered,
            SUM(CASE WHEN s.state = 'learning' THEN 1 ELSE 0 END) as learning,
            SUM(CASE WHEN s.state = 'review' THEN 1 ELSE 0 END) as reviewing,
            SUM(CASE WHEN s.state = 'new' THEN 1 ELSE 0 END) as new_count
        FROM items i
        JOIN srs_cards s ON i.id = s.item_id
        WHERE i.profile_id = ?
        GROUP BY i.item_type
        """, (pid,))
        
        type_data = {}
        for row in cursor.fetchall():
            type_data[row["item_type"]] = dict(row)
            
        cursor.execute("""
        SELECT COUNT(*) as due_cnt
        FROM srs_cards
        WHERE profile_id = ? AND due_date <= ?
        """, (pid, today_str))
        due_today = cursor.fetchone()["due_cnt"]
        
        kids_stats.append({
            "profile": p,
            "due_today": due_today,
            "words": type_data.get("word", {"total": 0, "mastered": 0, "learning": 0, "reviewing": 0, "new_count": 0}),
            "collocations": type_data.get("collocation", {"total": 0, "mastered": 0, "learning": 0, "reviewing": 0, "new_count": 0}),
            "sentences": type_data.get("sentence", {"total": 0, "mastered": 0, "learning": 0, "reviewing": 0, "new_count": 0})
        })
        
    # Past 7 days review activity log
    seven_days_ago = (date.today() - timedelta(days=6)).isoformat()
    cursor.execute("""
    SELECT SUBSTR(reviewed_at, 1, 10) as review_date, COUNT(*) as count
    FROM review_logs
    WHERE reviewed_at >= ?
    GROUP BY review_date
    ORDER BY review_date ASC
    """, (seven_days_ago,))
    activity_chart = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "overview": overview,
        "kids": kids_stats,
        "recent_activity": activity_chart
    }

@app.post("/api/seed")
def reseed_data():
    """Reset and re-seed sample items for both kids"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM review_logs")
    cursor.execute("DELETE FROM srs_cards")
    cursor.execute("DELETE FROM items")
    cursor.execute("SELECT id FROM profiles ORDER BY age ASC")
    rows = cursor.fetchall()
    if len(rows) >= 2:
        kid1_id = rows[0]["id"]
        kid2_id = rows[1]["id"]
        seed_starter_items(conn, kid1_id, kid2_id)
    conn.close()
    return {"status": "success", "message": "Database successfully reseeded with sample collocations, words, and sentences."}

@app.get("/api/export")
def export_data():
    """Export complete dataset as JSON backup"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles")
    profiles = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM items")
    items = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM srs_cards")
    cards = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {
        "exported_at": datetime.now().isoformat(),
        "profiles": profiles,
        "items": items,
        "srs_cards": cards
    }

# Serve static frontend
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    import uvicorn
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
            
    local_ip = get_local_ip()
    print("\n" + "=" * 62)
    print("  EchoKids English: Listening & Speaking SRS Platform")
    print("=" * 62)
    print(f"  [1] On this PC, open:")
    print(f"      http://localhost:8000")
    print(f"  [2] On iPad / iPhone / Tablet on the same Wi-Fi, open:")
    print(f"      http://{local_ip}:8000")
    print("=" * 62 + "\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
