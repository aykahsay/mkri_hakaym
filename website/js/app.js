/**
 * Mkri Hakaym (ምኽሪ ሓካይም) - Interactive Portal Logic
 * 2G Phone Simulator, Red-Flag Triage Engine, and Dataset Explorer
 */

// Global State
let currentLang = 'ti'; // 'ti' or 'en'
let callState = 'STANDBY'; // 'STANDBY', 'CALLING', 'IN_CALL', 'DOCTOR_SPEAKING', 'EMERGENCY'
let dialedNumber = '';
let currentAudio = null;

// Clinical Red-Flags Matching Patterns (Exact mirror of brain/triage_rules.py)
const RED_FLAG_RULES = {
  maternal_hemorrhage: {
    title_ti: 'ምፍሳስ ደም ኣብ ጥንሲ (Maternal Bleeding)',
    title_en: 'Maternal Vaginal Bleeding in Pregnancy',
    patterns: [/ምፍሳስ ደም/, /ደም ምፍሳስ/, /ደም ይፈሰ[ኒካኪ]/, /ደም ፈሲሱ[ኒካኪ]/, /ደም ኣሎ[ኒኪ]/, /ደም መጺኡ[ኒኪ]/, /ደም ርእየ/],
    level: 'CRITICAL',
    msg_ti: '🚨 ኣድህቡ! ኣብ እዋን ጥንሲ ምፍሳስ ደም ቀይሕ ምልክት (ሓደጋ) እዩ። ብቕጽበት ናብ ዝቐረበ ሆስፒታል ወይ ጥዕና ጣብያ ኪዱ! ኣብ ገዛ ደው ኣይትበሉ!',
    msg_en: 'Immediate Emergency: Vaginal bleeding during pregnancy is a critical red flag. Go to the nearest hospital immediately!',
    action_ti: 'ህጹጽ ናብ ሆስፒታል ምኻድ የድሊ',
  },
  preeclampsia: {
    title_ti: 'ጸቕጢ ደም ጥንሲ (Pre-eclampsia)',
    title_en: 'Pre-eclampsia / Severe Hypertension',
    patterns: [/ብርቱዕ.*(ርእሲ|ርእሰይ)/, /(ርእሲ|ርእሰይ).*ብርቱዕ/, /ዓይኒ.*(ምፍዛዝ|ዘይምርኣይ)/, /ሕበጥ.*(ገጽ|ኣእጋር)/, /መንቀጥቀጥ/],
    level: 'CRITICAL',
    msg_ti: '🚨 ብርቱዕ ርእሲ ሕማም ምስ ዓይኒ ምፍዛዝ ኣብ ጥንሲ ምልክት ልዑል ጸቕጢ ደም (Pre-eclampsia) ክኸውን ስለዝኽእል ቀጥታ ናብ ጥዕና ጣብያ ብምኻድ ጸቕጢ ደምኩም ተመርመሩ።',
    msg_en: 'Critical Emergency: Severe headache, visual disturbance, or sudden facial edema in pregnancy indicates possible pre-eclampsia.',
    action_ti: 'ህጹጽ መርመራ ጸቕጢ ደም የድሊ',
  },
  fetal_distress: {
    title_ti: 'ምንቅስቓስ ዕሸል ምቁራጽ',
    title_en: 'Reduced Fetal Movement',
    patterns: [/ዕሸል.*(ምንቅስቓስ|ምንቅስቃስ)/, /ምንቅስቓስ.*ዕሸል/, /ዕሸል.*ኣይተንቀሳቐሰን/],
    level: 'CRITICAL',
    msg_ti: '🚨 ዕሸል ምንቅስቓስ እንተኣቋሪጹ ወይ ብርቱዕ እንተነክዩ፣ ብዘይ ምድንጓይ ህጹጽ ናይ ዕሸል ትርቂ ልቢ መርመራ ክግበር ይግባእ።',
    msg_en: 'Critical Emergency: Cessation or marked reduction in fetal movements requires urgent heartbeat monitoring.',
    action_ti: 'ህጹጽ መርመራ ትርቂ ልቢ ዕሸል',
  },
  pediatric_pneumonia: {
    title_ti: 'ነድሪ ሳምባ ኣብ ህጻናት (Pneumonia)',
    title_en: 'Pediatric Pneumonia & Chest Indrawing',
    patterns: [/ፈጣን.*ኣተነፋፍሳ/, /ኣተነፋፍሳ.*ፈጣን/, /ደረት.*ውሽጢ/, /ነድሪ ሳምባ/],
    level: 'CRITICAL',
    msg_ti: '🚨 ህጻን ደረቱ ናብ ውሽጢ ዝሰሕብ ወይ ኣዝዩ ፈጣን ኣተነፋፍሳ ዘለዎ እንተኾይኑ ናይ ነድሪ ሳምባ (Pneumonia) ምልክት ስለዝኾነ ብቕጽበት ናብ ጥዕና ጣብያ ውሰድዎ!',
    msg_en: 'Critical Emergency: Rapid breathing or chest indrawing in children indicates pneumonia. Seek immediate health center care.',
    action_ti: 'ህጹጽ ሕክምና ነድሪ ሳምባ',
  },
  dehydration: {
    title_ti: 'ውጽኣትን ተምላስን ኣብ ህጻናት',
    title_en: 'Pediatric Acute Diarrhea & Dehydration',
    patterns: [/ውጽኣት/, /ተምላስ/, /ማይ ምውዳእ/, /ልሕሉሕ/],
    level: 'HIGH',
    msg_ti: '⚠️ ተምላስን ውጽኣትን ማይ ኣብ ውሽጢ ሰብነት ስለዘውድእ፣ ብቕጽበት ኦ.ኣር.ኤስ (ORS) ወይ ማይ ብጨውን ሽኮርን እናሃብኩም ናብ ጥዕና ጣብያ ውሰድዎ።',
    msg_en: 'Urgent: Vomiting and diarrhea cause rapid dehydration. Immediately administer ORS and visit a clinic.',
    action_ti: 'ምሃብ ኦ.ኣር.ኤስ (ORS) + ናብ ጥዕና ጣብያ',
  }
};

// Web Audio API DTMF Generator
let audioCtx = null;
function playDTMF(digit) {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    const dtmfFreqs = {
      '1': [697, 1209], '2': [697, 1336], '3': [697, 1477],
      '4': [770, 1209], '5': [770, 1336], '6': [770, 1477],
      '7': [852, 1209], '8': [852, 1336], '9': [852, 1477],
      '*': [941, 1209], '0': [941, 1336], '#': [941, 1477],
    };

    const freqs = dtmfFreqs[digit] || [440, 440];
    const osc1 = audioCtx.createOscillator();
    const osc2 = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc1.frequency.value = freqs[0];
    osc2.frequency.value = freqs[1];

    gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.18);

    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(audioCtx.destination);

    osc1.start();
    osc2.start();
    osc1.stop(audioCtx.currentTime + 0.18);
    osc2.stop(audioCtx.currentTime + 0.18);
  } catch (e) {
    console.log('AudioContext not allowed or not supported yet');
  }
}

// ---------------------------------------------------------------------------
// 2G Phone Simulator Functions
// ---------------------------------------------------------------------------
function updatePhoneScreen(contentHtml, statusTop = null, statusBottom = null) {
  const contentEl = document.getElementById('phoneScreenContent');
  const topEl = document.getElementById('screenTopStatus');
  const btmEl = document.getElementById('screenBtmStatus');

  if (contentEl) contentEl.innerHTML = contentHtml;
  if (statusTop && topEl) topEl.innerText = statusTop;
  if (statusBottom && btmEl) btmEl.innerText = statusBottom;
}

function handleKeypress(digit) {
  playDTMF(digit);

  if (callState === 'STANDBY') {
    dialedNumber += digit;
    updatePhoneScreen(`
      <div style="text-align:center; padding-top:20px;">
        <div style="font-size:0.75rem;">DIALING...</div>
        <div style="font-size:1.25rem; font-weight:800; letter-spacing:2px; margin-top:8px;">${dialedNumber}</div>
        <div style="font-size:0.7rem; color:#166534; margin-top:14px;">Press [CALL] to connect</div>
      </div>
    `, 'ETHIO TEL 2G', 'CALL / CLEAR');
    return;
  }

  if (callState === 'MENU' || callState === 'IN_CALL' || callState === 'DOCTOR_SPEAKING') {
    if (digit === '1') {
      simulatePresetQuestion('ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?');
    } else if (digit === '2') {
      simulatePresetQuestion('ቆልዓይ ውጽኣትን ተምላስን እንተኣጋጢምዎ እንታይ ክገብር?');
    } else if (digit === '3') {
      simulatePresetQuestion('ልዑል ጸቕጢ ደም እንታይ ምልክታት ኣለዎ?');
    } else if (digit === '0') {
      updatePhoneScreen(`
        <div style="text-align:center; padding-top:16px;">
          <div style="font-size:0.9rem; font-weight:800;">ናብ ሓኪም/ነርስ ምትሕልላፍ</div>
          <div style="font-size:0.75rem; margin-top:8px;">Routing call to on-duty Community Health Worker...</div>
          <div style="font-size:0.75rem; color:#b91c1c; font-weight:800; margin-top:12px;">📞 መስመር ክፍቲ እዩ (Dialing 800)</div>
        </div>
      `, 'CALL CONNECTED', 'HANGUP');
    }
  }
}

function startCall() {
  playDTMF('1');
  callState = 'CALLING';
  dialedNumber = '800';

  updatePhoneScreen(`
    <div style="text-align:center; padding-top:20px;">
      <div style="font-size:0.75rem;">CALLING...</div>
      <div style="font-size:1.15rem; font-weight:800; margin:6px 0;">800 (ምኽሪ ሓካይም)</div>
      <div style="font-size:0.7rem; color:#166534;">Connecting to Voice Gateway...</div>
    </div>
  `, 'ETHIO TEL 2G', 'CONNECTING...');

  setTimeout(() => {
    callState = 'MENU';
    updatePhoneScreen(`
      <div>
        <div style="font-size:0.75rem; font-weight:800; border-bottom:1px solid #166534; padding-bottom:2px; margin-bottom:4px;">
          ምኽሪ ሓካይም (2G MENU)
        </div>
        <div style="font-size:0.72rem; line-height:1.4;">
          [1] ክትትል ጥንሲ (Maternal)<br>
          [2] ጥዕና ህጻናት (Pediatrics)<br>
          [3] ሕዱራት ሕማማት (Chronic)<br>
          [0] ሓኪም/ነርስ (Nurse Handoff)
        </div>
      </div>
    `, 'CONNECTED 00:06', 'PRESS 1-3 OR 0');

    // Play welcome voice if possible
    playWelcomeAudio();
  }, 1200);
}

function endCall() {
  playDTMF('#');
  callState = 'STANDBY';
  dialedNumber = '';

  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
  }

  updatePhoneScreen(`
    <div style="text-align:center; padding-top:24px;">
      <div style="font-size:0.75rem;">CALL ENDED</div>
      <div style="font-size:0.85rem; font-weight:800; margin-top:6px;">ደሓን ይጽንሓልና!</div>
      <div style="font-size:0.7rem; color:#166534; margin-top:10px;">Press [CALL] to dial 800</div>
    </div>
  `, 'ETHIO TEL 2G', 'MENU / DIAL');
}

// Evaluate Clinical Triage against Red Flags
function evaluateTriage(query) {
  for (const [key, rule] of Object.entries(RED_FLAG_RULES)) {
    for (const pattern of rule.patterns) {
      if (pattern.test(query)) {
        return {
          is_emergency: true,
          level: rule.level,
          title: currentLang === 'ti' ? rule.title_ti : rule.title_en,
          message: currentLang === 'ti' ? rule.msg_ti : rule.msg_en,
          action: rule.action_ti,
        };
      }
    }
  }

  // Find in local dataset
  if (typeof DATASET !== 'undefined') {
    const qLower = query.toLowerCase();
    for (const item of DATASET) {
      if (item.caller_question_ti && query.includes(item.caller_question_ti.substring(0, 10))) {
        return {
          is_emergency: item.triage_level === 'CRITICAL',
          level: item.triage_level,
          title: item.topic_ti,
          message: item.doctor_answer_ti,
          action: 'መደበኛ ሕክምናዊ ምኽሪ',
        };
      }
    }
  }

  return {
    is_emergency: false,
    level: 'ROUTINE',
    title: 'ሓፈሻዊ ሕክምናዊ ምኽሪ',
    message: 'እንቋዕ ናብ ምኽሪ ሓካይም ብደሓን መጻእኹም። ሕቶኹም ተቐቢልናዮ ኣለና። ብፍላይ ኣብ እዋን ጥንሲ ቀዳማይ ክትትል ኣብ ውሽጢ ቀዳሞት 12 ሰሙናት ክጅምር ኣለዎ።',
    action: 'ናብ ጥዕና ጣብያ ምብጻሕ',
  };
}

async function simulatePresetQuestion(queryText) {
  callState = 'DOCTOR_SPEAKING';
  
  updatePhoneScreen(`
    <div style="text-align:center; padding-top:14px;">
      <div style="font-size:0.75rem; color:#166534;">🗣️ CALLER ASKING:</div>
      <div style="font-size:0.8rem; font-weight:800; margin:4px 0;">"${queryText.substring(0, 38)}..."</div>
      <div style="font-size:0.7rem; color:#15803d; margin-top:8px;">⏳ Analyzing triage rules...</div>
    </div>
  `, 'IN CALL 00:15', 'ANALYZING...');

  // Try fetching live from FastAPI backend (/api/ask), with fallback to local client logic
  let triageResult = null;
  try {
    const res = await fetch('http://127.0.0.1:8000/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_text: queryText }),
    });
    if (res.ok) {
      const data = await res.json();
      triageResult = {
        is_emergency: data.result.triage_level === 'CRITICAL',
        level: data.result.triage_level,
        title: data.result.topic_ti,
        message: data.result.doctor_response_ti,
        action: data.result.recommended_action || 'ናብ ሆስፒታል ምኻድ',
      };
    }
  } catch (err) {
    // Backend offline, fallback to local rule engine
  }

  if (!triageResult) {
    triageResult = evaluateTriage(queryText);
  }

  setTimeout(() => {
    if (triageResult.is_emergency) {
      callState = 'EMERGENCY';
      updatePhoneScreen(`
        <div style="color:#b91c1c; font-weight:800;">
          <div style="font-size:0.8rem; border-bottom:2px solid #b91c1c; padding-bottom:2px; margin-bottom:4px;">
            🚨 ህጹጽ ቀይሕ ምልክት! (CRITICAL)
          </div>
          <div style="font-size:0.72rem; line-height:1.35; color:#7f1d1d;">
            ${triageResult.message.substring(0, 160)}...
          </div>
        </div>
      `, '⚠️ EMERGENCY!', 'REFER TO CLINIC');
    } else {
      updatePhoneScreen(`
        <div>
          <div style="font-size:0.75rem; font-weight:800; color:#166534; border-bottom:1px solid #166534; padding-bottom:2px; margin-bottom:4px;">
            🩺 ዶክተር ምላሽ (DOCTOR VOICE)
          </div>
          <div style="font-size:0.72rem; line-height:1.35; max-height:115px; overflow-y:auto;">
            ${triageResult.message}
          </div>
        </div>
      `, 'CONNECTED 00:28', 'PRESS # FOR MENU');
    }
  }, 700);
}

// ---------------------------------------------------------------------------
// Hero Welcome Audio Player
// ---------------------------------------------------------------------------
function playWelcomeAudio() {
  const audioEl = document.getElementById('heroAudio');
  const playBtn = document.getElementById('playWelcomeBtn');
  const viz = document.getElementById('heroWaveform');

  if (!audioEl) return;

  if (audioEl.paused) {
    audioEl.play().then(() => {
      if (playBtn) playBtn.innerHTML = '⏸️';
      if (viz) viz.classList.add('playing');
    }).catch(e => {
      console.log('Audio autoplay prevented:', e);
    });
  } else {
    audioEl.pause();
    if (playBtn) playBtn.innerHTML = '▶️';
    if (viz) viz.classList.remove('playing');
  }

  audioEl.onended = () => {
    if (playBtn) playBtn.innerHTML = '▶️';
    if (viz) viz.classList.remove('playing');
  };
}

// ---------------------------------------------------------------------------
// Live Triage Diagnostic Input in Red-Flags Section
// ---------------------------------------------------------------------------
function runLiveTriageCheck() {
  const inputEl = document.getElementById('triageCheckInput');
  const resultEl = document.getElementById('triageCheckResult');
  if (!inputEl || !resultEl) return;

  const query = inputEl.value.trim();
  if (!query) {
    resultEl.innerHTML = '';
    return;
  }

  const res = evaluateTriage(query);
  const badgeClass = res.level === 'CRITICAL' ? 'badge-emergency' : (res.level === 'HIGH' ? 'badge-urgent' : 'badge-routine');

  resultEl.innerHTML = `
    <div style="margin-top:14px; padding:16px; border-radius:10px; background:${res.is_emergency ? '#fef2f2' : '#f0fdf4'}; border:1px solid ${res.is_emergency ? '#fca5a5' : '#86efac'};">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
        <span style="font-weight:800; font-size:0.95rem; color:${res.is_emergency ? '#991b1b' : '#166534'};">
          ${res.is_emergency ? '🚨 ህጹጽ ምልክት ተረኺቡ' : '✅ መደበኛ ሕቶ'}
        </span>
        <span class="preset-badge ${badgeClass}">${res.level}</span>
      </div>
      <div style="font-size:0.9rem; margin-bottom:8px;">${res.message}</div>
      <div style="font-size:0.8rem; font-weight:700; color:${res.is_emergency ? '#b91c1c' : '#15803d'};">
        👉 ዝምከር ስጉምቲ: ${res.action}
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Dataset Table Rendering & Search
// ---------------------------------------------------------------------------
let currentFilter = 'ALL';

function renderDatasetTable(filter = 'ALL', search = '') {
  const tbody = document.getElementById('datasetTableBody');
  const countEl = document.getElementById('datasetRowCount');
  if (!tbody || typeof DATASET === 'undefined') return;

  let items = DATASET;

  // Filter by tag/topic
  if (filter !== 'ALL') {
    items = items.filter(d => {
      const top = (d.topic_ti + ' ' + d.topic_en + ' ' + (d.tags || '')).toLowerCase();
      if (filter === 'ANC') return top.includes('ጥንሲ') || top.includes('antenatal') || top.includes('anc');
      if (filter === 'PED') return top.includes('ህጻን') || top.includes('pediatric') || top.includes('ውጽኣት');
      if (filter === 'CHR') return top.includes('ኩላሊት') || top.includes('ሽኮር') || top.includes('ጸቕጢ');
      if (filter === 'INF') return top.includes('ዓሶ') || top.includes('malaria');
      return true;
    });
  }

  // Search filter
  if (search.trim()) {
    const s = search.toLowerCase();
    items = items.filter(d => {
      return (
        (d.id && d.id.toLowerCase().includes(s)) ||
        (d.topic_ti && d.topic_ti.toLowerCase().includes(s)) ||
        (d.topic_en && d.topic_en.toLowerCase().includes(s)) ||
        (d.caller_question_ti && d.caller_question_ti.toLowerCase().includes(s)) ||
        (d.doctor_answer_ti && d.doctor_answer_ti.toLowerCase().includes(s))
      );
    });
  }

  if (countEl) countEl.innerText = `${items.length} records`;

  let html = '';
  items.forEach(item => {
    const badgeClass = item.triage_level === 'CRITICAL' ? 'badge-emergency' : (item.triage_level === 'HIGH' ? 'badge-urgent' : 'badge-routine');
    html += `
      <tr>
        <td><code>${item.id}</code></td>
        <td><span class="preset-badge ${badgeClass}">${item.triage_level}</span></td>
        <td>
          <strong>${currentLang === 'ti' ? item.topic_ti : item.topic_en}</strong>
          <div style="font-size:0.75rem; color:#64748b;">${item.video_title || ''}</div>
        </td>
        <td>${item.caller_question_ti}</td>
        <td>${item.doctor_answer_ti.substring(0, 110)}...</td>
        <td>
          <a href="${item.video_url || 'https://www.youtube.com/watch?v=2FHD7FWWYNc'}" target="_blank" style="font-size:0.8rem; font-weight:700;">
            🎬 Watch Clip
          </a>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

function filterDataset(category) {
  currentFilter = category;
  document.querySelectorAll('.pill-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === category);
  });
  const searchVal = document.getElementById('datasetSearchInput')?.value || '';
  renderDatasetTable(currentFilter, searchVal);
}

function downloadDatasetCSV() {
  if (typeof DATASET === 'undefined' || !DATASET.length) return;

  const cols = ["id", "topic_ti", "topic_en", "video_id", "video_title", "video_url", "caller_question_ti", "caller_question_en", "doctor_answer_ti", "doctor_answer_en", "key_clinical_takeaways_ti", "danger_signs_ti", "triage_level", "tags"];
  let csvContent = "\uFEFF" + cols.join(",") + "\n";

  DATASET.forEach(row => {
    const line = cols.map(c => `"${(row[c] || '').replace(/"/g, '""')}"`).join(",");
    csvContent += line + "\n";
  });

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'medical_qa_dataset.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// ---------------------------------------------------------------------------
// Bilingual Switcher (Tigrinya / English)
// ---------------------------------------------------------------------------
function toggleLanguage() {
  currentLang = currentLang === 'ti' ? 'en' : 'ti';
  const btn = document.getElementById('langToggleBtn');
  if (btn) btn.innerText = currentLang === 'ti' ? '🌐 English' : '🌐 ትግርኛ';

  document.querySelectorAll('[data-ti][data-en]').forEach(el => {
    el.innerText = currentLang === 'ti' ? el.getAttribute('data-ti') : el.getAttribute('data-en');
  });

  renderDatasetTable(currentFilter, document.getElementById('datasetSearchInput')?.value || '');
}

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  renderDatasetTable();

  // Search Listener
  const searchInput = document.getElementById('datasetSearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      renderDatasetTable(currentFilter, e.target.value);
    });
  }

  // Check Backend Status
  fetch('http://127.0.0.1:8000/')
    .then(r => r.json())
    .then(data => {
      const badge = document.getElementById('gatewayStatusBadge');
      if (badge) {
        badge.innerHTML = `<span class="status-dot"></span> 2G Gateway Online (${data.knowledge_entries} records)`;
      }
    })
    .catch(() => {
      // Backend not running locally
    });
});
