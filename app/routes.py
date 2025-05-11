# app/routes.py
from flask import Blueprint, request, jsonify, g
from app.models import insert_user, get_user_by_email,insert_groupe, insert_prompt, valider_prompt_by_id,demander_modification_prompt, supprimer_prompt, demander_suppression_prompt,ajouter_vote, noter_prompt, acheter_prompt_non_connecte
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import jwt
from datetime import datetime, timedelta
from app.config import Config
from app.utils import admin_required, login_required


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

@main.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    user = get_user_by_email(email)
    if not user or not check_password_hash(user['password'], password):
        return jsonify({"error": "Identifiants invalides"}), 401
    # Générer le token JWT
    payload = {
        'id': user['id'],
        'email': user['email'],
        'role': user['role'],
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')
    return jsonify({"token": token}), 200

@main.route('/api/groups', methods=['POST'])
@admin_required
def create_group():
    data = request.get_json()
    group_name = data.get('nom')

    if not group_name:
        return jsonify({"error": "Nom du groupe requis"}), 400

    try:
        group = insert_groupe(
            nom=group_name,
            description=data.get('description', '')
        )
        # return jsonify({"message": "Groupe créé avec succès"}), 201
        return jsonify({
            "message": "Groupe créé avec succès",
            "groupe": group
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/prompts', methods=['POST'])
@login_required
def create_prompt():
    data = request.get_json()
    titre = data.get('titre')
    contenu = data.get('contenu')

    if not titre or not contenu:
        return jsonify({"error": "Titre et contenu requis"}), 400

    try:
        prompt = insert_prompt(
            titre=titre,
            contenu=contenu,
            auteur_id=g.user_id,  # pris depuis le token
            etat=data.get('etat', 'En attente')
        )
        return jsonify({
            "message": "Prompt créé avec succès",
            "prompt": prompt
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/prompts/<int:prompt_id>/valider', methods=['PATCH'])
@admin_required
def valider_prompt(prompt_id):
    try:
        updated = valider_prompt_by_id(prompt_id)
        if not updated:
            return jsonify({"error": "Prompt non trouvé"}), 404

        return jsonify({
            "message": "Prompt validé avec succès",
            "prompt": {
                "id": updated[0],
                "titre": updated[1],
                "contenu": updated[2],
                "auteur_id": updated[3],
                "etat": updated[4]
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/prompts/<int:prompt_id>/revoir', methods=['PATCH'])
@admin_required
def demande_modication_prompt(prompt_id):
    try:
        updated = demander_modification_prompt(prompt_id)
        if not updated:
            return jsonify({"error": "Prompt non trouvé"}), 404

        return jsonify({
            "message": "Demande de modification envoyée avec succès",
            "prompt": {
                "id": updated[0],
                "titre": updated[1],
                "contenu": updated[2],
                "auteur_id": updated[3],
                "etat": updated[4]
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/prompts/<int:prompt_id>', methods=['DELETE'])
@admin_required
def delete_prompt(prompt_id):
    try:
        deleted = supprimer_prompt(prompt_id)
        if not deleted:
            return jsonify({"error": "Prompt non trouvé"}), 404

        return jsonify({"message": "Prompt supprimé avec succès"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/prompts/<int:prompt_id>/demande-suppression', methods=['PATCH'])
@login_required  # ou toute autre vérification d'utilisateur connecté
def demande_suppression_prompt(prompt_id):
    try:
        auteur_id = g.user_id  # supposé être injecté par le middleware auth
        success = demander_suppression_prompt(prompt_id, auteur_id)

        if not success:
            return jsonify({"error": "Non autorisé ou prompt introuvable"}), 403

        return jsonify({"message": "Demande de suppression envoyée, en attente de validation"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/prompts/<int:prompt_id>/vote', methods=['POST'])
@login_required
def voter_prompt(prompt_id):
    user_id = g.user_id  # récupéré depuis le décorateur login_required

    try:
        result = ajouter_vote(user_id, prompt_id)
        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Une erreur s’est produite lors du vote."}), 500


@main.route('/api/prompts/<int:prompt_id>/noter', methods=['POST'])
@login_required
def noter(prompt_id):
    user_id = g.user_id
    data = request.get_json()
    note = data.get("note")

    if note is None:
        return jsonify({"error": "La note est requise."}), 400

    try:
        result = noter_prompt(user_id, prompt_id, int(note))
        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception:
        return jsonify({"error": "Une erreur s’est produite."}), 500


@main.route('/api/prompts/<int:prompt_id>/acheter', methods=['POST'])
def acheter_prompt(prompt_id):
    data = request.get_json()
    nom = data.get("nom")
    prenom = data.get("prenom")
    telephone = data.get("telephone")

    if not all([nom, prenom, telephone]):
        return jsonify({"error": "Tous les champs sont requis (nom, prénom, téléphone)."}), 400

    try:
        result = acheter_prompt_non_connecte(prompt_id, nom, prenom, telephone)
        return jsonify(result), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception:
        return jsonify({"error": "Erreur lors de l'enregistrement de l'achat."}), 500


__all__ = ['main']