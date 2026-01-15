import streamlit as st
import json
import requests
from datetime import datetime
import jwt

# -------- Config --------
QUOTA_FILE = "quota.json"
MAX_QUOTA = 10  # requêtes par jour
JWT_SECRET = st.secrets["JWT_SECRET"]  # même clé que sur Railway

# -------- Récupération du token depuis l'URL --------
params = st.query_params
token = params.get("token")

if not token:
    st.warning("Tu dois te connecter via Google.")
    st.stop()

try:
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
except Exception:
    st.error("Token invalide ou expiré.")
    st.stop()

user_id = payload["sub"]       # ID Google unique
user_email = payload["email"] # Email Google

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

# -------- Interface --------
st.title("Démo Quota Utilisateur avec Google OAuth")

st.write(f"Bonjour {user_email} 👋")
st.write(f"Requêtes restantes aujourd'hui : {MAX_QUOTA - quota_data[user_id]['count']}")

if st.button("Appeler l'API"):

    if quota_data[user_id]["count"] >= MAX_QUOTA:
        st.error("Tu as atteint ton quota journalier ! Réessaie demain.")
    else:
        response = requests.get("https://httpbin.org/get")
        if response.status_code == 200:
            st.success("Requête API réussie !")
            st.json(response.json())
            quota_data[user_id]["count"] += 1
        else:
            st.error("Erreur lors de l'appel API.")

    with open(QUOTA_FILE, "w") as f:
        json.dump(quota_data, f, indent=4)
