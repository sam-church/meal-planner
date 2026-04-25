# Meal Planner — Design Spec
*Date: 2026-04-24*

---

## Overview

A local web app for weekly meal planning, recipe management, shopping list generation, and Google Calendar sync. Built for one household, two people, no microwave. Runs entirely on your machine — no cloud, no auth, no accounts.

---

## Scope

### In Scope
- 5-day (Mon–Fri) meal planner with lunch and dinner slots
- Optional Sunday batch prep slot
- Recipe library: manual entry, Spoonacular API import, URL import (JSON-LD with Spoonacular-first fallback)
- Assisted meal plan suggestions (variety + preferences + cook method)
- Auto-fill leftover lunch slots from prior dinner
- Shopping list generator with pantry staples exclusion
- Quick "have it" toggle and "add to permanent staples" on shopping list view
- Markdown shopping list export (Obsidian-ready)
- Weekly macro summary display (calories, protein, carbs, fat — display only, no goals)
- Soft preferences list (likes/dislikes, informs suggestions)
- Google Calendar sync to "Tripe F" calendar
- Frontend design polish via `frontend-design` skill (install plugin before frontend phase)

### Out of Scope (v1)
- Cost estimation
- Mobile layout
- User authentication
- Generic URL scraper (JSON-LD only)
- Batch cooking detail beyond Sunday prep slot (v2)

---

## Architecture

**Stack:** Python (Flask) + SQLite (SQLAlchemy) + vanilla HTML/CSS/JavaScript

```
meal-planner/
├── app/
│   ├── api/              # Flask route handlers
│   │   ├── recipes.py
│   │   ├── weeks.py
│   │   ├── shopping.py
│   │   ├── pantry.py
│   │   └── preferences.py
│   ├── services/         # Business logic
│   │   ├── suggestion_service.py
│   │   ├── shopping_service.py
│   │   ├── import_service.py
│   │   ├── calendar_service.py
│   │   └── export_service.py
│   ├── models/           # SQLAlchemy models
│   │   ├── recipe.py
│   │   ├── week_plan.py
│   │   ├── shopping_list.py
│   │   ├── pantry_staple.py
│   │   └── preference.py
│   └── static/           # Frontend (HTML/CSS/JS)
│       ├── index.html
│       ├── app.js
│       └── style.css
├── data/
│   └── meal_planner.db   # SQLite database (auto-created on first run)
├── config.py
├── run.py
├── requirements.txt
└── .gitignore            # Excludes data/token.json, data/*.db
```

Flask serves the single-page frontend at `/`. All data operations go through `/api/` JSON endpoints. The frontend uses `fetch()` to call those endpoints — no page reloads.

---

## Data Model

### `recipes`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT | |
| `source_url` | TEXT | nullable |
| `source_api_id` | TEXT | Spoonacular ID if imported |
| `ingredients` | JSON | list of `{name, quantity, unit, category}` |
| `cook_method` | JSON | subset of `["oven", "stove", "grill", "air_fryer"]` |
| `prep_time_mins` | INTEGER | |
| `cook_time_mins` | INTEGER | |
| `makes_leftovers` | BOOLEAN | true = cook for 4, false = cook for 2 |
| `nutrition` | JSON | `{calories, protein_g, carbs_g, fat_g}` per serving |
| `tags` | JSON | e.g. `["quick", "batch", "hearty", "light"]` |
| `notes` | TEXT | freeform |
| `last_used_date` | DATE | updated each time recipe is placed in a plan |

### `week_plans`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `week_start_date` | DATE | always a Monday |
| `slots` | JSON | keys: `mon_lunch`, `mon_dinner` … `fri_lunch`, `fri_dinner`, `sunday_prep` (optional). Values: recipe ID or `"leftover:<recipe_id>"` |
| `calendar_synced` | BOOLEAN | true after successful Google Calendar push |
| `notes` | TEXT | |

### `shopping_lists`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `week_plan_id` | INTEGER FK | |
| `items` | JSON | `{ingredient_name: {quantity, unit, category, checked, is_staple}}` |
| `generated_at` | DATETIME | |

### `pantry_staples`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `ingredient_name` | TEXT | |
| `category` | TEXT | `produce`, `protein`, `dairy`, `pantry`, `other` |

### `preferences`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `type` | TEXT | `like` or `dislike` |
| `value` | TEXT | e.g. `"spicy"`, `"fish"`, `"Mediterranean"` |
| `scope` | TEXT | `ingredient` or `cuisine` |

---

## Configuration (`config.py`)

```python
LUNCH_START = "11:30"
DINNER_START = "18:00"
SUNDAY_PREP_START = "14:00"
CALENDAR_NAME = "Tripe F"
SPOONACULAR_API_KEY = ""  # set via environment variable
```

Google OAuth token stored at `data/token.json` — excluded from git.

---

## API Endpoints

```
# Recipes
GET    /api/recipes                  # list library
POST   /api/recipes                  # add manually
GET    /api/recipes/<id>             # get one
PUT    /api/recipes/<id>             # edit
DELETE /api/recipes/<id>             # delete
GET    /api/recipes/search           # search Spoonacular
POST   /api/recipes/import/<id>      # save Spoonacular result to library
POST   /api/recipes/import-url       # import by URL (Spoonacular-first, JSON-LD fallback)

# Week Plans
GET    /api/weeks                    # list past plans
POST   /api/weeks                    # create new week
GET    /api/weeks/<id>               # get a specific week
PUT    /api/weeks/<id>               # update slots
POST   /api/weeks/<id>/suggest       # generate suggestions for empty slots
POST   /api/weeks/<id>/shopping-list # generate shopping list
GET    /api/weeks/<id>/export        # return markdown shopping list
POST   /api/weeks/<id>/sync-calendar # push to Google Calendar

# Pantry
GET    /api/pantry                   # list staples
POST   /api/pantry                   # add staple
DELETE /api/pantry/<id>              # remove staple

# Preferences
GET    /api/preferences              # list preferences
POST   /api/preferences              # add preference
DELETE /api/preferences/<id>         # remove preference
```

---

## Service Layer

### `suggestion_service.py`
Selects recipes for empty week slots. Logic:
1. Filter out recipes used in the last 3 weeks (`last_used_date`)
2. Filter out recipes with an empty `cook_method` list (treated as "needs tagging" — not surfaced in suggestions until at least one method is set). No microwave tag is permitted; recipes imported without a cook method must be tagged before use.
3. Weight toward recipes matching active `preferences` (likes boost, dislikes suppress)
4. Vary cook methods across the week (avoid scheduling oven 5 days in a row)
5. If `makes_leftovers = true` on the selected dinner, offer to auto-fill next day's lunch as `"leftover:<id>"`
6. Sunday prep slot: suggest recipes tagged `"batch"` only

### `shopping_service.py`
Aggregates ingredients from all slots in a week plan:
1. Collect all recipe IDs from slots (resolve leftover references to their source recipe)
2. Scale quantities: `makes_leftovers = true` → 4-serving quantities; `false` → 2-serving quantities
3. Deduplicate and sum matching ingredients
4. Exclude any ingredient whose name matches a pantry staple
5. Group by category: `produce`, `protein`, `dairy`, `pantry`, `other`

### `import_service.py`
Handles recipe import from URL:
1. Check Spoonacular for a match by URL (includes nutrition data if found)
2. If no match, fetch page HTML and parse `<script type="application/ld+json">` for Schema.org Recipe data
3. Map parsed fields to `Recipe` model
4. Return partially-filled recipe dict — missing fields left blank for manual completion in the UI

### `calendar_service.py`
Google Calendar integration:
1. Handle OAuth 2.0 flow; store token at `data/token.json`
2. If token expired, trigger re-auth in browser
3. For each slot in the week plan, create a calendar event:
   - Title: recipe name
   - Start: slot date + fixed time (`LUNCH_START`, `DINNER_START`, or `SUNDAY_PREP_START`)
   - Duration: `prep_time_mins + cook_time_mins`
   - Calendar: `CALENDAR_NAME`
4. Mark `calendar_synced = true` on success

### `export_service.py`
Renders shopping list as Obsidian-ready markdown:
```markdown
# Shopping List — Week of [date]

## Produce
- [ ] spinach — 2 cups
- [ ] cherry tomatoes — 1 pint

## Protein
- [ ] chicken breast — 1.5 lbs
```

---

## Frontend

Single HTML page (`index.html`) with four views toggled by vanilla JS router. No page reloads.

**Install note:** Before building the frontend, invoke the `frontend-design` skill (requires plugin install). If unavailable, build functional HTML/CSS/JS without it.

### Views

**Meal Planner** (default)
- 5-column (Mon–Fri) × 2-row (Lunch/Dinner) grid
- Optional Sunday prep row, toggled on/off
- Each cell: recipe name, prep + cook time, cook method icons
- Click cell → recipe picker modal
- "Suggest" button fills empty slots
- Leftover auto-fill prompt when `makes_leftovers = true` dinner is placed
- Weekly macro summary bar (totals across all slots)
- "Generate Shopping List" and "Sync to Calendar" buttons in header

**Recipe Library**
- Searchable, filterable table (by cook method, tags, last used)
- Add Recipe button → form for manual entry or import (URL field + Spoonacular search)
- Edit / delete per row

**Shopping List**
- Grouped by category with checkboxes per item
- Each item has a pantry icon button → `POST /api/pantry` (add to permanent staples)
- Checked items are visually struck through (not deleted — just marked for this week)
- "Export as Markdown" button at top

**Settings**
- Editable list: Pantry Staples (add/remove inline)
- Editable list: Preferences — likes and dislikes (add/remove inline, tag each as ingredient or cuisine)

Navigation: simple top bar with four tabs.

---

## Error Handling

- API errors (Spoonacular rate limit, network failure, Calendar auth expired): dismissible banner in the UI with plain-English message
- JSON-LD import failure: return partially-filled form for manual completion — no silent failure
- Google OAuth token expired: "Sync to Calendar" triggers re-auth flow in browser
- Database: schema auto-created on first run if `meal_planner.db` does not exist

---

## Testing

- Unit tests for `suggestion_service`, `shopping_service`, `import_service`
- One integration test per API endpoint group (recipes, weeks, shopping list, pantry, preferences)
- Manual verification for frontend and Google Calendar sync
- Test file location: `tests/`

---

## Constraints

- No microwave — recipes must use `oven`, `stove`, `grill`, or `air_fryer` only
- Cooking for 2 (standard) or 4 (leftovers) — no arbitrary serving scaling
- Single user, local only — no auth, no multi-user support
- Python 3.10+, Flask, SQLAlchemy, SQLite
