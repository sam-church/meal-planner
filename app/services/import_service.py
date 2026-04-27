import json
import re
import requests
from bs4 import BeautifulSoup

SPOONACULAR_BASE = 'https://api.spoonacular.com'


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
            'unit': ext.get('unit', ''),
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
    ingredients = [{'name': ing, 'quantity': '', 'unit': '', 'category': ''} for ing in ingredients_raw]

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
