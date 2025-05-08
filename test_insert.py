from app.models import execute_query
from werkzeug.security import generate_password_hash

hashed_password = generate_password_hash("admin123", method="pbkdf2:sha256")

# Ajouter un groupe
execute_query(
    "INSERT INTO groupes (nom) VALUES (%s) ON CONFLICT (nom) DO NOTHING;",
    ("Développement",),
    fetch=False
)

# Récupérer l'id du groupe inséré
groupe = execute_query("SELECT id FROM groupes WHERE nom = %s", ("Développement",))
groupe_id = groupe[0]['id']

# Ajouter un utilisateur
execute_query(
    """
    INSERT INTO users (nom, prenom, email, password_hash, role, group_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (email) DO NOTHING;
    """,
    ("Ahmed", "Fall", "ahmedfall@gmail.com", hashed_password, "admin", groupe_id),
    fetch=False
)

print("Utilisateur inséré avec succès.")