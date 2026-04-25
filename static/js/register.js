/* =================================================================
   register.js  -  Student Registration Page
   Handles webcam capture and form submission to /api/register
   ================================================================= */

const video = document.getElementById('webcam-preview');
const canvas = document.getElementById('capture-canvas');
const captureBtn = document.getElementById('btn-capture');
const retakeBtn = document.getElementById('btn-retake');
const statusEl = document.getElementById('capture-status');
const submitBtn = document.getElementById('btn-submit');
const form = document.getElementById('register-form');
const captureOverlay = document.getElementById('capture-overlay');
const captureFlash = document.getElementById('capture-flash');

let stream = null;
let capturedImageB64 = null;
const WS_URL = `ws://${location.hostname}:8000/ws`;
let ws = null;

// ─── Helper: show / hide overlay ─────────────────────────────────
function showOverlay(html) {
    captureOverlay.innerHTML = html;
    captureOverlay.style.display = 'flex';
    captureOverlay.style.opacity = '1';
}
function hideOverlay() {
    captureOverlay.style.opacity = '0';
    captureOverlay.style.pointerEvents = 'none';
    setTimeout(() => { captureOverlay.style.display = 'none'; }, 320);
}

// ─── Start webcam ─────────────────────────────────────────────────
async function startWebcam() {
    showOverlay(`
    <div class="webcam-icon-wrap">
      <svg viewBox="0 0 120 120" width="110" height="110" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="54" fill="none" stroke="url(#r1)" stroke-width="6" opacity="0.9"/>
        <circle cx="60" cy="60" r="46" fill="none" stroke="url(#r2)" stroke-width="5" opacity="0.85"/>
        <circle cx="60" cy="60" r="38" fill="none" stroke="url(#r3)" stroke-width="4" opacity="0.8"/>
        <circle cx="60" cy="60" r="29" fill="#111827"/>
        <circle cx="60" cy="60" r="26" fill="#0f172a" stroke="rgba(99,179,237,0.3)" stroke-width="1.5"/>
        <circle cx="60" cy="60" r="18" fill="url(#lens-grad)"/>
        <circle cx="60" cy="60" r="12" fill="url(#shine-grad)"/>
        <circle cx="60" cy="60" r="5"  fill="#000"/>
        <circle cx="54" cy="54" r="2.5" fill="rgba(255,255,255,0.7)"/>
        <rect x="48" y="108" width="24" height="5" rx="2.5" fill="rgba(100,116,139,0.6)"/>
        <rect x="57" y="113" width="6"  height="4" rx="1"   fill="rgba(100,116,139,0.5)"/>
        <defs>
          <linearGradient id="r1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%"   stop-color="#ef4444"/>
            <stop offset="33%"  stop-color="#f59e0b"/>
            <stop offset="66%"  stop-color="#22c55e"/>
            <stop offset="100%" stop-color="#3b82f6"/>
          </linearGradient>
          <linearGradient id="r2" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%"   stop-color="#8b5cf6"/>
            <stop offset="50%"  stop-color="#06b6d4"/>
            <stop offset="100%" stop-color="#f59e0b"/>
          </linearGradient>
          <linearGradient id="r3" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%"   stop-color="#3b82f6"/>
            <stop offset="100%" stop-color="#ec4899"/>
          </linearGradient>
          <radialGradient id="lens-grad" cx="40%" cy="40%">
            <stop offset="0%"   stop-color="#1e3a5f"/>
            <stop offset="100%" stop-color="#0a1628"/>
          </radialGradient>
          <radialGradient id="shine-grad" cx="35%" cy="35%">
            <stop offset="0%"   stop-color="#2563eb" stop-opacity="0.7"/>
            <stop offset="100%" stop-color="#0a1628" stop-opacity="0"/>
          </radialGradient>
        </defs>
      </svg>
    </div>
    <span class="webcam-icon-label">Starting camera…</span>
  `);

    try {
        ws = new WebSocket(WS_URL);
        
        ws.onmessage = (evt) => {
            try {
                const data = JSON.parse(evt.data);
                if (data.frame) {
                    video.src = `data:image/jpeg;base64,${data.frame}`;
                    stream = true; // Mark as available
                    if (captureOverlay.style.display !== 'none') {
                        hideOverlay();
                    }
                }
            } catch(e) {}
        };
        
        ws.onerror = () => {
            showOverlay(`
              <div style="font-size:2rem">🚫</div>
              <div style="font-size:.82rem;color:var(--red);font-weight:600">Camera access denied</div>
              <div style="font-size:.75rem;color:var(--text-3);text-align:center;max-width:180px">
                Ensure backend server is running and reload
              </div>
            `);
            statusEl.textContent = '⚠ Camera feed unavailable';
            statusEl.className = 'capture-status fail';
        };

        // Fallback: hide after 2s regardless
        setTimeout(() => {
            if (captureOverlay.style.display !== 'none') {
                hideOverlay();
            }
        }, 2000);

    } catch (err) {
        console.error('Camera error:', err);
    }
}

// ─── Capture photo ────────────────────────────────────────────────
captureBtn.addEventListener('click', () => {
    if (!stream) {
        showToast('Camera not available — please allow access', 'error');
        return;
    }

    // Since we are using an img element now, we can just use its natural size
    canvas.width = video.naturalWidth || 640;
    canvas.height = video.naturalHeight || 480;
    const ctx = canvas.getContext('2d');

    // Mirror to match the preview (which is CSS-flipped)
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0);

    capturedImageB64 = canvas.toDataURL('image/jpeg', 0.92);

    // Flash animation
    captureFlash.classList.add('flash');
    setTimeout(() => captureFlash.classList.remove('flash'), 400);

    // Freeze preview: hide video, show canvas
    video.style.display = 'none';
    canvas.style.display = 'block';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.objectFit = 'cover';
    canvas.style.transform = 'none'; // canvas already mirrored above

    captureBtn.disabled = true;
    retakeBtn.style.display = '';
    statusEl.textContent = '✓ Face captured — ready to submit';
    statusEl.className = 'capture-status ok';
});

// ─── Retake ───────────────────────────────────────────────────────
retakeBtn.addEventListener('click', () => {
    capturedImageB64 = null;
    canvas.style.display = 'none';
    video.style.display = '';
    captureBtn.disabled = false;
    retakeBtn.style.display = 'none';
    statusEl.textContent = '';
    statusEl.className = 'capture-status';
});

// ─── Submit form ──────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!capturedImageB64) {
        showToast('Please capture a face photo first', 'error');
        statusEl.textContent = '⚠ Please capture your face first';
        statusEl.className = 'capture-status fail';
        return;
    }

    const payload = {
        firstName: document.getElementById('first-name').value.trim(),
        lastName: document.getElementById('last-name').value.trim(),
        studentId: document.getElementById('student-id').value.trim(),
        email: document.getElementById('email').value.trim(),
        phone: document.getElementById('phone').value.trim(),
        course: document.getElementById('course').value,
        image: capturedImageB64
    };

    if (!payload.firstName || !payload.studentId) {
        showToast('First name and Student ID are required', 'error');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Registering…';

    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const json = await res.json();

        if (res.ok && json.status === 'success') {
            showToast(json.message || 'Student registered!', 'success');
            statusEl.textContent = '✓ ' + (json.message || 'Student registered successfully');
            statusEl.className = 'capture-status ok';
            form.reset();
            retakeBtn.click();
            setTimeout(() => { window.location.href = '/'; }, 2500);
        } else {
            showToast(json.message || 'Registration failed', 'error');
            statusEl.textContent = '✗ ' + (json.message || 'Error');
            statusEl.className = 'capture-status fail';
        }
    } catch (err) {
        showToast('Network error — is the server running?', 'error');
        statusEl.textContent = '✗ Network error';
        statusEl.className = 'capture-status fail';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '✅ Register Student';
    }
});

// ─── Toast ────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<span>${msg}</span>`;
    container.appendChild(t);
    setTimeout(() => {
        t.style.opacity = '0';
        t.style.transition = 'opacity .4s';
        setTimeout(() => t.remove(), 400);
    }, 3500);
}

// ─── Boot ─────────────────────────────────────────────────────────
retakeBtn.style.display = 'none';
startWebcam();
