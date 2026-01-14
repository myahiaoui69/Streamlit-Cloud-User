import streamlit as st
import json
import requests
from datetime import datetime

# -------- Config --------
QUOTA_FILE = "quota.json"
MAX_QUOTA = 10  # requêtes par jour

# -------- Utilisateur Google --------
user = st.experimental_user  # nécessite d'activer Google OAuth dans le dashboard
if user is None:
    st.warning("Connecte-toi avec Google pour utiliser l'application.")
    st.stop()

user_id = user.id  # identifiant unique Google
user_email = user.email

# -------- Charger le quota depuis JSON --------
try:
    with open(QUOTA_FILE, "r") as f:
        quota_data = json.load(f)
except FileNotFoundError:
    quota_data = {}

# -------- Initialiser l'utilisateur si nouveau --------
today = datetime.today().strftime("%Y-%m-%d")

if user_id not in quota_data or quota_data[user_id]["date"] != today:
    quota_data[user_id] = {"date": today, "count": 0}

# -------- Bouton pour appel API --------
st.title("Démo Quota Utilisateur avec API")

st.write(f"Bonjour {user_email} !")
st.write(f"Requêtes restantes aujourd'hui : {MAX_QUOTA - quota_data[user_id]['count']}")

if st.button("Appeler l'API"):

    if quota_data[user_id]["count"] >= MAX_QUOTA:
        st.error("Tu as atteint ton quota journalier ! Réessaie demain.")
    else:
        # -------- Appel API réel --------
        response = requests.get("https://httpbin.org/get")
        if response.status_code == 200:
            st.success("Requête API réussie !")
            st.json(response.json())
            # -------- Incrémenter le compteur --------
            quota_data[user_id]["count"] += 1
        else:
            st.error("Erreur lors de l'appel API.")

    # -------- Sauvegarder le quota --------
    with open(QUOTA_FILE, "w") as f:
        json.dump(quota_data, f, indent=4)
