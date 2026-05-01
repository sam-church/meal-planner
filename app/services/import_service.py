import json
import re
import requests
from bs4 import BeautifulSoup

SPOONACULAR_BASE = 'https://api.spoonacular.com'

# Maps full unit names to their abbreviations
_UNIT_MAP = {
    'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
    'teaspoon': 'tsp', 'teaspoons': 'tsp',
    'pound': 'lb', 'pounds': 'lb', 'lbs': 'lb',
    'ounce': 'oz', 'ounces': 'oz',
    'cup': 'cup', 'cups': 'cup',
    'gram': 'g', 'grams': 'g',
    'kilogram': 'kg', 'kilograms': 'kg',
    'milliliter': 'ml', 'milliliters': 'ml',
    'liter': 'l', 'liters': 'l',
    'clove': 'clove', 'cloves': 'cloves',
    'can': 'can', 'cans': 'cans',
    'slice': 'slice', 'slices': 'slices',
    'package': 'pkg', 'packages': 'pkg',
    'pinch': 'pinch', 'handful': 'handful',
    'large': 'large', 'medium': 'medium', 'small': 'small',
}

# All recognized unit tokens (single words); "fl oz" handled separately
_UNIT_TOKENS = set(_UNIT_MAP.keys()) | {'tbsp', 'tsp', 'lb', 'oz', 'g', 'kg', 'ml', 'l', 'pkg'}

# Matches an optional leading quantity: integer, decimal, fraction, or mixed number
_QTY_RE = re.compile(r'^(\d+\s+\d+/\d+|\d+/\d+|\d*\.?\d+)\s*')


def _abbrev_unit(unit):
    return _UNIT_MAP.get(unit.lower(), unit)


def _fmt_qty(qty_str):
    """Convert quantity string to a clean number (strips trailing .0)."""
    if '/' in qty_str:
        parts = qty_str.split()
        try:
            if len(parts) == 2:  # mixed number e.g. "1 1/2"
                num, den = parts[1].split('/')
                val = int(parts[0]) + int(num) / int(den)
            else:
                num, den = parts[0].split('/')
                val = int(num) / int(den)
            return str(round(val, 2)).rstrip('0').rstrip('.')
        except (ValueError, ZeroDivisionError):
            return qty_str
    try:
        val = float(qty_str)
        return str(int(val)) if val == int(val) else str(val)
    except ValueError:
        return qty_str


def _parse_ingredient(raw):
    """Parse a raw ingredient string into {name, quantity, unit, category}.

    Handles formats like:
      "1 tablespoon olive oil"  → name=olive oil, quantity=1, unit=tbsp
      "1/2 teaspoon salt"       → name=salt, quantity=0.5, unit=tsp
      "2 large eggs"            → name=eggs, quantity=2, unit=large
      "16 fl oz chicken broth"  → name=chicken broth, quantity=16, unit=fl oz
      "salt to taste"           → name=salt to taste, quantity='', unit=''
    """
    raw = raw.strip()
    if not raw:
        return {'name': '', 'quantity': '', 'unit': '', 'category': ''}

    m = _QTY_RE.match(raw)
    if not m:
        return {'name': raw, 'quantity': '', 'unit': '', 'category': ''}

    qty = _fmt_qty(m.group(1))
    remainder = raw[m.end():].strip()

    # Check for two-word "fl oz" first
    if re.match(r'^fl\s+oz\b', remainder, re.IGNORECASE):
        unit = 'fl oz'
        name = re.sub(r'^fl\s+oz\s*', '', remainder, flags=re.IGNORECASE).strip()
    else:
        words = remainder.split(None, 1)
        token = words[0].lower().rstrip('.')
        if token in _UNIT_TOKENS:
            unit = _abbrev_unit(token)
            name = words[1].strip() if len(words) > 1 else ''
        else:
            unit = ''
            name = remainder

    return {'name': name, 'quantity': qty, 'unit': unit, 'category': ''}


def import_from_url(url, api_key=None):
    """Try Spoonacular extract endpoint first, then JSON-LD fallback."""
    if api_key:
        result = _try_spoonacular_extract(url, api_key)
        if result:
            return result
    return _try_json_ld(url)


def _try_spoonacular_extract(url, api_key):
    try:
        resp = requests.get(
            f'{SPOONACULAR_BASE}/recipes/extract',
            params={'url': url, 'apiKey': api_key},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        return map_spoonacular(resp.json())
    except Exception:
        return None


def _try_json_ld(url):
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                recipes = _find_recipe_schema(data)
                if recipes:
                    return map_json_ld(recipes[0])
            except json.JSONDecodeError:
                continue
        return None
    except Exception:
        return None


def _find_recipe_schema(data):
    if isinstance(data, list):
        results = []
        for item in data:
            results.extend(_find_recipe_schema(item))
        return results
    if isinstance(data, dict):
        graph = data.get('@graph', [])
        if graph:
            return _find_recipe_schema(graph)
        if data.get('@type') == 'Recipe':
            return [data]
    return []


def map_spoonacular(data):
    ingredients = []
    for ext in data.get('extendedIngredients', []):
        ingredients.append({
            'name': ext.get('name', ''),
            'quantity': ext.get('amount', 0),
            'unit': _abbrev_unit(ext.get('unit', '')),
            'category': '',
        })
    nutrition = None
    nutrients = data.get('nutrition', {}).get('nutrients', [])
    if nutrients:
        def find_n(name):
            for item in nutrients:
                if item.get('name') == name:
                    return item.get('amount')
            return None
        nutrition = {
            'calories': find_n('Calories'),
            'protein_g': find_n('Protein'),
            'carbs_g': find_n('Carbohydrates'),
            'fat_g': find_n('Fat'),
        }
    prep = data.get('preparationMinutes') or 0
    total = data.get('readyInMinutes') or 0
    cook = data.get('cookingMinutes') or max(0, total - prep)
    return {
        'name': data.get('title', ''),
        'source_url': data.get('sourceUrl', ''),
        'source_api_id': str(data.get('id', '')),
        'base_servings': data.get('servings', 2),
        'ingredients': ingredients,
        'cook_method': [],
        'prep_time_mins': prep,
        'cook_time_mins': cook,
        'makes_leftovers': False,
        'nutrition': nutrition,
        'tags': [],
        'notes': '',
    }


def map_json_ld(data):
    ingredients_raw = data.get('recipeIngredient', [])
    ingredients = [_parse_ingredient(ing) for ing in ingredients_raw]

    def parse_duration(iso):
        if not iso:
            return 0
        h = re.search(r'(\d+)H', iso)
        m = re.search(r'(\d+)M', iso)
        hours = int(h.group(1)) if h else 0
        minutes = int(m.group(1)) if m else 0
        return hours * 60 + minutes

    servings = data.get('recipeYield', '2')
    if isinstance(servings, list):
        servings = servings[0] if servings else '2'
    try:
        servings = int(str(servings).split()[0])
    except (ValueError, IndexError):
        servings = 2

    return {
        'name': data.get('name', ''),
        'source_url': data.get('url', data.get('@id', '')),
        'source_api_id': None,
        'base_servings': servings,
        'ingredients': ingredients,
        'cook_method': [],
        'prep_time_mins': parse_duration(data.get('prepTime')),
        'cook_time_mins': parse_duration(data.get('cookTime')),
        'makes_leftovers': False,
        'nutrition': None,
        'tags': [],
        'notes': '',
    }
