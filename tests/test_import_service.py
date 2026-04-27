from unittest.mock import patch, MagicMock
from app.services.import_service import map_spoonacular, map_json_ld, import_from_url, _find_recipe_schema


def test_map_spoonacular_basic():
    data = {
        'title': 'Spaghetti Bolognese',
        'id': 123,
        'servings': 4,
        'preparationMinutes': 10,
        'cookingMinutes': 30,
        'sourceUrl': 'https://example.com/recipe',
        'extendedIngredients': [
            {'name': 'ground beef', 'amount': 0.5, 'unit': 'lb'},
        ],
        'nutrition': {'nutrients': [
            {'name': 'Calories', 'amount': 450},
            {'name': 'Protein', 'amount': 30},
        ]},
    }
    result = map_spoonacular(data)
    assert result['name'] == 'Spaghetti Bolognese'
    assert result['base_servings'] == 4
    assert result['prep_time_mins'] == 10
    assert result['cook_time_mins'] == 30
    assert len(result['ingredients']) == 1
    assert result['ingredients'][0]['name'] == 'ground beef'
    assert result['nutrition']['calories'] == 450
    assert result['cook_method'] == []


def test_map_json_ld_basic():
    data = {
        '@type': 'Recipe',
        'name': 'Avocado Toast',
        'url': 'https://skinnytaste.com/avocado-toast',
        'recipeYield': '2 servings',
        'prepTime': 'PT5M',
        'cookTime': 'PT10M',
        'recipeIngredient': ['2 slices bread', '1 avocado'],
    }
    result = map_json_ld(data)
    assert result['name'] == 'Avocado Toast'
    assert result['base_servings'] == 2
    assert result['prep_time_mins'] == 5
    assert result['cook_time_mins'] == 10
    assert len(result['ingredients']) == 2
    assert result['ingredients'][0]['name'] == '2 slices bread'
    assert result['nutrition'] is None


def test_find_recipe_schema_graph():
    data = {
        '@graph': [
            {'@type': 'WebPage', 'name': 'Page'},
            {'@type': 'Recipe', 'name': 'My Recipe'},
        ]
    }
    results = _find_recipe_schema(data)
    assert len(results) == 1
    assert results[0]['name'] == 'My Recipe'


def test_import_from_url_uses_json_ld_when_no_api_key():
    mock_html = '''<html><head>
    <script type="application/ld+json">
    {"@type": "Recipe", "name": "Test Recipe", "recipeYield": "2", "recipeIngredient": ["1 egg"]}
    </script></head></html>'''
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html
    with patch('app.services.import_service.requests.get', return_value=mock_resp):
        result = import_from_url('https://example.com/recipe', api_key=None)
    assert result is not None
    assert result['name'] == 'Test Recipe'


def test_import_from_url_returns_none_on_failure():
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch('app.services.import_service.requests.get', return_value=mock_resp):
        result = import_from_url('https://example.com/404', api_key=None)
    assert result is None
