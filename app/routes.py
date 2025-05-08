# app/routes.py
from flask import Blueprint, request, jsonify
from app.models import insert_user
from app.utils import admin_required

main = Blueprint('main', __name__)

@main.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    required_fields = ['nom', 'prenom', 'email', 'password', 'role', 'group_id']

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Champs manquants"}), 400

    try:
        result = insert_user(
            data['nom'],
            data['prenom'],
            data['email'],
            data['password'],
            data['role'],
            data['group_id']
        )
        return jsonify({"message": "Utilisateur créé avec succès", "user": result[0]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500














__all__ = ['main']