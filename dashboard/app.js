/* ============================================================
   ExecutiveAI Dashboard — app.js
   Connects to the ADK REST API at http://127.0.0.1:8000
   ============================================================ */

const ADK_BASE   = '';          // same origin — dashboard served from port 8000
const APP_NAME   = 'executive_ai';
const USER_ID    = 'ceo-user';

let sessionId    = null;
let isProcessing = false;
let selectedAgent = 'SQL_AGENT';

// ── DOM refs ─────────────────────────────────────────────────
const chatArea      = document.getElementById('chatArea');
const messages      = document.getElementById('messages');
const welcome       = document.getElementById('welcome');
const queryInput    = document.getElementById('queryInput');
const sendBtn       = document.getElementById('sendBtn');
const sessionDot    = document.getElementById('sessionDot');
const sessionText   = document.getElementById('sessionText');
const newChatBtn    = document.getElementById('newChatBtn');
const sidebar       = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const statusBadge   = document.getElementById('statusBadge');
const statusLabel   = document.getElementById('statusLabel');
const agentTabs     = document.querySelectorAll('.agent-tab');

// ── Session Management ────────────────────────────────────────

async function createSession() {
  setStatus('connecting');
  try {
    const res = await fetch(
      `${ADK_BASE}/apps/${APP_NAME}/users/${USER_ID}/sessions`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    sessionId = data.id || data.session_id || data.sessionId;
    if (!sessionId) throw new Error('No session ID in response');
    setStatus('connected', sessionId);
    return sessionId;
  } catch (err) {
    setStatus('error', err.message);
    throw err;
  }
}

function setStatus(state, detail) {
  if (state === 'connecting') {
    sessionDot.className = 'session-dot';
    sessionText.textContent = 'Connecting…';
    statusBadge.style.color = 'var(--warning)';
    statusLabel.textContent = 'Connecting';
  } else if (state === 'connected') {
    sessionDot.className = 'session-dot connected';
    sessionText.textContent = `Session active`;
    statusBadge.style.color = 'var(--success)';
    statusLabel.textContent = 'Live';
  } else if (state === 'error') {
    sessionDot.className = 'session-dot error';
    sessionText.textContent = 'Not connected';
    statusBadge.style.color = 'var(--danger)';
    statusLabel.textContent = 'Offline';
  }
}

// ── Send Message ──────────────────────────────────────────────

async function sendMessage(question) {
  if (isProcessing || !question.trim()) return;
  if (!sessionId) {
    try { await createSession(); } catch { return; }
  }

  isProcessing = true;
  sendBtn.disabled = true;
  queryInput.value = '';
  autoResize(queryInput);

  // Hide welcome screen
  if (welcome.style.display !== 'none') {
    welcome.style.opacity = '0';
    welcome.style.transition = 'opacity 0.3s';
    setTimeout(() => { welcome.style.display = 'none'; }, 300);
  }

  // Add user bubble
  appendMessage('user', question);

  // Add typing indicator
  const typingEl = appendTyping();

  try {
    const body = {
      app_name: APP_NAME,
      user_id: USER_ID,
      session_id: sessionId,
      new_message: {
        role: 'user',
        parts: [{ text: `[${selectedAgent}] ${question}` }]
      }
    };

    const res = await fetch(`${ADK_BASE}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Server error ${res.status}: ${errText}`);
    }

    const events = await res.json();
    typingEl.remove();

    // Find the final model text response
    const finalText = extractFinalResponse(events);
    appendMessage('assistant', finalText);

  } catch (err) {
    typingEl.remove();
    appendError(err.message);
  } finally {
    isProcessing = false;
    sendBtn.disabled = false;
    queryInput.focus();
  }
}

// ── Response Extraction ───────────────────────────────────────

function extractFinalResponse(events) {
  if (!Array.isArray(events)) {
    return formatResponseText(JSON.stringify(events, null, 2));
  }

  // Collect all model text parts in order
  let parts = [];
  for (const event of events) {
    // ADK event format: { author, content: { parts: [{text}] } }
    const content = event.content || event.message || {};
    const author   = event.author || '';
    if (author === 'user') continue;

    const eventParts = content.parts || content.text
      ? [{ text: content.text }]
      : [];

    for (const part of (content.parts || [])) {
      if (part.text) parts.push(part.text);
    }
  }

  if (parts.length === 0) return 'No response received from the agent.';
  return parts.join('\n').trim();
}

// ── Message Rendering ─────────────────────────────────────────

function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = `message ${role}`;

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'You' : 'ExecutiveAI';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = formatResponseText(text);

  div.appendChild(label);
  div.appendChild(bubble);
  messages.appendChild(div);
  scrollToBottom();
  return div;
}

function appendTyping() {
  const div = document.createElement('div');
  div.className = 'message assistant';

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = 'ExecutiveAI';

  const indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.innerHTML = `
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  `;

  div.appendChild(label);
  div.appendChild(indicator);
  messages.appendChild(div);
  scrollToBottom();
  return div;
}

function appendError(message) {
  const div = document.createElement('div');
  div.className = 'message assistant';

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = 'ExecutiveAI';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = `
    <div class="error-block">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;margin-top:1px"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      <span>${escHtml(message)}</span>
    </div>
  `;

  div.appendChild(label);
  div.appendChild(bubble);
  messages.appendChild(div);
  scrollToBottom();
}

// ── Text Formatting ───────────────────────────────────────────

function formatResponseText(text) {
  if (!text) return '';

  // Detect embedded JSON result block
  const jsonMatch = text.match(/```json\s*([\s\S]+?)\s*```/);
  if (jsonMatch) {
    try {
      const json = JSON.parse(jsonMatch[1]);
      const before = text.slice(0, jsonMatch.index).trim();
      const after  = text.slice(jsonMatch.index + jsonMatch[0].length).trim();
      return (before ? `<p>${mdToHtml(before)}</p>` : '') +
             renderTable(json) +
             (after ? `<p>${mdToHtml(after)}</p>` : '');
    } catch (_) { /* fall through */ }
  }

  // Check if the entire text is JSON with rows
  if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
    try {
      const json = JSON.parse(text.trim());
      if (json.rows || (Array.isArray(json) && json.length > 0 && typeof json[0] === 'object')) {
        return renderTable(json);
      }
    } catch (_) { /* fall through */ }
  }

  return mdToHtml(text);
}

function mdToHtml(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code style="background:var(--bg-hover);padding:1px 5px;border-radius:4px;font-size:12px">$1</code>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^/, '<p>').replace(/$/, '</p>');
}

function renderTable(data) {
  // Normalise: accept {rows, columns} or raw array
  let rows = [];
  let columns = [];

  if (data && data.rows && Array.isArray(data.rows)) {
    rows    = data.rows;
    columns = data.columns || (rows.length ? Object.keys(rows[0]) : []);
  } else if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'object') {
    rows    = data;
    columns = Object.keys(data[0]);
  } else {
    return `<pre style="font-size:12px;color:var(--text-2);white-space:pre-wrap">${escHtml(JSON.stringify(data,null,2))}</pre>`;
  }

  if (rows.length === 0) return '<p><em>No data returned.</em></p>';

  const rowCount = data.row_count || rows.length;

  const headerCells = columns.map(col =>
    `<th>${escHtml(col.replace(/_/g,' '))}</th>`
  ).join('');

  const bodyRows = rows.map(row => {
    const cells = columns.map(col => {
      const val = row[col];
      const isNum = typeof val === 'number' ||
                    (typeof val === 'string' && !isNaN(parseFloat(val)) && !/^\d{4}-\d{2}/.test(val));
      const display = formatCellValue(val, col);
      return `<td class="${isNum ? 'num' : ''}">${display}</td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');

  return `
    <div class="result-block">
      <div class="result-header">
        <span class="result-title">Query Results</span>
        <span class="result-count">${rowCount} row${rowCount !== 1 ? 's' : ''}</span>
      </div>
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr>${headerCells}</tr></thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>
    </div>
  `;
}

function formatCellValue(val, col) {
  if (val === null || val === undefined) return '<span style="color:var(--text-3)">—</span>';
  const colUp = col.toUpperCase();

  // Currency columns
  if (['AMOUNT','REVENUE','ARR','MRR','VALUE','PRICE','COST','BUDGET','PIPELINE'].some(k => colUp.includes(k))) {
    const n = parseFloat(val);
    if (!isNaN(n)) return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  // Percentage columns
  if (['RATE','PCT','PERCENT','SCORE'].some(k => colUp.includes(k))) {
    const n = parseFloat(val);
    if (!isNaN(n) && n <= 100) return n.toFixed(1) + '%';
  }

  // Date strings — format nicely
  if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}/.test(val)) {
    return new Date(val + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  // Large numbers
  if (typeof val === 'number' && val > 999) {
    return val.toLocaleString('en-US');
  }

  return escHtml(String(val));
}

function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// ── UI Helpers ────────────────────────────────────────────────

function scrollToBottom() {
  chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'smooth' });
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

// ── Event Listeners ───────────────────────────────────────────

queryInput.addEventListener('input', () => {
  autoResize(queryInput);
  sendBtn.disabled = queryInput.value.trim().length === 0 || isProcessing;
});

queryInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendBtn.disabled) sendMessage(queryInput.value.trim());
  }
});

sendBtn.addEventListener('click', () => {
  sendMessage(queryInput.value.trim());
});

newChatBtn.addEventListener('click', async () => {
  messages.innerHTML = '';
  welcome.style.display = 'flex';
  welcome.style.opacity = '1';
  sessionId = null;
  try { await createSession(); } catch(_) {}
});

sidebarToggle.addEventListener('click', () => {
  sidebar.classList.toggle('collapsed');
});

mobileMenuBtn.addEventListener('click', () => {
  sidebar.classList.toggle('open');
});

// Quick action buttons
document.querySelectorAll('.quick-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const q = btn.dataset.question;
    if (q) {
      queryInput.value = q;
      autoResize(queryInput);
      sendBtn.disabled = false;
      sendMessage(q);
      // Close mobile sidebar
      sidebar.classList.remove('open');
    }
  });
});

// Suggestion pills
document.querySelectorAll('.suggest-pill').forEach(pill => {
  pill.addEventListener('click', () => {
    const q = pill.dataset.question;
    if (q) {
      queryInput.value = q;
      autoResize(queryInput);
      sendBtn.disabled = false;
      sendMessage(q);
    }
  });
});

// Agent Tabs
agentTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    agentTabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    selectedAgent = tab.dataset.agent;
  });
});

// ── Init ──────────────────────────────────────────────────────

(async function init() {
  try {
    await createSession();
    queryInput.focus();
  } catch (err) {
    console.warn('Could not connect to ADK server:', err.message);
    appendError('Could not connect to the ExecutiveAI server. Make sure it is running: adk web executive_ai');
    if (welcome) {
      welcome.style.display = 'none';
    }
  }
})();
