from functools import wraps
from flask import request, jsonify, g
import jwt
from app.config import Config  # Ajuste selon l'emplacement de ta config

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Token manquant ou invalide"}), 401

        token = auth_header.split(" ")[1]

        try:
            decoded = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            if decoded.get('role') != 'admin':
                return jsonify({"error": "Accès refusé, admin uniquement"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expiré"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token invalide"}), 401

        return f(*args, **kwargs)
    return decorated


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "Token manquant"}), 401

        try:
            token = auth_header.split(" ")[1]
            decoded = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            g.user_id = decoded.get("id")  # stocké globalement pour accès facile
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expiré"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token invalide"}), 401

        return f(*args, **kwargs)
    return decorated

