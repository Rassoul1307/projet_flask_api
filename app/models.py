import psycopg2
import psycopg2.extras
from app.config import Config
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


def get_db_connection():
    conn = psycopg2.connect (
        host=Config.DB_HOST,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )
    return conn

def execute_query(query, params=None, fetch=True):
    """Exécute une requête SQL"""
    conn = None
    results = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch:
                results = cur.fetchall()
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()
    return results


def insert_user(nom, prenom, email, password, role, group_id):
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
    query = """
    INSERT INTO users (nom, prenom, email, password_hash, role, group_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, nom, prenom, email, role, group_id;
    """
    return execute_query(query, (nom, prenom, email, hashed_password, role, group_id))

def get_user_by_email(email):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    row = cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "nom": row[1],
            "prenom": row[2],
            "email": row[3],
            "password": row[4],  # hashé
            "role": row[5],
            "group_id": row[6]
        }
    return None


def insert_groupe(nom, description):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO groupes (nom, description) VALUES (%s, %s) RETURNING id;", (nom, description))
        groupe_id = cursor.fetchone()[0]
        db.commit()
        return {'id': groupe_id, 'nom': nom, 'description': description}
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()

def insert_prompt(titre, contenu, auteur_id, etat='En attente'):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO prompts (titre, contenu, auteur_id, etat) VALUES (%s, %s, %s, %s) RETURNING id;",
            (titre, contenu, auteur_id, etat)
        )
        prompt_id = cursor.fetchone()[0]
        db.commit()
        return {'id': prompt_id, 'titre': titre, 'contenu': contenu, 'auteur_id': auteur_id, 'etat': etat}
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()

def valider_prompt_by_id(prompt_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE prompts SET etat = %s WHERE id = %s RETURNING id, titre, contenu, auteur_id, etat;",
            ('Activer', prompt_id)
        )
        updated = cursor.fetchone()
        db.commit()
        return updated
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()

def demander_modification_prompt(prompt_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE prompts SET etat = %s WHERE id = %s RETURNING id, titre, contenu, auteur_id, etat;",
            ('À revoir', prompt_id)
        )
        updated = cursor.fetchone()
        db.commit() 
        return updated
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()

def supprimer_prompt(prompt_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM prompts WHERE id = %s RETURNING id;", (prompt_id,))
        deleted = cursor.fetchone()
        db.commit()
        return deleted is not None
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()

def demander_suppression_prompt(prompt_id, auteur_id):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        # Vérifie que le prompt appartient à l'utilisateur
        cursor.execute("SELECT auteur_id FROM prompts WHERE id = %s;", (prompt_id,))
        row = cursor.fetchone()

        if not row or row[0] != auteur_id:
            return False  # Non autorisé ou prompt inexistant

        # Mettre à jour l'état du prompt
        cursor.execute("UPDATE prompts SET etat = %s WHERE id = %s;", ('À supprimer', prompt_id))
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()


def mettre_a_jour_prompts_rappel():
    db = get_db_connection()
    cursor = db.cursor()
    try:
        limite = datetime.utcnow() - timedelta(days=2)
        cursor.execute("""
            UPDATE prompts
            SET etat = 'Rappel'
            WHERE etat IN ('En attente', 'À revoir', 'À supprimer')
            AND date_creation <= %s
        """, (limite,))
        db.commit()
        return cursor.rowcount  # nombre de prompts mis à jour
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()

def ajouter_vote(user_id, prompt_id):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        # Vérifier si le prompt est dans un état pouvant être voté
        cursor.execute("SELECT auteur_id, etat FROM prompts WHERE id = %s", (prompt_id,))
        prompt = cursor.fetchone()
        if not prompt:
            raise ValueError("Prompt non trouvé.")
        
        auteur_id, etat = prompt
        if etat not in ('En attente', 'Rappel'):
            raise ValueError("Ce prompt n’est pas éligible au vote.")

        # Vérifier que l'utilisateur n'a pas déjà voté
        cursor.execute("SELECT 1 FROM votes WHERE user_id = %s AND prompt_id = %s", (user_id, prompt_id))
        if cursor.fetchone():
            raise ValueError("Vous avez déjà voté pour ce prompt.")

        # Vérifier l'appartenance au même groupe
        cursor.execute("""
            SELECT u1.group_id = u2.group_id
            FROM users u1, users u2
            WHERE u1.id = %s AND u2.id = %s
        """, (user_id, auteur_id))
        same_group = cursor.fetchone()[0]
        vote_value = 2 if same_group else 1

        # Insérer le vote
        cursor.execute("INSERT INTO votes (user_id, prompt_id, value) VALUES (%s, %s, %s)", (user_id, prompt_id, vote_value))

        # Calculer le total de points pour ce prompt
        cursor.execute("SELECT SUM(value) FROM votes WHERE prompt_id = %s", (prompt_id,))
        total = cursor.fetchone()[0] or 0

        # Si le total atteint 6 ou plus → activer le prompt
        if total >= 6:
            cursor.execute("UPDATE prompts SET etat = 'Activer' WHERE id = %s", (prompt_id,))

        db.commit()
        return {"message": "Vote enregistré", "points_total": total}
    
    except Exception as e:
        db.rollback()
        raise e

    finally:
        cursor.close()
        db.close()


def noter_prompt(user_id, prompt_id, valeur_note):
    if not (-10 <= valeur_note <= 10):
        raise ValueError("La note doit être comprise entre -10 et +10.")

    db = get_db_connection()
    cursor = db.cursor()

    try:
        # Vérifier l'état du prompt
        cursor.execute("SELECT auteur_id, etat FROM prompts WHERE id = %s;", (prompt_id,))
        result = cursor.fetchone()
        if not result:
            raise ValueError("Prompt introuvable.")
        auteur_id, etat = result
        if etat in ('Activer', 'À supprimer'):
            raise ValueError("Ce prompt ne peut plus être noté.")

        # Vérifier si l'utilisateur a déjà noté
        cursor.execute("SELECT 1 FROM notes WHERE user_id = %s AND prompt_id = %s;", (user_id, prompt_id))
        if cursor.fetchone():
            raise ValueError("Vous avez déjà noté ce prompt.")

        # Récupérer les groupes
        cursor.execute("SELECT group_id FROM users WHERE id = %s;", (user_id,))
        user_group = cursor.fetchone()[0]

        cursor.execute("SELECT group_id FROM users WHERE id = %s;", (auteur_id,))
        auteur_group = cursor.fetchone()[0]

        # Calcul du poids
        poids = 0.6 if user_group == auteur_group and user_group is not None else 0.4

        # Enregistrement de la note
        cursor.execute("""
            INSERT INTO notes (user_id, prompt_id, note, poids)
            VALUES (%s, %s, %s, %s);
        """, (user_id, prompt_id, valeur_note, poids))

        # Recalcul de la moyenne pondérée
        cursor.execute("""
            SELECT SUM(note * poids) / SUM(poids)
            FROM notes
            WHERE prompt_id = %s;
        """, (prompt_id,))
        moyenne = cursor.fetchone()[0] or 0

        # Recalcul du prix : 1000 * (1 + moyenne)
        nouveau_prix = int(1000 * (1 + moyenne))

        # Mise à jour du prix dans la table prompts
        cursor.execute("""
            UPDATE prompts SET prix = %s WHERE id = %s;
        """, (nouveau_prix, prompt_id))

        db.commit()
        return {
            "message": "Note enregistrée avec succès.",
            "nouveau_prix": nouveau_prix,
            "moyenne_notes": round(moyenne, 2)
        }

    except Exception as e:
        db.rollback()
        raise e

    finally:
        cursor.close()
        db.close()

# def noter_prompt(user_id, prompt_id, valeur_note):
#     if not (-10 <= valeur_note <= 10):
#         raise ValueError("La note doit être comprise entre -10 et +10.")

#     db = get_db_connection()
#     cursor = db.cursor()

#     try:
#         # Vérifier l'état du prompt
#         cursor.execute("SELECT auteur_id, etat FROM prompts WHERE id = %s;", (prompt_id,))
#         result = cursor.fetchone()
#         if not result:
#             raise ValueError("Prompt introuvable.")
#         auteur_id, etat = result
#         if etat in ('Activer', 'À supprimer'):
#             raise ValueError("Ce prompt ne peut plus être noté.")

#         # Vérifier si l'utilisateur a déjà noté
#         cursor.execute("SELECT 1 FROM notes WHERE user_id = %s AND prompt_id = %s;", (user_id, prompt_id))
#         if cursor.fetchone():
#             raise ValueError("Vous avez déjà noté ce prompt.")

#         # Récupérer les groupes
#         cursor.execute("SELECT group_id FROM users WHERE id = %s;", (user_id,))
#         user_group = cursor.fetchone()[0]

#         cursor.execute("SELECT group_id FROM users WHERE id = %s;", (auteur_id,))
#         auteur_group = cursor.fetchone()[0]

#         # Calcul du poids
#         poids = 0.6 if user_group == auteur_group else 0.4

#         # Enregistrement de la note
#         cursor.execute("""
#             INSERT INTO notes (user_id, prompt_id, note, poids)
#             VALUES (%s, %s, %s, %s);
#         """, (user_id, prompt_id, valeur_note, poids))
#         db.commit()
#         return {"message": "Note enregistrée avec succès."}

#     except Exception as e:
#         db.rollback()
#         raise e
#     finally:
#         cursor.close()
#         db.close()



def acheter_prompt_non_connecte(prompt_id, nom, prenom, telephone):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        # Vérifie que le prompt existe et est activé
        cursor.execute("SELECT prix, etat FROM prompts WHERE id = %s;", (prompt_id,))
        result = cursor.fetchone()
        if not result:
            raise ValueError("Prompt introuvable.")

        prix, etat = result
        if etat != 'Activer':
            raise ValueError("Ce prompt n’est pas disponible à l’achat.")

        # Enregistre l'achat
        cursor.execute("""
            INSERT INTO achats (prompt_id, nom, prenom, telephone, prix)
            VALUES (%s, %s, %s, %s, %s);
        """, (prompt_id, nom, prenom, telephone, prix))
        db.commit()
        return {"message": "Achat enregistré avec succès.", "prix": float(prix)}

    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()