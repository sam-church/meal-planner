from flask import Blueprint, request, jsonify, current_app
from app.database import db
from app.models.recipe import Recipe
import requests as http_requests

bp = Blueprint('recipes', __name__, url_prefix='/api/recipes')

UPDATABLE_FIELDS = [
    'name', 'source_url', 'source_api_id', 'base_servings', 'ingredients',
    'cook_method', 'prep_time_mins', 'cook_time_mins', 'makes_leftovers',
    'nutrition', 'tags', 'notes',
]

@bp.route('', methods=['GET'])
def list_recipes():
    recipes = Recipe.query.order_by(Recipe.name).all()
    return jsonify([r.to_dict() for r in recipes])

@bp.route('', methods=['POST'])
def create_recipe():
    data = request.get_json(silent=True) or {}

    # Validate required field
    if not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    recipe = Recipe(
        name=data['name'],
        source_url=data.get('source_url'),
        source_api_id=data.get('source_api_id'),
        base_servings=data.get('base_servings', 2),
        ingredients=data.get('ingredients', []),
        cook_method=data.get('cook_method', []),
        prep_time_mins=data.get('prep_time_mins'),
        cook_time_mins=data.get('cook_time_mins'),
        makes_leftovers=data.get('makes_leftovers', False),
        nutrition=data.get('nutrition'),
        tags=data.get('tags', []),
        notes=data.get('notes'),
    )
    db.session.add(recipe)
    db.session.commit()
    return jsonify(recipe.to_dict()), 201

@bp.route('/<int:recipe_id>', methods=['GET'])
def get_recipe(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(recipe.to_dict())

@bp.route('/<int:recipe_id>', methods=['PUT'])
def update_recipe(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json(silent=True) or {}
    for field in UPDATABLE_FIELDS:
        if field in data:
            setattr(recipe, field, data[field])
    db.session.commit()
    return jsonify(recipe.to_dict())

@bp.route('/<int:recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(recipe)
    db.session.commit()
    return '', 204


@bp.route('/search', methods=['GET'])
def search_spoonacular():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'query parameter q is required'}), 400
    api_key = current_app.config.get('SPOONACULAR_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'Spoonacular API key not configured'}), 503
    try:
        resp = http_requests.get(
            'https://api.spoonacular.com/recipes/complexSearch',
            params={'query': query, 'apiKey': api_key, 'number': 10},
            timeout=10,
        )
        resp.raise_for_status()
        return jsonify(resp.json())
    except http_requests.RequestException as e:
        return jsonify({'error': f'Spoonacular search failed: {str(e)}'}), 502


@bp.route('/import/<int:spoonacular_id>', methods=['POST'])
def import_spoonacular(spoonacular_id):
    api_key = current_app.config.get('SPOONACULAR_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'Spoonacular API key not configured'}), 503
    try:
        resp = http_requests.get(
            f'https://api.spoonacular.com/recipes/{spoonacular_id}/information',
            params={'apiKey': api_key, 'includeNutrition': True},
            timeout=10,
        )
        resp.raise_for_status()
    except http_requests.RequestException as e:
        return jsonify({'error': f'Spoonacular fetch failed: {str(e)}'}), 502

    from app.services.import_service import map_spoonacular
    recipe_data = map_spoonacular(resp.json())
    recipe = Recipe(**recipe_data)
    db.session.add(recipe)
    db.session.commit()
    return jsonify(recipe.to_dict()), 201


@bp.route('/import-url', methods=['POST'])
def import_url():
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'url is required'}), 400
    api_key = current_app.config.get('SPOONACULAR_API_KEY', '')
    from app.services.import_service import import_from_url
    recipe_data = import_from_url(url, api_key or None)
    if not recipe_data:
        return jsonify({'error': 'Could not parse recipe from URL — check the URL or fill in details manually'}), 422
    return jsonify(recipe_data)
