// ── Router ──────────────────────────────────────────────────────────────────
const views = ['planner', 'recipes', 'shopping', 'settings'];
const state = { currentWeekId: null, weeks: [], recipes: [] };

function navigate(viewName) {
  views.forEach(v => {
    document.getElementById(`view-${v}`).classList.toggle('active', v === viewName);
    document.querySelector(`.nav-tab[data-view="${v}"]`).classList.toggle('active', v === viewName);
  });
  if (viewName === 'planner') renderPlanner();
  if (viewName === 'recipes') renderRecipes();
  if (viewName === 'shopping') renderShopping();
  if (viewName === 'settings') renderSettings();
}

document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => navigate(tab.dataset.view));
});

// ── API helpers ──────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const resp = await fetch(`/api${path}`, opts);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(err.error || `HTTP ${resp.status}`);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

function showError(msg) {
  const banner = document.getElementById('error-banner');
  banner.textContent = msg + ' (click to dismiss)';
  banner.classList.remove('hidden');
  banner.onclick = () => banner.classList.add('hidden');
}

// ── Modal ────────────────────────────────────────────────────────────────────
function openModal(html) {
  document.getElementById('modal-box').innerHTML = html;
  document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
});

// ── Planner view ─────────────────────────────────────────────────────────────
async function renderPlanner() {
  const el = document.getElementById('view-planner');
  el.innerHTML = '<p>Loading...</p>';
  try {
    state.weeks = await api('GET', '/weeks');
    state.recipes = await api('GET', '/recipes');
    if (state.weeks.length === 0) {
      el.innerHTML = plannerEmptyHTML();
      document.getElementById('btn-new-week').onclick = createNewWeek;
      return;
    }
    if (!state.currentWeekId) state.currentWeekId = state.weeks[0].id;
    const week = state.weeks.find(w => w.id === state.currentWeekId) || state.weeks[0];
    el.innerHTML = plannerHTML(week);
    bindPlannerEvents(week);
  } catch (e) { showError(e.message); }
}

function plannerEmptyHTML() {
  return `<div style="text-align:center;padding:3rem">
    <p style="margin-bottom:1rem;color:#666">No weeks yet.</p>
    <button class="btn btn-primary" id="btn-new-week">Create First Week</button>
  </div>`;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri'];
const MEAL_KEYS = ['lunch', 'dinner'];

function plannerHTML(week) {
  const weekLabel = new Date(week.week_start_date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const prevWeek = state.weeks.find(w => w.id < week.id);
  const nextWeek = state.weeks.find(w => w.id > week.id);

  let rows = '';
  MEAL_KEYS.forEach(meal => {
    rows += `<tr><th>${meal.charAt(0).toUpperCase() + meal.slice(1)}</th>`;
    DAY_KEYS.forEach(day => {
      const slotKey = `${day}_${meal}`;
      const val = week.slots[slotKey];
      rows += `<td class="planner-cell" data-slot="${slotKey}">${cellContent(val)}</td>`;
    });
    rows += '</tr>';
  });

  const sundayVal = week.slots['sunday_prep'];
  const sunday_synced = week.calendar_synced ? ' (synced)' : '';

  return `
    <div class="planner-header">
      <button class="btn btn-secondary btn-sm" id="btn-prev" ${!prevWeek ? 'disabled' : ''}>← Prev</button>
      <span class="week-label">Week of ${weekLabel}</span>
      <button class="btn btn-secondary btn-sm" id="btn-next" ${!nextWeek ? 'disabled' : ''}>Next →</button>
      <button class="btn btn-primary btn-sm" id="btn-new-week">+ New Week</button>
    </div>
    <table class="planner-grid">
      <thead><tr><th></th>${DAYS.map(d => `<th>${d}</th>`).join('')}</tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="planner-sunday">
      <strong>Sunday Prep:</strong>
      <span class="planner-cell" data-slot="sunday_prep">${cellContent(sundayVal)}</span>
    </div>
    <div class="planner-actions">
      <button class="btn btn-secondary" id="btn-suggest">Suggest</button>
      <button class="btn btn-secondary" id="btn-gen-shopping">Generate Shopping List</button>
      <button class="btn btn-secondary" id="btn-sync-cal">Sync to Calendar${sunday_synced}</button>
    </div>`;
}

function cellContent(val) {
  if (!val) return '<span class="cell-empty">—</span>';
  if (typeof val === 'string' && val.startsWith('leftover:')) return '<span class="cell-leftover">↩ Leftovers</span>';
  const recipe = state.recipes.find(r => r.id === (typeof val === 'string' ? parseInt(val) : val));
  if (!recipe) return '<span class="cell-empty">—</span>';
  const methods = (recipe.cook_method || []).join(', ');
  return `<span class="cell-recipe" title="${methods}">${recipe.name}</span>`;
}

function bindPlannerEvents(week) {
  document.getElementById('btn-prev')?.addEventListener('click', () => {
    const prev = state.weeks.find(w => w.id < week.id);
    if (prev) { state.currentWeekId = prev.id; renderPlanner(); }
  });
  document.getElementById('btn-next')?.addEventListener('click', () => {
    const next = state.weeks.find(w => w.id > week.id);
    if (next) { state.currentWeekId = next.id; renderPlanner(); }
  });
  document.getElementById('btn-new-week').addEventListener('click', createNewWeek);
  document.getElementById('btn-suggest').addEventListener('click', async () => {
    try {
      const updated = await api('POST', `/weeks/${week.id}/suggest`);
      state.currentWeekId = updated.id;
      renderPlanner();
    } catch (e) { showError(e.message); }
  });
  document.getElementById('btn-gen-shopping').addEventListener('click', async () => {
    try {
      await api('POST', `/weeks/${week.id}/shopping-list`);
      navigate('shopping');
    } catch (e) { showError(e.message); }
  });
  document.getElementById('btn-sync-cal').addEventListener('click', async () => {
    try {
      await api('POST', `/weeks/${week.id}/sync-calendar`);
      renderPlanner();
    } catch (e) { showError(e.message); }
  });
  document.querySelectorAll('.planner-cell[data-slot]').forEach(cell => {
    cell.addEventListener('click', () => openRecipePicker(week, cell.dataset.slot));
  });
}

async function createNewWeek() {
  const today = new Date();
  const dayOfWeek = today.getDay();
  const daysToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(today);
  monday.setDate(today.getDate() + daysToMonday);
  const iso = monday.toISOString().split('T')[0];
  try {
    const week = await api('POST', '/weeks', { week_start_date: iso });
    state.weeks.unshift(week);
    state.currentWeekId = week.id;
    renderPlanner();
  } catch (e) { showError(e.message); }
}

function openRecipePicker(week, slotKey) {
  const items = state.recipes.map(r =>
    `<div class="recipe-pick-item" data-id="${r.id}">${r.name} <small>${(r.cook_method||[]).join(', ')}</small></div>`
  ).join('') || '<p>No recipes in library yet.</p>';

  openModal(`
    <h3 style="margin-bottom:1rem">Pick a recipe for ${slotKey.replace('_', ' ')}</h3>
    <input id="picker-search" class="picker-search" placeholder="Search..." style="width:100%;margin-bottom:0.75rem;padding:0.4rem">
    <div id="picker-list">${items}</div>
    <button class="btn btn-secondary btn-sm" style="margin-top:0.75rem" id="btn-clear-slot">Clear slot</button>
  `);

  document.getElementById('picker-search').addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('.recipe-pick-item').forEach(el => {
      el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });

  document.querySelectorAll('.recipe-pick-item').forEach(el => {
    el.addEventListener('click', async () => {
      const newSlots = { ...week.slots, [slotKey]: parseInt(el.dataset.id) };
      try {
        await api('PUT', `/weeks/${week.id}`, { slots: newSlots });
        closeModal();
        renderPlanner();
      } catch (e) { showError(e.message); }
    });
  });

  document.getElementById('btn-clear-slot').addEventListener('click', async () => {
    const newSlots = { ...week.slots };
    delete newSlots[slotKey];
    try {
      await api('PUT', `/weeks/${week.id}`, { slots: newSlots });
      closeModal();
      renderPlanner();
    } catch (e) { showError(e.message); }
  });
}
function renderRecipes() {
  document.getElementById('view-recipes').innerHTML = '<p>Recipes loading...</p>';
}
function renderShopping() {
  document.getElementById('view-shopping').innerHTML = '<p>Shopping loading...</p>';
}
function renderSettings() {
  document.getElementById('view-settings').innerHTML = '<p>Settings loading...</p>';
}

// ── Init ─────────────────────────────────────────────────────────────────────
navigate('planner');
