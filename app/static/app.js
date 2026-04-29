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
  return `<div class="empty-state">
    <p>No weeks planned yet. Create your first week to get started.</p>
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
    <div class="modal-title">Pick a recipe — ${slotKey.replace(/_/g, ' ')}</div>
    <input id="picker-search" class="picker-search" type="search" placeholder="Search recipes…">
    <div id="picker-list">${items}</div>
    <button class="btn btn-ghost btn-sm" style="margin-top:0.75rem" id="btn-clear-slot">Clear slot</button>
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
// ── Recipe library view ──────────────────────────────────────────────────────
async function renderRecipes() {
  const el = document.getElementById('view-recipes');
  el.innerHTML = '<p>Loading...</p>';
  try {
    state.recipes = await api('GET', '/recipes');
    el.innerHTML = recipesHTML(state.recipes);
    bindRecipesEvents();
  } catch (e) { showError(e.message); }
}

function recipesHTML(recipes) {
  const rows = recipes.length === 0
    ? '<tr><td colspan="5" class="table-empty">No recipes yet. Add one above.</td></tr>'
    : recipes.map(r => `
      <tr>
        <td class="recipe-name-cell">${r.name}</td>
        <td>${(r.cook_method || []).map(m => `<span class="recipe-tag method">${m.replace('_',' ')}</span>`).join(' ') || '<span class="text-muted">—</span>'}</td>
        <td>${(r.tags || []).map(t => `<span class="recipe-tag">${t}</span>`).join(' ') || '<span class="text-muted">—</span>'}</td>
        <td class="text-muted">${r.last_used_date || 'never'}</td>
        <td class="actions-cell">
          <button class="btn btn-ghost btn-xs" data-action="edit" data-id="${r.id}">Edit</button>
          <button class="btn btn-danger btn-xs" data-action="delete" data-id="${r.id}">Delete</button>
        </td>
      </tr>`).join('');

  return `
    <div class="view-header">
      <div>
        <div class="view-title">Recipe Library</div>
        <div class="view-subtitle">${recipes.length} recipe${recipes.length !== 1 ? 's' : ''}</div>
      </div>
      <div style="display:flex;gap:0.5rem">
        <button class="btn btn-secondary" id="btn-import-url">Import from URL</button>
        <button class="btn btn-primary" id="btn-add-recipe">+ Add Recipe</button>
      </div>
    </div>
    <div class="card" style="overflow:hidden">
      <table class="recipe-table">
        <thead><tr><th>Name</th><th>Method</th><th>Tags</th><th>Last Used</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function bindRecipesEvents() {
  document.getElementById('btn-add-recipe').addEventListener('click', () => openRecipeForm(null));
  document.getElementById('btn-import-url').addEventListener('click', openImportUrlModal);

  document.querySelectorAll('[data-action="edit"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const recipe = state.recipes.find(r => r.id === parseInt(btn.dataset.id));
      openRecipeForm(recipe);
    });
  });
  document.querySelectorAll('[data-action="delete"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Delete this recipe?')) return;
      try {
        await api('DELETE', `/recipes/${btn.dataset.id}`);
        renderRecipes();
      } catch (e) { showError(e.message); }
    });
  });
}

function recipeFormHTML(recipe) {
  const r = recipe || {};
  return `
    <div class="modal-title">${r.id ? 'Edit Recipe' : 'Add Recipe'}</div>
    <div class="form-grid">
      <div class="field-group" style="grid-column:1/-1">
        <label class="field-label">Name *</label>
        <input name="name" value="${r.name || ''}" required placeholder="Recipe name">
      </div>
      <div class="field-group">
        <label class="field-label">Source URL</label>
        <input name="source_url" type="url" value="${r.source_url || ''}" placeholder="https://…">
      </div>
      <div class="field-group">
        <label class="field-label">Base Servings</label>
        <input name="base_servings" type="number" min="1" value="${r.base_servings || 2}">
      </div>
      <div class="field-group">
        <label class="field-label">Prep Time (mins)</label>
        <input name="prep_time_mins" type="number" min="0" value="${r.prep_time_mins || ''}">
      </div>
      <div class="field-group">
        <label class="field-label">Cook Time (mins)</label>
        <input name="cook_time_mins" type="number" min="0" value="${r.cook_time_mins || ''}">
      </div>
    </div>
    <div class="field-group">
      <label class="field-label">Cook Methods</label>
      <div class="method-checks">
        ${['oven','stove','grill','air_fryer'].map(m =>
          `<label class="method-check-label"><input type="checkbox" name="cook_method" value="${m}" ${(r.cook_method||[]).includes(m) ? 'checked' : ''}> ${m.replace('_',' ')}</label>`
        ).join('')}
      </div>
    </div>
    <div class="field-group">
      <label class="field-label">Makes Leftovers</label>
      <label class="method-check-label"><input name="makes_leftovers" type="checkbox" ${r.makes_leftovers ? 'checked' : ''}> Cook for 4, use second serving as leftovers</label>
    </div>
    <div class="field-group">
      <label class="field-label">Tags (comma-separated)</label>
      <input name="tags" value="${(r.tags||[]).join(', ')}" placeholder="chicken, quick, weeknight">
    </div>
    <div class="field-group">
      <label class="field-label">Ingredients (one per line: name, quantity unit, category)</label>
      <textarea name="ingredients_raw" rows="5" placeholder="chicken breast, 1 lb, protein&#10;olive oil, 2 tbsp, pantry">${(r.ingredients||[]).map(i => `${i.name}, ${i.quantity} ${i.unit}, ${i.category}`).join('\n')}</textarea>
    </div>
    <div class="field-group">
      <label class="field-label">Notes</label>
      <textarea name="notes" rows="2" placeholder="Any notes…">${r.notes || ''}</textarea>
    </div>
    <div style="display:flex;gap:0.5rem;margin-top:0.5rem">
      <button class="btn btn-primary" id="btn-save-recipe">Save Recipe</button>
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
    </div>`;
}

function openRecipeForm(recipe) {
  openModal(recipeFormHTML(recipe));
  document.getElementById('btn-save-recipe').addEventListener('click', async () => {
    const form = document.querySelector('#modal-box');
    const name = form.querySelector('[name="name"]').value.trim();
    if (!name) { alert('Name is required'); return; }

    const methods = [...form.querySelectorAll('[name="cook_method"]:checked')].map(el => el.value);
    const tagsRaw = form.querySelector('[name="tags"]').value;
    const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);
    const ingredientsRaw = form.querySelector('[name="ingredients_raw"]').value;
    const ingredients = ingredientsRaw.split('\n').map(line => {
      const parts = line.split(',').map(p => p.trim());
      const [iName, qtyUnit, cat] = parts;
      if (!iName) return null;
      const qpParts = (qtyUnit || '').split(' ');
      const qty = parseFloat(qpParts[0]) || '';
      const unit = qpParts.slice(1).join(' ') || '';
      return { name: iName, quantity: qty, unit, category: cat || 'other' };
    }).filter(Boolean);

    const body = {
      name,
      source_url: form.querySelector('[name="source_url"]').value.trim() || null,
      base_servings: parseInt(form.querySelector('[name="base_servings"]').value) || 2,
      prep_time_mins: parseInt(form.querySelector('[name="prep_time_mins"]').value) || null,
      cook_time_mins: parseInt(form.querySelector('[name="cook_time_mins"]').value) || null,
      makes_leftovers: form.querySelector('[name="makes_leftovers"]').checked,
      cook_method: methods,
      tags,
      ingredients,
      notes: form.querySelector('[name="notes"]').value.trim() || null,
    };

    try {
      if (recipe?.id) {
        await api('PUT', `/recipes/${recipe.id}`, body);
      } else {
        await api('POST', '/recipes', body);
      }
      closeModal();
      renderRecipes();
    } catch (e) { showError(e.message); }
  });
}

function openImportUrlModal() {
  openModal(`
    <div class="modal-title">Import Recipe from URL</div>
    <p style="color:var(--text-muted);margin-bottom:1rem;font-size:0.875rem;line-height:1.5">Tries Spoonacular first, then JSON-LD schema — works with skinnytaste.com and most recipe blogs.</p>
    <div class="field-group">
      <label class="field-label">Recipe URL</label>
      <input id="import-url-input" type="url" placeholder="https://…">
    </div>
    <div style="display:flex;align-items:center;gap:0.75rem">
      <button class="btn btn-primary" id="btn-do-import">Import</button>
      <span id="import-status" style="font-size:0.875rem;color:var(--text-muted)"></span>
    </div>
  `);
  document.getElementById('btn-do-import').addEventListener('click', async () => {
    const url = document.getElementById('import-url-input').value.trim();
    if (!url) return;
    document.getElementById('import-status').textContent = 'Fetching…';
    try {
      const data = await api('POST', '/recipes/import-url', { url });
      closeModal();
      openRecipeForm(data);
    } catch (e) {
      document.getElementById('import-status').textContent = '';
      showError(e.message);
    }
  });
}
// ── Shopping list view ───────────────────────────────────────────────────────
async function renderShopping() {
  const el = document.getElementById('view-shopping');
  el.innerHTML = '<p>Loading...</p>';
  try {
    state.weeks = await api('GET', '/weeks');
    if (state.weeks.length === 0) {
      el.innerHTML = '<div class="empty-state"><p>No weeks yet. Create a week in the Planner first.</p></div>';
      return;
    }
    const weekId = state.currentWeekId || state.weeks[0].id;
    const week = state.weeks.find(w => w.id === weekId) || state.weeks[0];
    const sl = await api('GET', `/weeks/${week.id}/shopping-list`);
    el.innerHTML = shoppingHTML(week, sl);
    bindShoppingEvents(week, sl);
  } catch (e) { showError(e.message); }
}

const CAT_ORDER = ['produce', 'protein', 'dairy', 'pantry', 'other'];

function shoppingHTML(week, sl) {
  const weekLabel = new Date(week.week_start_date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  if (!sl || !sl.items || Object.keys(sl.items).length === 0) {
    return `
      <div class="view-header">
        <div>
          <div class="view-title">Shopping List</div>
          <div class="view-subtitle">Week of ${weekLabel}</div>
        </div>
        <button class="btn btn-primary" id="btn-regen">Generate</button>
      </div>
      <div class="empty-state"><p>No shopping list yet. Generate one from the Planner view, or click Generate above.</p></div>`;
  }

  const items = sl.items;
  const byCat = {};
  for (const [name, data] of Object.entries(items)) {
    const cat = data.category || 'other';
    if (!byCat[cat]) byCat[cat] = [];
    byCat[cat].push([name, data]);
  }

  const allCats = [...CAT_ORDER, ...Object.keys(byCat).filter(c => !CAT_ORDER.includes(c))];
  let sections = '';
  for (const cat of allCats) {
    if (!byCat[cat]) continue;
    const catItems = byCat[cat].sort((a, b) => a[0].localeCompare(b[0]));
    sections += `<div class="shopping-section">
      <div class="shopping-section-title">${cat.charAt(0).toUpperCase() + cat.slice(1)}</div>
      ${catItems.map(([name, data]) => {
        const qty = data.quantity ? `${parseFloat(data.quantity).toFixed(1)} ${data.unit || ''}`.trim() : '';
        return `<div class="shopping-item ${data.checked ? 'checked' : ''}" data-name="${name}">
          <input type="checkbox" class="item-check" data-name="${name}" ${data.checked ? 'checked' : ''}>
          <span class="item-label">${name}${qty ? '<span class="item-qty"> — ' + qty + '</span>' : ''}</span>
          <button class="pantry-btn" data-name="${name}" title="Add to pantry staples">☆</button>
        </div>`;
      }).join('')}
    </div>`;
  }

  const total = Object.keys(items).length;
  const checked = Object.values(items).filter(d => d.checked).length;

  return `
    <div class="view-header">
      <div>
        <div class="view-title">Shopping List</div>
        <div class="view-subtitle">Week of ${weekLabel} &mdash; ${checked}/${total} items checked</div>
      </div>
      <div style="display:flex;gap:0.5rem">
        <button class="btn btn-secondary" id="btn-export-md">Export Markdown</button>
        <button class="btn btn-primary" id="btn-regen">Regenerate</button>
      </div>
    </div>
    <div class="shopping-columns">${sections}</div>`;
}

function bindShoppingEvents(week, sl) {
  document.getElementById('btn-regen')?.addEventListener('click', async () => {
    try {
      await api('POST', `/weeks/${week.id}/shopping-list`);
      renderShopping();
    } catch (e) { showError(e.message); }
  });

  document.getElementById('btn-export-md')?.addEventListener('click', async () => {
    try {
      const resp = await fetch(`/api/weeks/${week.id}/export`);
      if (!resp.ok) throw new Error(await resp.text());
      const text = await resp.text();
      const blob = new Blob([text], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `shopping-${week.week_start_date}.md`;
      a.click();
    } catch (e) { showError(e.message); }
  });

  document.querySelectorAll('.item-check').forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      const name = checkbox.dataset.name;
      const updated = { ...sl.items };
      updated[name] = { ...updated[name], checked: checkbox.checked };
      sl.items = updated;
      checkbox.closest('.shopping-item').classList.toggle('checked', checkbox.checked);
      // Update subtitle count
      const total = Object.keys(sl.items).length;
      const checked = Object.values(sl.items).filter(d => d.checked).length;
      const sub = document.querySelector('.view-subtitle');
      if (sub) sub.innerHTML = sub.innerHTML.replace(/\d+\/\d+ items checked/, `${checked}/${total} items checked`);
    });
  });

  document.querySelectorAll('.pantry-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const name = btn.dataset.name;
      const item = sl?.items?.[name] || {};
      try {
        await api('POST', '/pantry', { ingredient_name: name, category: item.category || 'other' });
        btn.textContent = '★';
        btn.title = 'Added to pantry staples';
        btn.style.color = 'var(--accent)';
      } catch (e) { showError(e.message); }
    });
  });
}
function renderSettings() {
  document.getElementById('view-settings').innerHTML = '<p>Settings loading...</p>';
}

// ── Init ─────────────────────────────────────────────────────────────────────
navigate('planner');
