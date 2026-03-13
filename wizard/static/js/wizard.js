/**
 * DoNotes Setup Wizard — Client-side logic
 */

const TOTAL_STEPS = 9;
let currentStep = 1;

// Collected configuration data
const stepData = {
    telegram_bot_token: '',
    telegram_user_id: 0,
    openai_api_key: '',
    openai_model: 'gpt-4o',
    gmail_sender_email: '',
    gmail_recipient_email: '',
    work_calendar_id: '',
    personal_calendar_id: '',
    timezone: 'UTC',
    user_name: '',
    user_profile_context: '',
    self_names: [],
    known_people: [],
    whisper_places: [],
    whisper_companies: [],
};

// Tag data for personalization lists
const tagData = {
    'known-people': [],
    'whisper-places': [],
    'whisper-companies': [],
};


// ========================================================================
// Step Navigation
// ========================================================================

function showStep(n) {
    if (n < 1 || n > TOTAL_STEPS) return;

    document.querySelectorAll('.step').forEach(s => s.style.display = 'none');
    const target = document.querySelector(`[data-step="${n}"]`);
    if (target) {
        target.style.display = 'block';
        currentStep = n;
        updateProgressBar();

        // Load timezones when step 7 is shown
        if (n === 7) loadTimezones();
        // Build review when step 9 is shown
        if (n === 9) buildReview();
        // Check OAuth status when step 6 is shown
        if (n === 6) checkOAuthStatus();
    }
}

function nextStep() {
    // Collect data from current step before advancing
    collectStepData(currentStep);
    showStep(currentStep + 1);
}

function prevStep() {
    collectStepData(currentStep);
    showStep(currentStep - 1);
}

function updateProgressBar() {
    // Update fill width
    const pct = (currentStep / TOTAL_STEPS) * 100;
    document.getElementById('progress-fill').style.width = pct + '%';

    // Update step dots
    document.querySelectorAll('.step-dot').forEach(dot => {
        const s = parseInt(dot.dataset.step);
        dot.classList.remove('active', 'completed');
        if (s === currentStep) {
            dot.classList.add('active');
        } else if (s < currentStep) {
            dot.classList.add('completed');
        }
    });
}

// Allow clicking step dots to navigate (only to completed steps)
document.querySelectorAll('.step-dot').forEach(dot => {
    dot.addEventListener('click', () => {
        const s = parseInt(dot.dataset.step);
        if (s <= currentStep) {
            collectStepData(currentStep);
            showStep(s);
        }
    });
});


// ========================================================================
// Data Collection
// ========================================================================

function collectStepData(step) {
    switch(step) {
        case 2:
            stepData.telegram_bot_token = val('telegram_token');
            stepData.telegram_user_id = parseInt(val('telegram_user_id')) || 0;
            break;
        case 3:
            stepData.openai_api_key = val('openai_key');
            break;
        case 7:
            stepData.user_name = val('user_name');
            stepData.gmail_sender_email = val('gmail_sender');
            stepData.gmail_recipient_email = val('gmail_recipient') || val('gmail_sender');
            stepData.work_calendar_id = val('work_calendar') || val('gmail_sender');
            stepData.personal_calendar_id = val('personal_calendar') || val('gmail_sender');
            stepData.timezone = val('timezone') || 'UTC';
            break;
        case 8:
            stepData.user_profile_context = val('profile_context');
            stepData.known_people = [...tagData['known-people']];
            stepData.whisper_places = [...tagData['whisper-places']];
            stepData.whisper_companies = [...tagData['whisper-companies']];
            break;
    }
}

function val(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
}


// ========================================================================
// Telegram Validation
// ========================================================================

async function validateTelegram() {
    const token = val('telegram_token');
    const userId = parseInt(val('telegram_user_id'));
    const statusEl = document.getElementById('telegram-status');
    const btn = document.getElementById('btn-validate-telegram');

    if (!token || !userId) {
        setStatus(statusEl, 'error', 'Please fill in both the bot token and your user ID');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Validating...';
    setStatus(statusEl, 'pending', 'Checking with Telegram...');

    try {
        const resp = await fetch('/api/validate/telegram', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({bot_token: token, user_id: userId}),
        });
        const data = await resp.json();

        if (data.valid) {
            setStatus(statusEl, 'success', data.message);
            document.getElementById('step2-next').disabled = false;
            stepData.telegram_bot_token = token;
            stepData.telegram_user_id = userId;
        } else {
            setStatus(statusEl, 'error', data.message);
        }
    } catch (e) {
        setStatus(statusEl, 'error', 'Network error — check your connection');
    }

    btn.disabled = false;
    btn.textContent = 'Validate';
}


// ========================================================================
// OpenAI Validation
// ========================================================================

async function validateOpenAI() {
    const key = val('openai_key');
    const statusEl = document.getElementById('openai-status');
    const btn = document.getElementById('btn-validate-openai');

    if (!key) {
        setStatus(statusEl, 'error', 'Please enter your API key');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Validating...';
    setStatus(statusEl, 'pending', 'Checking with OpenAI...');

    try {
        const resp = await fetch('/api/validate/openai', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({api_key: key}),
        });
        const data = await resp.json();

        if (data.valid) {
            setStatus(statusEl, 'success', data.message);
            document.getElementById('step3-next').disabled = false;
            stepData.openai_api_key = key;
        } else {
            setStatus(statusEl, 'error', data.message);
        }
    } catch (e) {
        setStatus(statusEl, 'error', 'Network error — check your connection');
    }

    btn.disabled = false;
    btn.textContent = 'Validate';
}


// ========================================================================
// Google Credentials Upload
// ========================================================================

async function uploadCredentials() {
    const fileInput = document.getElementById('credentials_file');
    const statusEl = document.getElementById('credentials-status');
    const dropZone = document.getElementById('drop-zone');

    if (!fileInput.files.length) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    setStatus(statusEl, 'pending', 'Uploading and validating...');

    try {
        const resp = await fetch('/api/upload/google-credentials', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();

        if (data.valid) {
            setStatus(statusEl, 'success', data.message);
            dropZone.classList.add('uploaded');
            document.querySelector('.upload-content').innerHTML =
                '<div class="upload-icon">&#9989;</div><p><strong>credentials.json</strong> uploaded!</p>';
            document.getElementById('step5-next').disabled = false;
        } else {
            setStatus(statusEl, 'error', data.message);
        }
    } catch (e) {
        setStatus(statusEl, 'error', 'Upload failed — try again');
    }
}

// Drag and drop
const dropZone = document.getElementById('drop-zone');
if (dropZone) {
    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, e => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
    });
    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, e => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });
    });
    dropZone.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        if (files.length) {
            document.getElementById('credentials_file').files = files;
            uploadCredentials();
        }
    });
}


// ========================================================================
// Google OAuth
// ========================================================================

async function checkOAuthStatus() {
    const statusEl = document.getElementById('oauth-status');
    try {
        const resp = await fetch('/api/oauth/status');
        const data = await resp.json();
        if (data.authorized) {
            setStatus(statusEl, 'success', 'Google access authorized!');
            document.getElementById('step6-next').disabled = false;
            document.getElementById('btn-oauth').style.display = 'none';
        }
    } catch (e) {
        // Silently fail — user hasn't authorized yet
    }
}


// ========================================================================
// Timezones
// ========================================================================

let timezonesLoaded = false;

async function loadTimezones() {
    if (timezonesLoaded) return;

    try {
        const resp = await fetch('/api/timezones');
        const data = await resp.json();

        const select = document.getElementById('timezone');
        select.innerHTML = '';

        // Common timezones group
        const commonGroup = document.createElement('optgroup');
        commonGroup.label = 'Common';
        data.common.forEach(tz => {
            const opt = document.createElement('option');
            opt.value = tz;
            opt.textContent = tz;
            commonGroup.appendChild(opt);
        });
        select.appendChild(commonGroup);

        // All timezones group
        const allGroup = document.createElement('optgroup');
        allGroup.label = 'All Timezones';
        data.all.forEach(tz => {
            const opt = document.createElement('option');
            opt.value = tz;
            opt.textContent = tz;
            allGroup.appendChild(opt);
        });
        select.appendChild(allGroup);

        // Try to detect user's timezone
        const guess = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (guess) {
            select.value = guess;
        }

        timezonesLoaded = true;
    } catch (e) {
        console.error('Failed to load timezones:', e);
    }
}


// ========================================================================
// Gmail Auto-fill
// ========================================================================

function autofillGmail() {
    const sender = val('gmail_sender');
    const recipientField = document.getElementById('gmail_recipient');
    const personalField = document.getElementById('personal_calendar');

    if (recipientField && !recipientField.value) {
        recipientField.value = sender;
    }
    if (personalField && !personalField.value) {
        personalField.value = sender;
    }
}


// ========================================================================
// Config Validation (Step 7)
// ========================================================================

function validateConfig() {
    const name = val('user_name');
    const email = val('gmail_sender');

    if (!name) {
        alert('Please enter your name');
        return false;
    }
    if (!email || !email.includes('@')) {
        alert('Please enter a valid Gmail address');
        return false;
    }

    collectStepData(7);
    return true;
}


// ========================================================================
// Tag Lists (Personalization)
// ========================================================================

function addTag(listId) {
    const input = document.getElementById(listId + '-input');
    const value = input.value.trim();
    if (!value) return;

    tagData[listId].push(value);
    input.value = '';
    renderTags(listId);
}

function removeTag(listId, index) {
    tagData[listId].splice(index, 1);
    renderTags(listId);
}

function renderTags(listId) {
    const container = document.getElementById(listId + '-list');
    container.innerHTML = tagData[listId].map((tag, i) =>
        `<span class="tag">${escapeHtml(tag)} <span class="remove-tag" onclick="removeTag('${listId}', ${i})">&times;</span></span>`
    ).join('');
}


// ========================================================================
// Review (Step 9)
// ========================================================================

function buildReview() {
    collectStepData(currentStep);

    const summary = document.getElementById('review-summary');
    const mask = s => s ? s.slice(0, 6) + '...' + s.slice(-4) : '(not set)';

    const rows = [
        ['Telegram Bot Token', mask(stepData.telegram_bot_token)],
        ['Telegram User ID', stepData.telegram_user_id || '(not set)'],
        ['OpenAI API Key', mask(stepData.openai_api_key)],
        ['Gmail Address', stepData.gmail_sender_email || '(not set)'],
        ['Digest Recipient', stepData.gmail_recipient_email || stepData.gmail_sender_email || '(not set)'],
        ['Work Calendar', stepData.work_calendar_id || '(not set)'],
        ['Personal Calendar', stepData.personal_calendar_id || '(not set)'],
        ['Timezone', stepData.timezone || 'UTC'],
        ['Name', stepData.user_name || '(not set)'],
    ];

    if (stepData.known_people.length) {
        rows.push(['People', stepData.known_people.join(', ')]);
    }
    if (stepData.whisper_places.length) {
        rows.push(['Places', stepData.whisper_places.join(', ')]);
    }

    summary.innerHTML = rows.map(([label, value]) =>
        `<div class="review-row">
            <span class="review-label">${label}</span>
            <span class="review-value">${escapeHtml(String(value))}</span>
        </div>`
    ).join('');
}


// ========================================================================
// Save & Launch
// ========================================================================

async function saveAndLaunch() {
    collectStepData(8); // Collect personalization data
    collectStepData(7); // Collect config data

    const statusEl = document.getElementById('launch-status');
    const btn = document.getElementById('btn-launch');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving configuration...';
    setStatus(statusEl, 'pending', 'Writing .env and user_profile.py...');

    try {
        // Save config
        const saveResp = await fetch('/api/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(stepData),
        });
        const saveResult = await saveResp.json();

        if (!saveResult.success) {
            setStatus(statusEl, 'error', 'Save failed: ' + (saveResult.error || 'Unknown error'));
            btn.disabled = false;
            btn.textContent = 'Save Configuration & Start DoNotes';
            return;
        }

        setStatus(statusEl, 'pending', 'Starting DoNotes bot...');
        btn.innerHTML = '<span class="spinner"></span> Starting bot...';

        // Launch bot
        const launchResp = await fetch('/api/launch', {method: 'POST'});
        const launchResult = await launchResp.json();

        if (launchResult.success) {
            setStatus(statusEl, 'success', launchResult.message + ' (PID: ' + launchResult.pid + ')');
            btn.style.display = 'none';
            document.getElementById('success-panel').style.display = 'block';
        } else {
            setStatus(statusEl, 'error', 'Launch failed: ' + (launchResult.error || 'Unknown error'));
            btn.disabled = false;
            btn.textContent = 'Save Configuration & Start DoNotes';
        }
    } catch (e) {
        setStatus(statusEl, 'error', 'Error: ' + e.message);
        btn.disabled = false;
        btn.textContent = 'Save Configuration & Start DoNotes';
    }
}


// ========================================================================
// Toggle Visibility (for password fields)
// ========================================================================

function toggleVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
    } else {
        input.type = 'password';
    }
}


// ========================================================================
// Utilities
// ========================================================================

function setStatus(el, type, message) {
    el.className = 'status-msg ' + type;
    el.textContent = message;
    el.style.display = 'block';
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}


// ========================================================================
// Init — Handle URL parameters (OAuth callback redirect)
// ========================================================================

window.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);

    // Handle OAuth redirect back
    if (params.has('step')) {
        const step = parseInt(params.get('step'));
        if (step >= 1 && step <= TOTAL_STEPS) {
            showStep(step);
        }
    }

    if (params.get('oauth') === 'success') {
        const statusEl = document.getElementById('oauth-status');
        setStatus(statusEl, 'success', 'Google access authorized!');
        document.getElementById('step6-next').disabled = false;
        const oauthBtn = document.getElementById('btn-oauth');
        if (oauthBtn) oauthBtn.style.display = 'none';
    } else if (params.get('oauth') === 'error') {
        const statusEl = document.getElementById('oauth-status');
        const msg = params.get('message') || 'Authorization failed';
        setStatus(statusEl, 'error', decodeURIComponent(msg.replace(/\+/g, ' ')));
    }

    // Clean URL
    if (params.toString()) {
        window.history.replaceState({}, '', '/');
    }

    // Check existing setup status
    checkExistingStatus();
});


async function checkExistingStatus() {
    try {
        const resp = await fetch('/api/status');
        const status = await resp.json();

        // If credentials exist, mark step 5 as done
        if (status.credentials_uploaded) {
            const dropZone = document.getElementById('drop-zone');
            if (dropZone) {
                dropZone.classList.add('uploaded');
                document.querySelector('.upload-content').innerHTML =
                    '<div class="upload-icon">&#9989;</div><p><strong>credentials.json</strong> already uploaded</p>';
                document.getElementById('step5-next').disabled = false;
            }
        }

        // If token exists, mark step 6 as done
        if (status.google_authorized) {
            const statusEl = document.getElementById('oauth-status');
            if (statusEl) {
                setStatus(statusEl, 'success', 'Google access already authorized!');
                document.getElementById('step6-next').disabled = false;
                const oauthBtn = document.getElementById('btn-oauth');
                if (oauthBtn) oauthBtn.style.display = 'none';
            }
        }
    } catch (e) {
        // Silently fail
    }
}
