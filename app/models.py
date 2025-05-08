import psycopg2
import psycopg2.extras
from app.config import Config

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
    hashed_password = generate_password_hash(password)
    query = """
    INSERT INTO users (nom, prenom, email, password_hash, role, group_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, nom, prenom, email, role, group_id;
    """
    return execute_query(query, (nom, prenom, email, hashed_password, role, group_id))