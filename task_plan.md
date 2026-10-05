# Task Plan: Kids English Listening & Speaking SRS Platform & Consultancy

## Goal
Design and architect a comprehensive English learning, monitoring, and Spaced Repetition System (SRS) platform tailored for two children (ages 7 and 11) with a core focus on **Listening and Speaking**, tracking **collocations, sentences, and words**, combined with actionable pedagogical consultancies and system blueprints.

---

## Status Overview
- **Current Phase**: Complete (All Phases Executed)
- **Overall Progress**: 100%
- **Active Plan**: Main Plan (Root)

---

## Phases

### Phase 1: Requirements & Pedagogical Analysis <!-- id: 0 -->
- [x] Analyze age-specific cognitive & language acquisition traits (7yo vs 11yo)
- [x] Formulate the Listening & Speaking framework (Lexical Approach, Comprehensible Input, Echo/Shadowing)
- [x] Define multi-tier tracking taxonomy: Words vs. Collocations vs. Full Sentences
- **Status**: complete

### Phase 2: Solution Architecture & Technology Options Evaluation <!-- id: 1 -->
- [x] Evaluate Option A: Tailored Anki Ecosystem (custom note types, AnkiWeb, plugins, mobile apps)
- [x] Evaluate Option B: Purpose-built Modern Web/PWA App (Next.js/React, local SQLite, Web Speech API, Edge TTS, FSRS/SM-2)
- [x] Evaluate Option C: Low-Code / Desktop Rapid Prototype (Python Streamlit / Gradio / Electron)
- [x] Trade-off analysis matrix (Usability for kids, Audio/Voice support, Parent metrics, Setup effort)
- **Status**: complete

### Phase 3: Platform Specification & Technical Architecture <!-- id: 2 -->
- [x] Data Model & Entity Relationship (Profiles, Items, Item Types, SRS State, Audio Records, Logs)
- [x] SRS Algorithm selection & implementation logic (SM-2 vs FSRS adapted for kids' retention)
- [x] Speech & Audio Pipeline (High-quality TTS synthesis, Kid Microphone Recording, Pronunciation assessment)
- [x] Dual-Child UX Design & Gamification Engine (Ages 7 vs 11 differentiated interfaces, streaks, badges)
- [x] Parent Monitoring Dashboard (Collocation/Word/Sentence counts, Mastery graphs, Due review alerts)
- **Status**: complete

### Phase 4: Pedagogical Consultancy & Daily Operating System <!-- id: 3 -->
- [x] 15-minute Daily Habit Protocol for 7yo (Sensory, gamified, picture-audio, physical response)
- [x] 25-minute Daily Habit Protocol for 11yo (Contextual, roleplay, collocations mastery, shadowing)
- [x] High-yield Content Ingestion pipeline (Cartoons, Readers, YouTube Kids, Everyday life dialogues)
- [x] Review & Feedback guidelines (Error correction without discouraging fluency)
- **Status**: complete

### Phase 5: Implementation Roadmap & Artifact Delivery <!-- id: 4 -->
- [x] Create comprehensive interactive blueprint & architecture documentation
- [x] Provide ready-to-run prototype/starter codebase plan (PWA / Next.js or Python app)
- [x] Deliver full consultation report to parent with clear next steps
- **Status**: complete

### Phase 6: 1-Click Launching & Online Cloud Archival (iPad / iPhone / Tablet Access) <!-- id: 5 -->
- [x] Build true 1-click Desktop launcher for PC (auto-starts background daemon and opens browser)
- [x] Configure Progressive Web App (PWA) manifest, service worker, and mobile touch icons for 1-tap iOS/iPadOS home screen install
- [x] Create cloud deployment bundle (`requirements.txt`, `Dockerfile`, `render.yaml`) for 24/7 free online hosting (Render / Hugging Face Spaces / Railway)
- [x] Implement cloud database & backup pipeline (auto-snapshot to Google Drive-synced `online_archive/` and cloud API)
- [x] Configure instant HTTPS tunnel script for zero-setup remote testing
- **Status**: complete

### Phase 7: Streamlit Cloud Deployment & Google Drive Synchronization <!-- id: 6 -->
- [x] Evaluate feasibility and architectural patterns (Google Drive API vs Google Sheets connection `st.connection('gsheets')`)
- [x] Build production-ready `streamlit_app.py` featuring Dual-Child Profiles, Categorical Tracking (Words, Collocations, Sentences), Audio-First SRS, and Google Drive sync
- [x] Integrate Audio/Speech pipeline for kids within Streamlit (TTS audio generation via `gTTS`, Web Speech API integration)
- [x] Configure `requirements.txt` and `run_streamlit.bat` for seamless local testing and Streamlit Community Cloud deployment
- [x] Provide end-to-end setup guide for deploying to `share.streamlit.io` with Google Drive integration
- **Status**: complete

### Phase 8: Automated Execution (Google Drive Sheet Creation, GitHub Push & Streamlit Deploy) <!-- id: 7 -->
- [x] Step 1: Create live Google Sheet in user's Google Drive via `google-workspace` MCP and seed initial cards (`EchoKids English - Learning Database`, ID: `1LU4SAghihRdM_ivhDizHLKi6vKPVlYL2ppHWNrUhJ_c`)
- [x] Step 2: Initialize Git repo, create `.gitignore`, and commit all codebase files
- [x] Step 3: Create GitHub repository `chuductu-ui/echokids-english` using `gh repo create` and push to GitHub
- [x] Step 4: Ensure `streamlit_app.py` is configured with Google Sheet ID and live sync
- [x] Step 5: Provide 1-click Streamlit Cloud deployment link and verify complete workflow
- **Status**: complete

### Phase 9: Library Vietnamese-First Flip Cards & Google Drive Folder Relocation <!-- id: 8 -->
- [x] Move Google Sheet to target Google Drive folder `1OfwAewoRPK-xGAH_O-UUQk577GK3XymP` via `google-workspace` MCP
- [x] Update `streamlit_app.py`: Design "My Library" cards to show Vietnamese ONLY by default, with an interactive "Flip Card" button that reveals the English version, audio player, example sentence, and IPA
- [x] Update `static/app.js`: Design "My Library" cards in FastAPI frontend to show Vietnamese ONLY by default with 1-click flip card toggle to English
- [x] Update documentation and README links with target Google Drive folder information
- [x] Commit all modifications to Git and push to GitHub repository `chuductu-ui/echokids-english`
- **Status**: complete

---

## Key Decisions & Log
| Decision | Rationale | Impact |
|:---|:---|:---|
| Focus on Lexical Approach (Collocations & Sentences) | Isolated words fail to build speaking fluency; chunking enables instantaneous recall | System data model must treat Collocation and Sentence as 1st-class citizens |
| Audio-First Card Design | Reading-only flashcards harm pronunciation & natural prosody | Every card must auto-play native audio and allow 1-tap voice recording |
| Age-differentiated UX (7yo vs 11yo) | 7yo cannot manage dense text or complex UI; 11yo gets bored by babyish interfaces | Profiles need switchable themes and interaction complexities |
| FSRS / Tuned SM-2 Algorithm | Standard Anki defaults are too punitive for children, leading to frustration | Soften penalty on failed cards; focus on confidence building |

---

## Errors & Blockers Log
| Issue | Attempt | Resolution |
|:---|:---|:---|
| None | - | - |
