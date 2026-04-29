// ── Router ──────────────────────────────────────────────────────────────────
const views = ['planner', 'recipes', 'shopping', 'settings'];

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

// ── View stubs (filled in subsequent tasks) ─────────────────────────────────
function renderPlanner() {
  document.getElementById('view-planner').innerHTML = '<p>Planner loading...</p>';
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
