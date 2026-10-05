// EchoKids English - Client Application Logic

let state = {
  profiles: [],
  activeProfileId: null,
  activeProfile: null,
  dueItems: [],
  currentCardIndex: 0,
  isFlipped: false,
  isAudioFirst: true,
  selectedAccent: 'en-US',
  activeTab: 'review',
  allLibraryItems: [],
  isRecording: false,
  recognition: null,
  mediaRecorder: null,
  audioChunks: [],
  userAudioUrl: null
};

// Web Audio API Sound Effects
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
function playChime(type) {
  try {
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    
    if (type === 'success') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(523.25, audioCtx.currentTime); // C5
      osc.frequency.setValueAtTime(659.25, audioCtx.currentTime + 0.1); // E5
      osc.frequency.setValueAtTime(783.99, audioCtx.currentTime + 0.2); // G5
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.45);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.45);
    } else if (type === 'flip') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(440, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.15);
    } else if (type === 'star') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
      osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.1); // A5
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.5);
    }
  } catch (e) {
    console.log("Audio FX error", e);
  }
}

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
  await loadProfiles();
  setupSpeechRecognition();
  lucide.createIcons();

  // Register PWA Service Worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').then(() => {
      console.log('EchoKids PWA Service Worker Registered');
    }).catch(err => {
      console.log('Service Worker registration skipped or failed:', err);
    });
  }
});

// Load Profiles & Set Initial Child
async function loadProfiles() {
  try {
    const res = await fetch("/api/profiles");
    state.profiles = await res.json();
    if (state.profiles.length > 0 && !state.activeProfileId) {
      state.activeProfileId = state.profiles[0].id;
    }
    renderProfileSelector();
    await updateActiveProfileData();
  } catch (err) {
    console.error("Failed to load profiles:", err);
  }
}

// Render Profile Switcher in Header
function renderProfileSelector() {
  const container = document.getElementById("profileSelector");
  if (!container) return;
  
  container.innerHTML = state.profiles.map(p => {
    const isActive = p.id === state.activeProfileId;
    return `
      <button onclick="selectProfile(${p.id})" 
        class="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
          isActive 
            ? 'bg-white text-slate-900 shadow-sm border border-slate-200/80 scale-[1.02]' 
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
        }">
        <span class="text-base">${p.avatar}</span>
        <span>${p.name.split(' ')[0]}</span>
        <span class="text-[10px] text-slate-400 font-semibold">(${p.age}y)</span>
      </button>
    `;
  }).join('');
}

// Select Profile
async function selectProfile(profileId) {
  state.activeProfileId = profileId;
  renderProfileSelector();
  await updateActiveProfileData();
  if (state.activeTab === 'review') {
    await loadDueItems();
  } else if (state.activeTab === 'library') {
    await loadLibraryItems();
  } else if (state.activeTab === 'dashboard') {
    await loadParentDashboard();
  }
}

// Update Active Profile Header & Live Stats
async function updateActiveProfileData() {
  if (!state.activeProfileId) return;
  try {
    const res = await fetch(`/api/profiles/${state.activeProfileId}`);
    state.activeProfile = await res.json();
    
    // Update Sub-Header Elements
    document.getElementById("headerAvatar").innerText = state.activeProfile.avatar;
    document.getElementById("headerKidName").innerText = state.activeProfile.name;
    document.getElementById("headerKidAge").innerText = `(Age ${state.activeProfile.age})`;
    document.getElementById("headerStreak").innerText = state.activeProfile.streak_days;
    
    // Breakdown Stats
    const bd = state.activeProfile.breakdown || {};
    const colTot = bd.collocation ? bd.collocation.total : 0;
    const senTot = bd.sentence ? bd.sentence.total : 0;
    const wrdTot = bd.word ? bd.word.total : 0;
    const masTot = (bd.collocation?.mastered || 0) + (bd.sentence?.mastered || 0) + (bd.word?.mastered || 0);

    document.getElementById("statCollocations").innerText = colTot;
    document.getElementById("statSentences").innerText = senTot;
    document.getElementById("statWords").innerText = wrdTot;
    document.getElementById("statMastered").innerText = masTot;

    // Load Due Items
    await loadDueItems();
  } catch (err) {
    console.error("Error updating profile data:", err);
  }
}

// Load SRS Due Items for Active Profile
async function loadDueItems(forceReset = false) {
  if (!state.activeProfileId) return;
  try {
    const res = await fetch(`/api/srs/due?profile_id=${state.activeProfileId}`);
    state.dueItems = await res.json();
    
    document.getElementById("badgeDue").innerText = state.dueItems.length;
    
    if (forceReset || state.currentCardIndex >= state.dueItems.length) {
      state.currentCardIndex = 0;
    }
    
    state.isFlipped = false;
    state.userAudioUrl = null;
    renderCurrentCard();
  } catch (err) {
    console.error("Error loading due items:", err);
  }
}

// Render Current Flashcard in Daily Review
function renderCurrentCard() {
  const cardArea = document.getElementById("reviewCardArea");
  const completedArea = document.getElementById("reviewCompletedArea");
  
  if (!state.dueItems || state.dueItems.length === 0 || state.currentCardIndex >= state.dueItems.length) {
    cardArea.innerHTML = "";
    completedArea.classList.remove("hidden");
    lucide.createIcons();
    return;
  }
  
  completedArea.classList.add("hidden");
  const item = state.dueItems[state.currentCardIndex];
  const progressPercent = Math.round(((state.currentCardIndex + 1) / state.dueItems.length) * 100);
  
  // Type styling
  let typeLabel = "Word";
  let typeColor = "amber";
  let typeIcon = "📚";
  if (item.item_type === "collocation") {
    typeLabel = "Collocation";
    typeColor = "indigo";
    typeIcon = "🔗";
  } else if (item.item_type === "sentence") {
    typeLabel = "Sentence";
    typeColor = "emerald";
    typeIcon = "💬";
  }

  // Audio-First display state
  const isAudioFirstActive = state.isAudioFirst && !state.isFlipped;
  
  cardArea.innerHTML = `
    <div class="bg-white rounded-3xl border border-slate-200/90 shadow-lg shadow-slate-100 overflow-hidden transition-all duration-300">
      
      <!-- Card Top Bar: Progress & Category -->
      <div class="px-6 py-4 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-extrabold bg-${typeColor}-100 text-${typeColor}-800">
            <span class="mr-1.5">${typeIcon}</span> ${typeLabel.toUpperCase()}
          </span>
          <span class="text-xs text-slate-400 font-bold uppercase tracking-wider">
            Card ${state.currentCardIndex + 1} of ${state.dueItems.length}
          </span>
        </div>
        <div class="flex items-center space-x-2">
          <span class="text-xs font-bold text-slate-500">${item.state ? item.state.toUpperCase() : 'NEW'}</span>
          <div class="w-20 bg-slate-200 rounded-full h-2 overflow-hidden">
            <div class="bg-orange-500 h-2 rounded-full transition-all duration-300" style="width: ${progressPercent}%"></div>
          </div>
        </div>
      </div>

      <!-- Card Core Body -->
      <div class="p-8 text-center min-h-[300px] flex flex-col justify-center items-center relative">
        
        ${isAudioFirstActive ? `
          <!-- AUDIO-FIRST PROMPT: Audio wave & Listen button -->
          <div class="space-y-5 my-4">
            <div class="w-24 h-24 mx-auto rounded-3xl bg-gradient-to-tr from-orange-400 to-amber-400 flex items-center justify-center text-white shadow-xl shadow-orange-200 cursor-pointer transform hover:scale-105 active:scale-95 transition"
              onclick="speakCurrentText()">
              <i data-lucide="volume-2" class="w-12 h-12"></i>
            </div>
            
            <div class="flex items-center justify-center space-x-1.5 h-7">
              <span class="w-1.5 bg-orange-400 rounded-full wave-bar"></span>
              <span class="w-1.5 bg-orange-500 rounded-full wave-bar"></span>
              <span class="w-1.5 bg-amber-500 rounded-full wave-bar"></span>
              <span class="w-1.5 bg-orange-400 rounded-full wave-bar"></span>
              <span class="w-1.5 bg-amber-400 rounded-full wave-bar"></span>
            </div>

            <div>
              <h3 class="text-xl font-extrabold text-slate-800 kid-font">Listen to the native voice!</h3>
              <p class="text-xs text-slate-500 mt-1">Tap the speaker to replay, then speak out loud</p>
            </div>

            <!-- Voice Recording Interactive Check -->
            <div class="pt-2 flex flex-col items-center">
              <button onclick="startVoiceInput()" id="btnMicRecord" 
                class="px-4 py-2 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs flex items-center space-x-2 transition border border-slate-200">
                <i data-lucide="mic" class="w-4 h-4 text-red-500"></i>
                <span id="micLabel">Tap to speak & check pronunciation</span>
              </button>
              <div id="speechFeedback" class="text-xs font-bold mt-2 text-emerald-600 min-h-[20px]"></div>
            </div>

          </div>
        ` : `
          <!-- REVEALED CONTENT / STANDARD VIEW -->
          <div class="space-y-4 w-full">
            
            <!-- Audio Speaker Button -->
            <button onclick="speakCurrentText()" class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-orange-100 text-orange-700 hover:bg-orange-200 font-bold text-xs transition">
              <i data-lucide="volume-2" class="w-4 h-4"></i>
              <span>Play Native Audio</span>
            </button>

            <!-- English Text -->
            <h2 class="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight kid-font">
              ${escapeHtml(item.english_text)}
            </h2>

            <!-- IPA Phonetic if available -->
            ${item.ipa_phonetic ? `
              <div class="text-sm font-mono text-slate-400">${escapeHtml(item.ipa_phonetic)}</div>
            ` : ''}

            <!-- Vietnamese Meaning -->
            <div class="pt-3 pb-1 border-t border-slate-100">
              <div class="text-lg sm:text-xl font-bold text-orange-600">
                ${escapeHtml(item.vietnamese_meaning)}
              </div>
            </div>

            <!-- Example Sentence / Context -->
            ${item.example_sentence ? `
              <div class="bg-amber-50/60 p-4 rounded-2xl border border-amber-100/80 text-xs sm:text-sm text-slate-700 italic max-w-lg mx-auto">
                "${escapeHtml(item.example_sentence)}"
              </div>
            ` : ''}

            <!-- Child's Voice Playback (if recorded) -->
            ${state.userAudioUrl ? `
              <div class="pt-2">
                <button onclick="playUserRecording()" class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-purple-100 text-purple-700 text-xs font-bold hover:bg-purple-200 transition">
                  <i data-lucide="play" class="w-3.5 h-3.5"></i>
                  <span>Play My Voice</span>
                </button>
              </div>
            ` : ''}

          </div>
        `}

      </div>

      <!-- Card Bottom Actions -->
      <div class="p-6 bg-slate-50 border-t border-slate-100">
        ${!state.isFlipped ? `
          <button onclick="flipCard()" class="w-full py-4 bg-orange-500 hover:bg-orange-600 active:scale-[0.99] text-white font-extrabold rounded-2xl shadow-md shadow-orange-200 transition text-base flex items-center justify-center space-x-2">
            <span>Check Meaning & Spelling</span>
            <i data-lucide="arrow-right" class="w-5 h-5"></i>
          </button>
        ` : `
          <!-- 3-Tier Kid-Friendly SRS Rating Buttons -->
          <div>
            <div class="text-xs font-bold text-center text-slate-500 uppercase tracking-wider mb-3">How well did you remember and pronounce it?</div>
            <div class="grid grid-cols-3 gap-3">
              
              <!-- 1: Again / Practice -->
              <button onclick="submitReview(1)" class="p-3.5 rounded-2xl border-2 border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-800 font-extrabold transition flex flex-col items-center justify-center space-y-1">
                <span class="text-xl">🌱</span>
                <span class="text-xs font-bold">Practice Again</span>
                <span class="text-[10px] text-rose-600 font-semibold">Today</span>
              </button>

              <!-- 2: Good Job -->
              <button onclick="submitReview(2)" class="p-3.5 rounded-2xl border-2 border-emerald-200 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-extrabold transition flex flex-col items-center justify-center space-y-1">
                <span class="text-xl">👍</span>
                <span class="text-xs font-bold">Good Job!</span>
                <span class="text-[10px] text-emerald-600 font-semibold">+2-3 days</span>
              </button>

              <!-- 3: Super Easy -->
              <button onclick="submitReview(3)" class="p-3.5 rounded-2xl border-2 border-amber-200 bg-amber-50 hover:bg-amber-100 text-amber-800 font-extrabold transition flex flex-col items-center justify-center space-y-1">
                <span class="text-xl">🌟</span>
                <span class="text-xs font-bold">Super Easy!</span>
                <span class="text-[10px] text-amber-600 font-semibold">+4-6 days</span>
              </button>

            </div>
          </div>
        `}
      </div>

    </div>
  `;
  
  lucide.createIcons();

  // Auto-play sound if Audio-First mode is ON
  if (isAudioFirstActive) {
    setTimeout(() => {
      speakCurrentText();
    }, 300);
  }
}

// Flip Card Action
function flipCard() {
  playChime('flip');
  state.isFlipped = true;
  renderCurrentCard();
}

// Toggle Audio-First Mode
function toggleAudioFirstMode(checked) {
  state.isAudioFirst = checked;
  renderCurrentCard();
}

// Text-To-Speech Execution
function speakCurrentText() {
  if (!state.dueItems || state.dueItems.length === 0) return;
  const item = state.dueItems[state.currentCardIndex];
  speakText(item.english_text);
}

function speakText(text) {
  if (!('speechSynthesis' in window)) {
    alert("Speech Synthesis not supported by this browser.");
    return;
  }
  window.speechSynthesis.cancel(); // cancel any active speech
  
  const utterance = new SpeechSynthesisUtterance(text);
  const accent = document.getElementById("voiceAccentSelect") ? document.getElementById("voiceAccentSelect").value : 'en-US';
  utterance.lang = accent;
  
  // Rate adjustment for kid age
  if (state.activeProfile && state.activeProfile.age <= 8) {
    utterance.rate = 0.88; // clear, gentle tempo for 7yo
  } else {
    utterance.rate = 0.95; // natural tempo for 11yo
  }
  
  // Voice selection
  const voices = window.speechSynthesis.getVoices();
  const matchedVoice = voices.find(v => v.lang.startsWith(accent.slice(0, 2)) && (v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("Samantha") || v.name.includes("Daniel")));
  if (matchedVoice) utterance.voice = matchedVoice;
  
  window.speechSynthesis.speak(utterance);
}

// Setup Speech Recognition (Speech-to-Text)
function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("Speech recognition not supported in this browser.");
    return;
  }
  state.recognition = new SpeechRecognition();
  state.recognition.continuous = false;
  state.recognition.interimResults = false;
  state.recognition.lang = 'en-US';

  state.recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    handleSpokenResult(transcript);
  };

  state.recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    const fb = document.getElementById("speechFeedback");
    if (fb) fb.innerHTML = `<span class="text-slate-500">Could not hear clearly. Try again!</span>`;
    stopVoiceInputUi();
  };

  state.recognition.onend = () => {
    stopVoiceInputUi();
  };
}

// Start Voice Recording & Pronunciation Check
function startVoiceInput() {
  if (!state.recognition) {
    alert("Voice recognition is best supported in Chrome, Edge, or Safari.");
    return;
  }
  
  const btn = document.getElementById("btnMicRecord");
  const label = document.getElementById("micLabel");
  const fb = document.getElementById("speechFeedback");
  
  if (state.isRecording) {
    state.recognition.stop();
    stopVoiceInputUi();
    return;
  }
  
  try {
    state.recognition.start();
    state.isRecording = true;
    if (btn) btn.classList.add("bg-red-100", "border-red-300", "animate-pulse");
    if (label) label.innerText = "Listening... Speak now!";
    if (fb) fb.innerText = "";
    
    // Also record raw audio if MediaRecorder is available
    startMediaAudioCapture();
  } catch (err) {
    console.error("Failed to start speech recognition:", err);
  }
}

function stopVoiceInputUi() {
  state.isRecording = false;
  const btn = document.getElementById("btnMicRecord");
  const label = document.getElementById("micLabel");
  if (btn) btn.classList.remove("bg-red-100", "border-red-300", "animate-pulse");
  if (label) label.innerText = "Tap to speak & check pronunciation";
}

// Compare Spoken Transcript with Target
function handleSpokenResult(transcript) {
  const item = state.dueItems[state.currentCardIndex];
  if (!item) return;
  
  const target = item.english_text.toLowerCase().replace(/[^\w\s]/g, "").trim();
  const spoken = transcript.toLowerCase().replace(/[^\w\s]/g, "").trim();
  
  const fb = document.getElementById("speechFeedback");
  if (!fb) return;
  
  if (spoken.includes(target) || target.includes(spoken) || levenshteinSimilarity(target, spoken) > 0.65) {
    playChime('star');
    fb.innerHTML = `
      <div class="flex items-center space-x-1.5 text-emerald-600 font-extrabold animate-bounce">
        <span>🎉 Fantastic! You said: "${transcript}"</span>
      </div>
    `;
  } else {
    fb.innerHTML = `
      <div class="text-amber-600 font-bold">
        <span>Heard: "${transcript}" (Keep practicing!)</span>
      </div>
    `;
  }
}

// Levenshtein Similarity calculation for speech tolerance
function levenshteinSimilarity(s1, s2) {
  let longer = s1.length < s2.length ? s2 : s1;
  let shorter = s1.length < s2.length ? s1 : s2;
  if (longer.length === 0) return 1.0;
  
  const costs = [];
  for (let i = 0; i <= longer.length; i++) {
    let lastValue = i;
    for (let j = 0; j <= shorter.length; j++) {
      if (i === 0) costs[j] = j;
      else if (j > 0) {
        let newValue = costs[j - 1];
        if (longer.charAt(i - 1) !== shorter.charAt(j - 1)) {
          newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
        }
        costs[j - 1] = lastValue;
        lastValue = newValue;
      }
    }
    if (i > 0) costs[shorter.length] = lastValue;
  }
  return (longer.length - costs[shorter.length]) / parseFloat(longer.length);
}

// Raw Audio Recording with MediaRecorder for Self-Comparison
async function startMediaAudioCapture() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.mediaRecorder = new MediaRecorder(stream);
    state.audioChunks = [];
    
    state.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) state.audioChunks.push(e.data);
    };
    
    state.mediaRecorder.onstop = () => {
      const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
      state.userAudioUrl = URL.createObjectURL(audioBlob);
      // Re-render card to display "Play My Voice" button
      if (state.isFlipped) renderCurrentCard();
    };
    
    state.mediaRecorder.start();
    // Stop recording automatically after 4 seconds
    setTimeout(() => {
      if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
        state.mediaRecorder.stop();
      }
    }, 4000);
  } catch (e) {
    console.warn("MediaRecorder permission denied or unavailable", e);
  }
}

function playUserRecording() {
  if (state.userAudioUrl) {
    const audio = new Audio(state.userAudioUrl);
    audio.play();
  }
}

// Submit SRS Review Result
async function submitReview(rating) {
  if (!state.dueItems || state.dueItems.length === 0) return;
  const currentItem = state.dueItems[state.currentCardIndex];
  
  if (rating === 3) {
    playChime('star');
  } else if (rating === 2) {
    playChime('success');
  } else {
    playChime('flip');
  }
  
  try {
    const res = await fetch("/api/srs/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        item_id: currentItem.id,
        profile_id: state.activeProfileId,
        rating: rating
      })
    });
    
    const result = await res.json();
    
    // Update streak counter if returned
    if (result.streak_days) {
      document.getElementById("headerStreak").innerText = result.streak_days;
    }

    // Move to next card
    state.currentCardIndex++;
    state.isFlipped = false;
    state.userAudioUrl = null;
    
    // Check if deck is finished
    if (state.currentCardIndex >= state.dueItems.length) {
      triggerConfetti();
      await updateActiveProfileData();
    } else {
      renderCurrentCard();
    }
  } catch (err) {
    console.error("Failed to submit review:", err);
  }
}

// Celebration Confetti
function triggerConfetti() {
  if (window.confetti) {
    window.confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    });
  }
}

// Form Submission for Daily Input (Add New Word / Collocation / Sentence)
async function handleFormSubmit(event) {
  event.preventDefault();
  
  const form = document.getElementById("addItemForm");
  const selectedType = form.elements["item_type"].value;
  const english = document.getElementById("inputEnglish").value.trim();
  const vietnamese = document.getElementById("inputVietnamese").value.trim();
  const example = document.getElementById("inputExample").value.trim();
  const ipa = document.getElementById("inputIpa").value.trim();
  const note = document.getElementById("inputNote").value.trim();
  
  if (!english || !vietnamese) {
    alert("Please provide both English text and Vietnamese meaning.");
    return;
  }
  
  try {
    const res = await fetch("/api/items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profile_id: state.activeProfileId,
        item_type: selectedType,
        english_text: english,
        vietnamese_meaning: vietnamese,
        example_sentence: example,
        ipa_phonetic: ipa,
        context_note: note
      })
    });
    
    if (res.ok) {
      playChime('success');
      form.reset();
      alert(`🎉 Successfully added ${selectedType} for ${state.activeProfile.name}! Queued for daily SRS review.`);
      await updateActiveProfileData();
      switchTab('review');
    } else {
      alert("Failed to save item. Please check inputs.");
    }
  } catch (err) {
    console.error("Error creating item:", err);
  }
}

function previewCurrentAudio() {
  const eng = document.getElementById("inputEnglish").value.trim();
  if (eng) {
    speakText(eng);
  } else {
    speakText("Make a wish");
  }
}

// Tab Switching
function switchTab(tabName) {
  state.activeTab = tabName;
  
  const tabs = ['review', 'add', 'library', 'dashboard'];
  tabs.forEach(t => {
    const sec = document.getElementById(`tab-${t}`);
    const btn = document.getElementById(`nav-${t}`);
    if (t === tabName) {
      sec.classList.remove('hidden');
      btn.classList.add('bg-orange-500', 'text-white', 'shadow-sm', 'shadow-orange-200');
      btn.classList.remove('text-slate-600', 'hover:bg-slate-100');
    } else {
      sec.classList.add('hidden');
      btn.classList.remove('bg-orange-500', 'text-white', 'shadow-sm', 'shadow-orange-200');
      btn.classList.add('text-slate-600', 'hover:bg-slate-100');
    }
  });

  if (tabName === 'library') {
    loadLibraryItems();
  } else if (tabName === 'dashboard') {
    loadParentDashboard();
  } else if (tabName === 'review') {
    loadDueItems();
  }
  
  lucide.createIcons();
}

// Load and Render Learning Library
async function loadLibraryItems() {
  if (!state.activeProfileId) return;
  try {
    const res = await fetch(`/api/items?profile_id=${state.activeProfileId}`);
    state.allLibraryItems = await res.json();
    filterLibrary();
  } catch (err) {
    console.error("Failed to load library items:", err);
  }
}

function filterLibrary() {
  const search = document.getElementById("libSearch").value.toLowerCase();
  const typeFilter = document.getElementById("libTypeFilter").value;
  const stateFilter = document.getElementById("libStateFilter").value;
  
  const filtered = state.allLibraryItems.filter(item => {
    const matchSearch = !search || 
      item.english_text.toLowerCase().includes(search) || 
      item.vietnamese_meaning.toLowerCase().includes(search) ||
      (item.example_sentence && item.example_sentence.toLowerCase().includes(search));
    const matchType = !typeFilter || item.item_type === typeFilter;
    const matchState = !stateFilter || item.state === stateFilter;
    return matchSearch && matchType && matchState;
  });
  
  renderLibraryGrid(filtered);
}

function renderLibraryGrid(items) {
  const container = document.getElementById("libraryContainer");
  if (!container) return;
  
  if (items.length === 0) {
    container.innerHTML = `
      <div class="col-span-full text-center py-12 bg-white rounded-3xl border border-slate-200">
        <div class="text-4xl mb-3">🔍</div>
        <div class="text-base font-bold text-slate-800">No items match your filter</div>
        <div class="text-xs text-slate-400 mt-1">Try switching filters or add a new collocation!</div>
      </div>
    `;
    return;
  }
  
  container.innerHTML = items.map(item => {
    let typeIcon = "📚";
    let typeColor = "amber";
    if (item.item_type === "collocation") { typeIcon = "🔗"; typeColor = "indigo"; }
    else if (item.item_type === "sentence") { typeIcon = "💬"; typeColor = "emerald"; }
    
    return `
      <div class="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition flex flex-col justify-between space-y-3">
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-${typeColor}-100 text-${typeColor}-800">
              <span class="mr-1">${typeIcon}</span> ${item.item_type.toUpperCase()}
            </span>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${
              item.state === 'mastered' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
            }">
              ${item.state.toUpperCase()}
            </span>
          </div>

          <div class="flex items-start justify-between gap-2">
            <h4 class="text-lg font-extrabold text-slate-900 kid-font leading-snug">${escapeHtml(item.english_text)}</h4>
            <button onclick="speakText('${escapeJsString(item.english_text)}')" class="p-1.5 rounded-xl bg-orange-50 text-orange-600 hover:bg-orange-100 transition flex-shrink-0">
              <i data-lucide="volume-2" class="w-4 h-4"></i>
            </button>
          </div>

          ${item.ipa_phonetic ? `<div class="text-xs font-mono text-slate-400 mt-0.5">${escapeHtml(item.ipa_phonetic)}</div>` : ''}

          <div class="text-xs font-bold text-slate-700 mt-2">${escapeHtml(item.vietnamese_meaning)}</div>

          ${item.example_sentence ? `
            <div class="text-xs text-slate-500 italic mt-2 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
              "${escapeHtml(item.example_sentence)}"
            </div>
          ` : ''}
        </div>

        <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 font-medium">
          <span>Interval: ${item.interval_days}d (${item.repetitions} reps)</span>
          <button onclick="deleteItem(${item.id})" class="text-rose-500 hover:text-rose-700 font-bold">Delete</button>
        </div>
      </div>
    `;
  }).join('');
  
  lucide.createIcons();
}

async function deleteItem(id) {
  if (!confirm("Are you sure you want to delete this item?")) return;
  try {
    await fetch(`/api/items/${id}`, { method: "DELETE" });
    await updateActiveProfileData();
    await loadLibraryItems();
  } catch (err) {
    console.error("Failed to delete item:", err);
  }
}

// Load Parent Monitoring Dashboard
async function loadParentDashboard() {
  try {
    const res = await fetch("/api/stats/dashboard");
    const data = await res.json();
    
    // Overview KPIs
    document.getElementById("parentTotalCollocations").innerText = data.overview.total_collocations || 0;
    document.getElementById("parentTotalSentences").innerText = data.overview.total_sentences || 0;
    document.getElementById("parentTotalWords").innerText = data.overview.total_words || 0;
    document.getElementById("parentTotalMastered").innerText = data.overview.total_mastered || 0;

    // Render Side-by-Side Comparison for Kid 1 and Kid 2
    const kidsContainer = document.getElementById("kidsComparisonCards");
    if (!kidsContainer) return;
    
    kidsContainer.innerHTML = data.kids.map(k => {
      const p = k.profile;
      const w = k.words;
      const c = k.collocations;
      const s = k.sentences;
      const totalAll = (w.total || 0) + (c.total || 0) + (s.total || 0);
      const totalMastered = (w.mastered || 0) + (c.mastered || 0) + (s.mastered || 0);
      const masteryRate = totalAll > 0 ? Math.round((totalMastered / totalAll) * 100) : 0;
      
      return `
        <div class="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm space-y-5">
          <!-- Child Profile Header -->
          <div class="flex items-center justify-between border-b border-slate-100 pb-4">
            <div class="flex items-center space-x-3">
              <span class="text-3xl">${p.avatar}</span>
              <div>
                <h4 class="text-lg font-extrabold text-slate-900 kid-font">${p.name}</h4>
                <p class="text-xs text-slate-500">Age: ${p.age} years old | Streak: <span class="text-orange-600 font-bold">${p.streak_days} days</span></p>
              </div>
            </div>
            <div class="text-right">
              <div class="text-xs font-bold text-slate-400 uppercase">Due Today</div>
              <div class="text-xl font-extrabold ${k.due_today > 0 ? 'text-orange-600' : 'text-emerald-600'}">
                ${k.due_today} cards
              </div>
            </div>
          </div>

          <!-- 3-Tier Categorical Counters -->
          <div class="grid grid-cols-3 gap-3 text-center">
            <div class="p-3 rounded-2xl bg-indigo-50 border border-indigo-100">
              <div class="text-xs font-bold text-indigo-700">🔗 Collocations</div>
              <div class="text-2xl font-black text-indigo-900 mt-1">${c.total || 0}</div>
              <div class="text-[10px] text-indigo-600 font-semibold mt-0.5">${c.mastered || 0} mastered</div>
            </div>

            <div class="p-3 rounded-2xl bg-emerald-50 border border-emerald-100">
              <div class="text-xs font-bold text-emerald-700">💬 Sentences</div>
              <div class="text-2xl font-black text-emerald-900 mt-1">${s.total || 0}</div>
              <div class="text-[10px] text-emerald-600 font-semibold mt-0.5">${s.mastered || 0} mastered</div>
            </div>

            <div class="p-3 rounded-2xl bg-amber-50 border border-amber-100">
              <div class="text-xs font-bold text-amber-700">📚 Words</div>
              <div class="text-2xl font-black text-amber-900 mt-1">${w.total || 0}</div>
              <div class="text-[10px] text-amber-600 font-semibold mt-0.5">${w.mastered || 0} mastered</div>
            </div>
          </div>

          <!-- Overall Mastery Progress Bar -->
          <div>
            <div class="flex justify-between text-xs font-bold text-slate-600 mb-1.5">
              <span>Overall Long-Term Retention</span>
              <span>${masteryRate}% (${totalMastered}/${totalAll})</span>
            </div>
            <div class="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
              <div class="bg-gradient-to-r from-amber-400 to-emerald-500 h-3 rounded-full transition-all duration-500" style="width: ${masteryRate}%"></div>
            </div>
          </div>

          <!-- Action Button -->
          <button onclick="selectProfile(${p.id}); switchTab('review');" class="w-full py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition flex items-center justify-center space-x-1.5">
            <i data-lucide="play" class="w-3.5 h-3.5"></i>
            <span>Switch to ${p.name.split(' ')[0]}'s Practice Room</span>
          </button>
        </div>
      `;
    }).join('');
    
    lucide.createIcons();
  } catch (err) {
    console.error("Failed to load dashboard:", err);
  }
}

// Backup Export
async function exportData() {
  try {
    const res = await fetch("/api/export");
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `echokids_backup_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
  } catch (err) {
    console.error("Export error:", err);
  }
}

// Reseed Sample Decks
async function reseedSampleData() {
  if (!confirm("This will reload curated sample collocations, words, and sentences for both kids. Continue?")) return;
  try {
    await fetch("/api/seed", { method: "POST" });
    alert("Sample decks loaded successfully!");
    await updateActiveProfileData();
    await loadParentDashboard();
  } catch (err) {
    console.error("Reseed error:", err);
  }
}

// Utilities
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function escapeJsString(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '\\"');
}
