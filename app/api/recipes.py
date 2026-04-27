from flask import Blueprint, request, jsonify
from app.database import db
from app.models.recipe import Recipe

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
