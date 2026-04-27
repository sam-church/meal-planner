from flask import Blueprint, request, jsonify
from app.database import db
from app.models.pantry_staple import PantryStaple
from sqlalchemy.exc import IntegrityError

bp = Blueprint('pantry', __name__, url_prefix='/api/pantry')

@bp.route('', methods=['GET'])
def list_staples():
    staples = PantryStaple.query.all()
    return jsonify([s.to_dict() for s in staples])

@bp.route('', methods=['POST'])
def add_staple():
    data = request.get_json(silent=True) or {}
    if not data.get('ingredient_name'):
        return jsonify({'error': 'ingredient_name is required'}), 400

    staple = PantryStaple(
        ingredient_name=data['ingredient_name'],
        category=data.get('category', 'other'),
    )
    db.session.add(staple)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'ingredient already exists in pantry'}), 409
    return jsonify(staple.to_dict()), 201

@bp.route('/<int:staple_id>', methods=['DELETE'])
def delete_staple(staple_id):
    staple = db.session.get(PantryStaple, staple_id)
    if not staple:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(staple)
    db.session.commit()
    return '', 204
