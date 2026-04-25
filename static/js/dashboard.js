/* =================================================================
   dashboard.js  -  Smart Classroom Live Dashboard
   Connects to ws://localhost:8000/ws and drives all UI elements.
   ================================================================= */

const WS_URL = `ws://${location.hostname}:8000/ws`;

// ── DOM refs ──────────────────────────────────────────────────────
const statusDot    = document.getElementById('status-dot');
const statusLabel  = document.getElementById('status-label');
const cameraFeed   = document.getElementById('camera-feed');
const noFeedOverlay= document.getElementById('no-feed-overlay');
const facesEl      = document.getElementById('faces-count');
const engEl        = document.getElementById('engagement-val');
const motionEl     = document.getElementById('motion-val');
const tempEl       = document.getElementById('temp-val');
const humEl        = document.getElementById('hum-val');
const aqiEl        = document.getElementById('aqi-val');
const lightEl      = document.getElementById('light-val');
const envStatusEl  = document.getElementById('env-status');
const timerEl      = document.getElementById('timer-display');
const timerBar     = document.getElementById('timer-bar');
const timerMinInput= document.getElementById('timer-minutes');
const startBtn     = document.getElementById('btn-start-timer');
const stopBtn      = document.getElementById('btn-stop-timer');
const attendTable  = document.getElementById('attendance-tbody');
const pillPresent  = document.getElementById('pill-present');
const pillAbsent   = document.getElementById('pill-absent');
const pillLate     = document.getElementById('pill-late');
const ringFill     = document.getElementById('ring-fill');
const ringLabel    = document.getElementById('ring-label');
const tempBarEl    = document.getElementById('temp-bar');
const humBarEl     = document.getElementById('hum-bar');
const aqiBarEl     = document.getElementById('aqi-bar');
const lightBarEl   = document.getElementById('light-bar');

// ── SVG ring params ───────────────────────────────────────────────
const RING_R  = 44;
const CIRC    = 2 * Math.PI * RING_R;
ringFill.setAttribute('stroke-dasharray', CIRC);
ringFill.setAttribute('stroke-dashoffset', CIRC);

function setRing(pct) {
  const offset = CIRC - (pct / 100) * CIRC;
  ringFill.setAttribute('stroke-dashoffset', offset);
  ringLabel.textContent = `${pct}%`;
}

// ── Timer controls ────────────────────────────────────────────────
startBtn.addEventListener('click', async () => {
  const mins = parseInt(timerMinInput.value) || 5;
  try {
    await fetch('/api/timer/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ duration_minutes: mins })
    });
    showToast(`Attendance timer started for ${mins} min`, 'success');
  } catch (e) { showToast('Failed to start timer', 'error'); }
});

stopBtn.addEventListener('click', async () => {
  try {
    await fetch('/api/timer/stop', { method: 'POST' });
    showToast('Timer stopped', 'info');
  } catch (e) { showToast('Failed to stop timer', 'error'); }
});

// ── WebSocket ─────────────────────────────────────────────────────
let ws = null;
let reconnectDelay = 2000;
let feedAlive = false;

function connect() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    setOnline(true);
    reconnectDelay = 2000;
    if (!feedAlive) {
      noFeedOverlay.classList.remove('hidden');
    }
  };

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      handleFrame(data);
    } catch (e) { console.error('Parse error', e); }
  };

  ws.onerror = (e) => console.warn('WS error', e);

  ws.onclose = () => {
    setOnline(false);
    feedAlive = false;
    noFeedOverlay.classList.remove('hidden');
    setTimeout(connect, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 1.5, 15000);
  };
}

function handleFrame(data) {
  // ── Camera frame ──
  if (data.frame) {
    cameraFeed.src = `data:image/jpeg;base64,${data.frame}`;
    if (!feedAlive) {
      feedAlive = true;
      noFeedOverlay.classList.add('hidden');
    }
  }

  // ── Vision meta ──
  if (data.vision) {
    const v = data.vision;
    facesEl.textContent  = v.num_faces ?? 0;
    motionEl.textContent = (v.num_faces ?? 0) > 0 ? 'Detected' : 'None';
    const eng = v.average_engagement ?? 0;
    setRing(eng);

    // Attendance table
    if (v.roster_summary && Array.isArray(v.roster_summary)) {
      renderAttendance(v.roster_summary);
    }
  }

  // ── Sensors ──
  if (data.sensors) {
    const s = data.sensors;
    updateSensor('temp', s.temperature, '°C', 16, 35, tempEl, tempBarEl);
    updateSensor('hum',  s.humidity,    '%',  20, 80, humEl,  humBarEl);
    updateSensor('aqi',  s.aqi,         ' AQI', 10, 150, aqiEl,  aqiBarEl);
    updateSensor('light',s.light_level, ' lx', 100,1000, lightEl, lightBarEl);

    // Env status
    const status = s.status || 'Optimal';
    envStatusEl.textContent = `● Environment: ${status}`;
    envStatusEl.className = 'env-status' + (status === 'Warning' ? ' warning' : '');
  }

  // ── Timer ──
  if (data.timer) {
    const t = data.timer;
    updateTimer(t);
  }
}

function updateSensor(key, val, unit, min, max, el, barEl) {
  if (val == null) return;
  el.innerHTML = `${val}<span class="sensor-unit">${unit}</span>`;
  const pct = Math.max(0, Math.min(100, ((val - min) / (max - min)) * 100));
  barEl.style.width = `${pct}%`;

  // Color
  let cls = '';
  if (key === 'aqi'  && val > 100) cls = 'danger';
  else if (key === 'aqi' && val > 70) cls = 'warn';
  else if (key === 'temp' && val > 30) cls = 'warn';
  barEl.className = 'sensor-bar-fill' + (cls ? ' ' + cls : '');
}

function updateTimer(t) {
  const rem = t.remaining || 0;
  const dur  = t.duration  || 300;
  const mins = Math.floor(rem / 60);
  const secs = Math.floor(rem % 60);
  timerEl.textContent = `${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;

  const pct = dur > 0 ? (rem / dur) * 100 : 0;
  timerBar.style.width = `${pct}%`;

  timerEl.className = 'timer-display' + (t.running ? ' running' : (rem === 0 ? ' expired' : ''));
}

function renderAttendance(roster) {
  let present = 0, absent = 0, late = 0;

  if (roster.length === 0) {
    attendTable.innerHTML = `<tr class="empty-row"><td colspan="5">No students registered yet. <a href="/register" style="color:var(--accent)">Register a student →</a></td></tr>`;
    pillPresent.textContent = `Present: 0`;
    pillAbsent.textContent  = `Absent: 0`;
    pillLate.textContent    = `Late: 0`;
    return;
  }

  const rows = roster.map(s => {
    const status = (s.status || 'Absent').toLowerCase();
    if (status === 'present') present++;
    else if (status === 'late') late++;
    else absent++;

    const dist = s.distraction_score || 0;
    const distPct = Math.min(100, dist * 5);
    const distColor = dist > 10 ? 'var(--red)' : dist > 3 ? 'var(--amber)' : 'var(--green)';
    const name = (s.name || 'Unknown').replace(/_/g, ' ');
    const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0,2);

    return `<tr>
      <td>
        <div style="display:flex;align-items:center;gap:10px">
          <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));
               display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:700;color:#fff;flex-shrink:0">
            ${initials}
          </div>
          <span style="font-weight:500">${name}</span>
        </div>
      </td>
      <td><span class="status-badge ${status}">${s.status || 'Absent'}</span></td>
      <td style="font-family:var(--mono);font-size:.8rem;color:var(--text-2)">${s.check_in_time || '--:--'}</td>
      <td>
        <div class="distraction-bar">
          <div class="distraction-track">
            <div class="distraction-fill" style="width:${distPct}%;background:${distColor}"></div>
          </div>
          <span class="distraction-val">${dist}</span>
        </div>
      </td>
    </tr>`;
  });

  attendTable.innerHTML = rows.join('');
  pillPresent.textContent = `Present: ${present}`;
  pillAbsent.textContent  = `Absent: ${absent}`;
  pillLate.textContent    = `Late: ${late}`;
}

function setOnline(online) {
  statusDot.className   = 'status-dot' + (online ? ' online' : '');
  statusLabel.textContent = online ? 'Live' : 'Disconnected';
}

// ── Toast notifications ───────────────────────────────────────────
function showToast(msg, type='info') {
  const container = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${msg}</span>`;
  container.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .4s'; setTimeout(() => t.remove(), 400); }, 3000);
}

// ── Boot ─────────────────────────────────────────────────────────
connect();
