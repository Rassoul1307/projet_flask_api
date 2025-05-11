import jwt
from datetime import datetime, timedelta


# Clé secrète (elle doit être la même que dans ton fichier de config Flask)
SECRET_KEY = 'ta_super_cle_secrete'  # Remplace par la vraie clé

# Données à encoder dans le token
payload = {
    'id': 1,
    'email': 'ahmedfall@gmail.com',
    'role': 'admin',
    "exp": datetime.utcnow() + timedelta(hours=2)
}

# Générer le token
token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

print("Voici votre JWT :")
print(token)