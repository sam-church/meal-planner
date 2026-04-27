from flask import Blueprint, request, jsonify
from app.database import db
from app.models.preference import Preference

bp = Blueprint('preferences', __name__, url_prefix='/api/preferences')

@bp.route('', methods=['GET'])
def list_preferences():
    prefs = Preference.query.all()
    return jsonify([p.to_dict() for p in prefs])

@bp.route('', methods=['POST'])
def add_preference():
    data = request.get_json(silent=True) or {}

    # Validate required fields
    if not data.get('type'):
        return jsonify({'error': 'type is required'}), 400
    if not data.get('value'):
        return jsonify({'error': 'value is required'}), 400
    if not data.get('scope'):
        return jsonify({'error': 'scope is required'}), 400

    # Validate type field
    if data['type'] not in ('like', 'dislike'):
        return jsonify({'error': "type must be 'like' or 'dislike'"}), 400

    # Validate scope field
    if data['scope'] not in ('ingredient', 'cuisine'):
        return jsonify({'error': "scope must be 'ingredient' or 'cuisine'"}), 400

    pref = Preference(
        type=data['type'],
        value=data['value'],
        scope=data['scope'],
    )
    db.session.add(pref)
    db.session.commit()
    return jsonify(pref.to_dict()), 201

@bp.route('/<int:pref_id>', methods=['DELETE'])
def delete_preference(pref_id):
    pref = db.session.get(Preference, pref_id)
    if not pref:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(pref)
    db.session.commit()
    return '', 204
