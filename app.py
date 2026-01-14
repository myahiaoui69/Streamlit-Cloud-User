import streamlit as st
import json
import uuid
from datetime import datetime
import hashlib
import requests
from typing import Dict, Any

# -------------------------
# SECTION 1: Récupération des infos utilisateur (MISE À JOUR)
# -------------------------

def get_user_info() -> Dict[str, Any]:
    """
    Récupère toutes les informations disponibles sur l'utilisateur
    Version mise à jour pour Streamlit 1.31+
    """
    user_info = {}
    
    # 1. Session ID (unique par session)
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    user_info['session_id'] = st.session_state.session_id
    
    # 2. User Agent et headers (NOUVELLE MÉTHODE)
    try:
        # Utiliser st.context.headers au lieu de _get_websocket_headers
        headers = get_streamlit_headers()
        if headers:
            user_agent = headers.get("User-Agent", "Inconnu")
            user_info['user_agent'] = user_agent
            user_info['user_agent_hash'] = hashlib.md5(user_agent.encode()).hexdigest()[:16]
            
            # Récupérer toutes les headers disponibles
            user_info['headers'] = dict(headers)
    except Exception as e:
        user_info['user_agent'] = f"Erreur: {str(e)[:50]}"
    
    # 3. Adresse IP (méthodes variées)
    user_info['ip_address'] = get_client_ip()
    
    # 4. Paramètres de requête (NOUVELLE MÉTHODE)
    try:
        # Utiliser st.query_params au lieu de st.experimental_get_query_params
        params = st.query_params
        user_info['query_params_count'] = len(params)
        user_info['query_params'] = dict(params)
    except:
        user_info['query_params_count'] = 0
    
    # 5. Informations de géolocalisation
    if user_info.get('ip_address') and user_info['ip_address'] != "Non disponible":
        geo_info = get_geolocation(user_info['ip_address'])
        user_info.update(geo_info)
    
    # 6. Timestamp
    user_info['timestamp'] = datetime.now().isoformat()
    user_info['timestamp_epoch'] = int(datetime.now().timestamp())
    
    # 7. Informations de la requête
    user_info.update(get_request_info())
    
    # 8. Générer un ID utilisateur unique et persistant
    user_info['user_fingerprint'] = generate_user_fingerprint(user_info)
    
    return user_info

def get_streamlit_headers():
    """
    Fonction compatible avec les nouvelles et anciennes versions de Streamlit
    """
    try:
        # Nouvelle méthode (Streamlit 1.31+)
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            return st.context.headers
    except:
        pass
    
    try:
        # Ancienne méthode (dépréciée mais encore fonctionnelle)
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        return _get_websocket_headers()
    except:
        return None

def get_client_ip() -> str:
    """
    Tente de récupérer l'adresse IP du client via différentes méthodes
    """
    ip_address = "Non disponible"
    
    # Méthode 1: Via st.context.headers (nouvelle méthode)
    try:
        headers = get_streamlit_headers()
        if headers:
            # Essayer différents headers courants pour l'IP
            for header in ['X-Forwarded-For', 'X-Real-IP', 'CF-Connecting-IP', 'True-Client-IP', 'X-Forwarded', 'Forwarded']:
                if header in headers:
                    ip = headers[header]
                    if ip and ip.lower() != 'unknown':
                        ip_address = ip.split(',')[0].strip()  # Prendre la première IP si liste
                        break
    except:
        pass
    
    # Méthode 2: Via l'API publique (fallback)
    if ip_address == "Non disponible":
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=3)
            if response.status_code == 200:
                ip_address = response.json().get('ip', 'Non disponible')
        except:
            pass
    
    # Méthode 3: Alternative API
    if ip_address == "Non disponible":
        try:
            response = requests.get('https://api64.ipify.org?format=json', timeout=3)
            if response.status_code == 200:
                ip_address = response.json().get('ip', 'Non disponible')
        except:
            pass
    
    return ip_address

def get_geolocation(ip_address: str) -> Dict[str, Any]:
    """
    Récupère les informations de géolocalisation
    """
    geo_info = {
        'country': 'Inconnu',
        'city': 'Inconnu',
        'region': 'Inconnu',
        'timezone': 'Inconnu',
        'isp': 'Inconnu',
        'latitude': None,
        'longitude': None
    }
    
    # Éviter les IPs locales
    if ip_address in ['127.0.0.1', 'localhost', '::1', 'Non disponible']:
        return geo_info
    
    try:
        if ip_address and ip_address != "Non disponible":
            # Essayer plusieurs APIs gratuites
            apis = [
                f'https://ipapi.co/{ip_address}/json/',
                f'http://ip-api.com/json/{ip_address}',
                f'https://freeipapi.com/api/json/{ip_address}'
            ]
            
            for api_url in apis:
                try:
                    response = requests.get(api_url, timeout=3)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # ipapi.co
                        if 'country_name' in data:
                            geo_info.update({
                                'country': data.get('country_name', 'Inconnu'),
                                'city': data.get('city', 'Inconnu'),
                                'region': data.get('region', 'Inconnu'),
                                'timezone': data.get('timezone', 'Inconnu'),
                                'isp': data.get('org', data.get('isp', 'Inconnu')),
                                'latitude': data.get('latitude'),
                                'longitude': data.get('longitude')
                            })
                            break
                        
                        # ip-api.com
                        elif 'country' in data:
                            geo_info.update({
                                'country': data.get('country', 'Inconnu'),
                                'city': data.get('city', 'Inconnu'),
                                'region': data.get('regionName', 'Inconnu'),
                                'timezone': data.get('timezone', 'Inconnu'),
                                'isp': data.get('isp', 'Inconnu'),
                                'latitude': data.get('lat'),
                                'longitude': data.get('lon')
                            })
                            break
                            
                except:
                    continue
                    
    except Exception as e:
        geo_info['error'] = str(e)[:100]
    
    return geo_info

def get_request_info() -> Dict[str, Any]:
    """
    Récupère des informations sur la requête HTTP
    """
    request_info = {}
    
    try:
        headers = get_streamlit_headers()
        if headers:
            # Ne pas stocker tous les headers pour éviter la surcharge
            selected_headers = {}
            for key in ['Referer', 'Accept-Language', 'Accept-Encoding', 
                       'Connection', 'Cache-Control', 'Sec-Ch-Ua', 'Sec-Ch-Ua-Mobile']:
                if key in headers:
                    selected_headers[key] = headers[key]
            
            request_info['selected_headers'] = selected_headers
            request_info['referer'] = headers.get('Referer', 'Direct')
            request_info['accept_language'] = headers.get('Accept-Language', 'Inconnu')
            
            # Détection du navigateur simplifiée
            user_agent = headers.get('User-Agent', '')
            if 'Chrome' in user_agent:
                request_info['browser'] = 'Chrome'
            elif 'Firefox' in user_agent:
                request_info['browser'] = 'Firefox'
            elif 'Safari' in user_agent and 'Chrome' not in user_agent:
                request_info['browser'] = 'Safari'
            elif 'Edge' in user_agent:
                request_info['browser'] = 'Edge'
            else:
                request_info['browser'] = 'Autre/Inconnu'
    except Exception as e:
        request_info['error'] = str(e)
    
    return request_info

def generate_user_fingerprint(user_info: Dict[str, Any]) -> str:
    """
    Génère une empreinte unique pour l'utilisateur
    Utilise plusieurs facteurs pour créer un ID persistant
    """
    # Données à inclure dans l'empreinte
    components = [
        user_info.get('user_agent', ''),
        user_info.get('ip_address', ''),
        user_info.get('accept_language', ''),
        user_info.get('browser', '') if 'browser' in user_info else ''
    ]
    
    # Filtrer les valeurs vides et créer la chaîne
    fingerprint_string = "|".join([str(c) for c in components if c])
    
    # Hash pour anonymisation
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:32]

# -------------------------
# SECTION 2: Gestion des quotas améliorée
# -------------------------

class QuotaManager:
    """
    Gère les quotas d'utilisation par utilisateur
    """
    
    def __init__(self):
        if 'quota_data' not in st.session_state:
            st.session_state.quota_data = {}
        
        if 'quota_settings' not in st.session_state:
            # Configuration par défaut des quotas
            st.session_state.quota_settings = {
                'daily_limit': 100,
                'hourly_limit': 30,
                'monthly_limit': 1000,
                'session_limit': 10,
                'cooldown_minutes': 5
            }
    
    def check_quota(self, user_fingerprint: str, action: str = "api_call", weight: int = 1) -> Dict[str, Any]:
        """
        Vérifie si l'utilisateur a dépassé son quota
        weight: poids de l'action (ex: 1 pour normal, 2 pour lourd)
        """
        now = datetime.now()
        
        # Initialiser les données utilisateur si première fois
        if user_fingerprint not in st.session_state.quota_data:
            st.session_state.quota_data[user_fingerprint] = {
                'first_seen': now.isoformat(),
                'last_seen': now.isoformat(),
                'total_actions': 0,
                'daily_actions': {},
                'hourly_actions': {},
                'action_counts': {},
                'blocked_until': None
            }
        
        user_data = st.session_state.quota_data[user_fingerprint]
        
        # Vérifier si bloqué temporairement
        if user_data.get('blocked_until'):
            blocked_until = datetime.fromisoformat(user_data['blocked_until'])
            if now < blocked_until:
                remaining = (blocked_until - now).seconds // 60
                return {
                    'allowed': False,
                    'reason': f'Bloqué temporairement. Réessayez dans {remaining} minutes',
                    'blocked_until': user_data['blocked_until']
                }
            else:
                user_data['blocked_until'] = None
        
        # Mettre à jour les compteurs
        today = now.date().isoformat()
        current_hour = now.strftime('%Y-%m-%d %H:00')
        
        # Initialiser les compteurs du jour
        if today not in user_data['daily_actions']:
            user_data['daily_actions'][today] = 0
        
        # Initialiser les compteurs de l'heure
        if current_hour not in user_data['hourly_actions']:
            user_data['hourly_actions'][current_hour] = 0
        
        # Initialiser le compteur de l'action
        if action not in user_data['action_counts']:
            user_data['action_counts'][action] = 0
        
        # Incrémenter les compteurs
        user_data['daily_actions'][today] += weight
        user_data['hourly_actions'][current_hour] += weight
        user_data['action_counts'][action] += weight
        user_data['total_actions'] += weight
        user_data['last_seen'] = now.isoformat()
        
        # Vérifier les limites
        limits = st.session_state.quota_settings
        violations = []
        
        # Limite journalière
        if user_data['daily_actions'][today] > limits['daily_limit']:
            violations.append(f"Limite journalière dépassée ({user_data['daily_actions'][today]}/{limits['daily_limit']})")
        
        # Limite horaire
        if user_data['hourly_actions'][current_hour] > limits['hourly_limit']:
            violations.append(f"Limite horaire dépassée ({user_data['hourly_actions'][current_hour]}/{limits['hourly_limit']})")
        
        # Limite totale (mensuelle approximative)
        if user_data['total_actions'] > limits['monthly_limit']:
            violations.append(f"Limite mensuelle dépassée ({user_data['total_actions']}/{limits['monthly_limit']})")
        
        # Limite par action
        if user_data['action_counts'][action] > limits['session_limit']:
            violations.append(f"Limite pour '{action}' dépassée ({user_data['action_counts'][action]}/{limits['session_limit']})")
        
        # Si violations, bloquer temporairement
        if violations:
            block_until = (now + timedelta(minutes=limits['cooldown_minutes'])).isoformat()
            user_data['blocked_until'] = block_until
            
            return {
                'allowed': False,
                'reason': ' | '.join(violations),
                'blocked_until': block_until,
                'violations': violations,
                'counters': {
                    'daily': user_data['daily_actions'][today],
                    'hourly': user_data['hourly_actions'][current_hour],
                    'total': user_data['total_actions'],
                    'action': user_data['action_counts'][action]
                }
            }
        
        # Tout est OK
        return {
            'allowed': True,
            'counters': {
                'daily': user_data['daily_actions'][today],
                'hourly': user_data['hourly_actions'][current_hour],
                'total': user_data['total_actions'],
                'action': user_data['action_counts'][action]
            },
            'limits': limits
        }
    
    def reset_user_quota(self, user_fingerprint: str):
        """Réinitialise les quotas d'un utilisateur"""
        if user_fingerprint in st.session_state.quota_data:
            now = datetime.now()
            st.session_state.quota_data[user_fingerprint] = {
                'first_seen': now.isoformat(),
                'last_seen': now.isoformat(),
                'total_actions': 0,
                'daily_actions': {now.date().isoformat(): 0},
                'hourly_actions': {now.strftime('%Y-%m-%d %H:00'): 0},
                'action_counts': {},
                'blocked_until': None
            }
    
    def get_stats(self):
        """Retourne des statistiques globales"""
        total_users = len(st.session_state.quota_data)
        total_actions = sum([data['total_actions'] for data in st.session_state.quota_data.values()])
        
        # Utilisateurs actifs aujourd'hui
        today = datetime.now().date().isoformat()
        active_today = sum([1 for data in st.session_state.quota_data.values() 
                           if today in data['daily_actions'] and data['daily_actions'][today] > 0])
        
        return {
            'total_users': total_users,
            'total_actions': total_actions,
            'active_today': active_today,
            'quota_settings': st.session_state.quota_settings
        }

# -------------------------
# SECTION 3: Interface Streamlit améliorée
# -------------------------

def main():
    st.set_page_config(
        page_title="Système de Quota & Sécurité",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🛡️ Système de Sécurité & Gestion des Quotas")
    st.markdown("""
    Cette application démontre comment récupérer les informations utilisateur
    et implémenter un système de quotas pour prévenir les abus.
    """)
    
    # Initialiser le gestionnaire de quotas
    quota_manager = QuotaManager()
    
    # Récupérer les informations utilisateur
    with st.spinner("Analyse de votre configuration..."):
        user_info = get_user_info()
    
    # Afficher les informations dans des onglets
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👤 Votre Profil", 
        "⚖️ Quotas", 
        "🗺️ Géolocalisation",
        "📊 Statistiques",
        "🔧 Paramètres"
    ])
    
    with tab1:
        st.header("Votre empreinte numérique")
        
        # Section d'identification
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Empreinte", user_info.get('user_fingerprint', 'N/A')[:16] + "...")
            st.caption("ID unique généré")
        
        with col2:
            st.metric("Session", user_info.get('session_id', 'N/A')[:8])
            st.caption("ID de session")
        
        with col3:
            ip_display = user_info.get('ip_address', 'N/A')
            if len(ip_display) > 20:
                ip_display = ip_display[:20] + "..."
            st.metric("Adresse IP", ip_display)
            st.caption("Adresse réseau détectée")
        
        # Détails techniques
        with st.expander("📋 Détails techniques complets", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Informations navigateur")
                browser = user_info.get('browser', 'Inconnu')
                st.write(f"**Navigateur:** {browser}")
                
                user_agent = user_info.get('user_agent', 'Inconnu')
                if len(user_agent) > 80:
                    user_agent = user_agent[:80] + "..."
                st.write(f"**User Agent:** `{user_agent}`")
                
                st.write(f"**Langue:** {user_info.get('accept_language', 'Inconnu')}")
                st.write(f"**Referer:** {user_info.get('referer', 'Direct')}")
            
            with col2:
                st.subheader("Informations réseau")
                st.write(f"**Pays:** {user_info.get('country', 'Inconnu')}")
                st.write(f"**Ville:** {user_info.get('city', 'Inconnu')}")
                st.write(f"**Région:** {user_info.get('region', 'Inconnu')}")
                st.write(f"**Fuseau horaire:** {user_info.get('timezone', 'Inconnu')}")
                st.write(f"**Fournisseur:** {user_info.get('isp', 'Inconnu')}")
        
        # Test de changement d'IP (pour VPN)
        with st.expander("🔍 Test de détection VPN/Proxy"):
            st.info("Activez/désactivez votre VPN et cliquez sur le bouton ci-dessous")
            if st.button("Rafraîchir les informations IP"):
                st.rerun()
    
    with tab2:
        st.header("Gestion de vos quotas")
        
        # Vérifier le quota actuel
        quota_result = quota_manager.check_quota(user_info['user_fingerprint'], "page_view")
        
        # Afficher le statut
        if quota_result['allowed']:
            st.success("✅ Vous êtes autorisé à utiliser le service")
        else:
            st.error(f"⛔ Accès temporairement limité: {quota_result['reason']}")
            if 'blocked_until' in quota_result:
                blocked_time = datetime.fromisoformat(quota_result['blocked_until'])
                remaining = (blocked_time - datetime.now()).seconds // 60
                st.warning(f"⏰ Déblocage dans {remaining} minutes")
        
        # Afficher les compteurs
        st.subheader("Votre utilisation actuelle")
        
        cols = st.columns(4)
        counters = quota_result.get('counters', {})
        
        with cols[0]:
            st.metric("Aujourd'hui", counters.get('daily', 0))
            st.caption(f"Limite: {quota_result.get('limits', {}).get('daily_limit', 100)}")
        
        with cols[1]:
            st.metric("Cette heure", counters.get('hourly', 0))
            st.caption(f"Limite: {quota_result.get('limits', {}).get('hourly_limit', 30)}")
        
        with cols[2]:
            st.metric("Total", counters.get('total', 0))
            st.caption(f"Limite: {quota_result.get('limits', {}).get('monthly_limit', 1000)}")
        
        with cols[3]:
            st.metric("Actions", counters.get('action', 0))
            st.caption(f"Limite: {quota_result.get('limits', {}).get('session_limit', 10)}")
        
        # Simuler des actions
        st.subheader("Tester le système de quotas")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Simuler une action légère", type="primary"):
                result = quota_manager.check_quota(user_info['user_fingerprint'], "light_action", 1)
                st.session_state.last_action = result
                st.rerun()
        
        with col2:
            if st.button("Simuler une action lourde", type="secondary"):
                result = quota_manager.check_quota(user_info['user_fingerprint'], "heavy_action", 5)
                st.session_state.last_action = result
                st.rerun()
        
        with col3:
            if st.button("Réinitialiser mes quotas", type="tertiary"):
                quota_manager.reset_user_quota(user_info['user_fingerprint'])
                st.success("Vos quotas ont été réinitialisés!")
                st.rerun()
        
        # Afficher le résultat de la dernière action
        if 'last_action' in st.session_state:
            st.json(st.session_state.last_action, expanded=False)
    
    with tab3:
        st.header("Votre position géographique")
        
        # Afficher la carte si coordonnées disponibles
        if user_info.get('latitude') and user_info.get('longitude'):
            import pandas as pd
            
            map_data = pd.DataFrame({
                'lat': [float(user_info['latitude'])],
                'lon': [float(user_info['longitude'])]
            })
            
            st.map(map_data, zoom=8, use_container_width=True)
            
            # Informations de localisation détaillées
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Coordonnées GPS:**")
                st.write(f"Latitude: {user_info['latitude']}")
                st.write(f"Longitude: {user_info['longitude']}")
                
                st.write("**Fuseau horaire:**")
                st.write(user_info.get('timezone', 'Inconnu'))
            
            with col2:
                st.write("**Localisation:**")
                st.write(f"Pays: {user_info.get('country', 'Inconnu')}")
                st.write(f"Région: {user_info.get('region', 'Inconnu')}")
                st.write(f"Ville: {user_info.get('city', 'Inconnu')}")
                
                st.write("**Fournisseur internet:**")
                st.write(user_info.get('isp', 'Inconnu'))
        else:
            st.warning("""
            ⚠️ Les coordonnées de géolocalisation ne sont pas disponibles.
            
            Raisons possibles :
            - Adresse IP locale (127.0.0.1, localhost)
            - VPN/Proxy qui masque la géolocalisation
            - Service de géolocalisation temporairement indisponible
            """)
        
        # Tester avec différentes IPs
        with st.expander("🔧 Tester avec une autre IP"):
            test_ip = st.text_input("Entrez une IP à tester:", "8.8.8.8")
            if st.button("Tester cette IP"):
                with st.spinner("Géolocalisation en cours..."):
                    geo_info = get_geolocation(test_ip)
                    st.json(geo_info, expanded=False)
    
    with tab4:
        st.header("Statistiques globales")
        
        stats = quota_manager.get_stats()
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Utilisateurs uniques", stats['total_users'])
        
        with col2:
            st.metric("Actions totales", stats['total_actions'])
        
        with col3:
            st.metric("Actifs aujourd'hui", stats['active_today'])
        
        with col4:
            avg = stats['total_actions'] / max(stats['total_users'], 1)
            st.metric("Moyenne/Utilisateur", f"{avg:.1f}")
        
        # Liste des utilisateurs
        st.subheader("Utilisateurs suivis")
        
        if st.session_state.quota_data:
            import pandas as pd
            
            users_list = []
            for fingerprint, data in st.session_state.quota_data.items():
                users_list.append({
                    'Fingerprint': fingerprint[:16] + "...",
                    'Première vue': data.get('first_seen', '')[:16],
                    'Dernière vue': data.get('last_seen', '')[:16],
                    'Actions totales': data.get('total_actions', 0),
                    'Statut': 'Bloqué' if data.get('blocked_until') else 'Actif'
                })
            
            df = pd.DataFrame(users_list)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun utilisateur n'a encore été enregistré.")
    
    with tab5:
        st.header("Configuration des quotas")
        
        # Modifier les limites
        st.subheader("Définir les limites")
        
        col1, col2 = st.columns(2)
        
        with col1:
            daily_limit = st.number_input(
                "Limite journalière", 
                min_value=1, 
                max_value=10000, 
                value=st.session_state.quota_settings['daily_limit'],
                help="Nombre maximum d'actions par jour"
            )
            
            hourly_limit = st.number_input(
                "Limite horaire", 
                min_value=1, 
                max_value=1000, 
                value=st.session_state.quota_settings['hourly_limit'],
                help="Nombre maximum d'actions par heure"
            )
        
        with col2:
            monthly_limit = st.number_input(
                "Limite mensuelle", 
                min_value=1, 
                max_value=100000, 
                value=st.session_state.quota_settings['monthly_limit'],
                help="Nombre maximum d'actions par mois"
            )
            
            session_limit = st.number_input(
                "Limite par session", 
                min_value=1, 
                max_value=100, 
                value=st.session_state.quota_settings['session_limit'],
                help="Nombre maximum d'actions par type d'action"
            )
        
        cooldown = st.slider(
            "Minutes de blocage après dépassement", 
            min_value=1, 
            max_value=60, 
            value=st.session_state.quota_settings['cooldown_minutes'],
            help="Durée de blocage après dépassement de quota"
        )
        
        if st.button("Appliquer les nouveaux paramètres", type="primary"):
            st.session_state.quota_settings.update({
                'daily_limit': daily_limit,
                'hourly_limit': hourly_limit,
                'monthly_limit': monthly_limit,
                'session_limit': session_limit,
                'cooldown_minutes': cooldown
            })
            st.success("Paramètres mis à jour avec succès!")
            st.rerun()
        
        # Exporter/Importer les données
        st.subheader("Gestion des données")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Exporter les données", help="Téléchargez toutes les données de quota"):
                import json
                from datetime import datetime
                
                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'quota_data': st.session_state.quota_data,
                    'quota_settings': st.session_state.quota_settings,
                    'export_user': user_info.get('user_fingerprint')
                }
                
                st.download_button(
                    label="Télécharger JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"quota_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("Réinitialiser toutes les données", type="tertiary", help="ATTENTION: Supprime toutes les données!"):
                if st.checkbox("Je confirme vouloir supprimer toutes les données"):
                    st.session_state.quota_data = {}
                    st.success("Toutes les données ont été réinitialisées!")
                    st.rerun()
    
    # Pied de page
    st.divider()
    
    # Afficher l'IP et la géolocalisation en bas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption(f"🌐 IP: {user_info.get('ip_address', 'N/A')}")
    
    with col2:
        location = f"{user_info.get('city', '')}, {user_info.get('country', '')}"
        if location != ", ":
            st.caption(f"📍 {location}")
    
    with col3:
        st.caption(f"🆔 Session: {user_info.get('session_id', 'N/A')[:8]}")

if __name__ == "__main__":
    main()