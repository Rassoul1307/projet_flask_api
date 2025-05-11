from app import create_app

from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from app.models import mettre_a_jour_prompts_rappel
import atexit

app = create_app()


# Fonction planifiée
def verifier_prompts_inactifs():
    try:
        updated = mettre_a_jour_prompts_rappel()
        print(f"{updated} prompts mis à jour en 'Rappel'")
    except Exception as e:
        print(f"Erreur lors de la mise à jour des prompts : {e}")

# Initialisation du scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=verifier_prompts_inactifs, trigger="interval", days=1)
scheduler.start()

# Stopper proprement quand l'app s'arrête
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(debug=True)