# EchoKids English: Listening & Speaking SRS Platform

A custom-designed, audio-first English learning and Spaced Repetition platform built specifically for parents teaching their kids (ages 7 and 11) with a laser focus on **Listening and Speaking**, tracking **Collocations, Sentences, and Words**.

---

## 🌟 Key Features

1. **Dual-Child Profile Switching**:
   - 🐰 **Kid 1 (Age 7)**: Playful, visual, gentle tempo audio, phonics & daily routines.
   - 🚀 **Kid 2 (Age 11)**: Modern, conversational chunks, natural tempo, speed recall.
   - 📊 **Parent Analytics**: Side-by-side comparison, total counts, retention rate.

2. **Categorical Tracking (The 3-Tier Lexical System)**:
   - 🔗 **Collocations**: High-frequency multi-word partnerships (e.g., *brush teeth, make a wish, burst into tears*).
   - 💬 **Sentences**: Full functional utterances (e.g., *Could you pass me the salt?*).
   - 📚 **Words**: Core vocabulary items with phonetic IPA and context.

3. **Audio-First Spaced Repetition (SRS)**:
   - **Sound Before Text**: Cards automatically play native pronunciation *first*, prompting the child to listen and repeat before reading text.
   - **Microphone & Speech Check**: Integrated Web Speech recognition transcribes and checks pronunciation in real-time.
   - **Voice Recording & Self-Comparison**: Records the child's voice so they can play back and compare directly with native audio.
   - **Kid-Friendly SM-2 Algorithm**: Positive reinforcement intervals (🌱 Practice Again, 👍 Good Job, 🌟 Super Easy) that prevent "Ease Hell".

4. **Zero-Friction Daily Input**:
   - Easily enter new words, collocations, or sentences discovered from cartoons, audiobooks, or daily conversations.
   - Instant native voice preview.
   - Automatic immediate queueing for Spaced Repetition.

---

## 🚀 Quick Start Guide

### 1. Launch with One Click
Double-click `run.bat` or run in terminal:
```bash
python app.py
```

### 2. Open in Your Browser
- On your PC: [http://localhost:8000](http://localhost:8000)
- On an iPad, iPhone, Android tablet, or laptop connected to the same Wi-Fi:
  ```
  http://192.168.1.3:8000
  ```

---

## 📁 Project Structure

```
G:\My Drive\CODE\8. English\
├── app.py                  # FastAPI server, SQLite database schema, REST APIs, and SRS engine
├── database.sqlite         # Persistent local database (Profiles, Items, SRS Cards, Review Logs)
├── run.bat                 # 1-click Windows launcher
├── README.md               # Quick start & technical reference
├── Pedagogical_Guide.md    # In-depth teaching handbook for listening & speaking (Ages 7 & 11)
├── task_plan.md            # Active phase tracking file
├── findings.md             # Research notes & pedagogical analysis
├── progress.md             # Session history log
└── static/
    ├── index.html          # Responsive single-page application with Tailwind CSS & Lucide icons
    └── app.js              # Web Speech API TTS, Speech Recognition, MediaRecorder, SRS card logic
```

---

## 📖 Pedagogical Handbook
Read [`Pedagogical_Guide.md`](file:///G:/My%20Drive/CODE/8.%20English/Pedagogical_Guide.md) for detailed guidelines on:
- Sourcing high-interest content for 7-year-olds (*Bluey, Peppa Pig, Super Simple Songs*) and 11-year-olds (*Mystery Doug, Crash Course Kids, BBC 6-Minute English*).
- The 15-minute daily family routine.
- The Echoing & Shadowing technique.
- Error recasting (painless grammar correction).
