from app.models import execute_query

def init_db():
    create_enum_role_type = """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role_type') THEN
            CREATE TYPE role_type AS ENUM ('admin','user');
        END IF;
    END$$;
    """

    create_groupes_table = """
    CREATE TABLE IF NOT EXISTS groupes (
        id SERIAL PRIMARY KEY,
        nom VARCHAR(100) UNIQUE NOT NULL,
        description TEXT
    );
    """

    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        nom VARCHAR(100) NOT NULL,
        prenom VARCHAR(100) NOT NULL,
        email VARCHAR(150) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role role_type NOT NULL,
        group_id INTEGER REFERENCES groupes(id) ON DELETE SET NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    execute_query(create_enum_role_type, fetch=False)
    execute_query(create_groupes_table, fetch=False)
    execute_query(create_users_table, fetch=False)