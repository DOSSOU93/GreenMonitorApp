# utils/earth_engine.py
"""
Initialisation et fonctions Earth Engine
"""
import ee
import streamlit as st


def load_engine():
    """
    Charge et initialise Google Earth Engine
    Gère à la fois l'authentification locale et Streamlit Cloud
    """
    # Vérifier si déjà initialisé
    try:
        ee.Initialize()
        return True
    except:
        pass
    
    # Pour Streamlit Cloud avec secrets
    try:
        if st.secrets and "earth_engine" in st.secrets:
            # Récupérer les informations du compte de service
            if "client_email" in st.secrets["earth_engine"] and "private_key" in st.secrets["earth_engine"]:
                service_account = st.secrets["earth_engine"]["client_email"]
                private_key = st.secrets["earth_engine"]["private_key"]
                
                credentials = ee.ServiceAccountCredentials(service_account, key_data=private_key)
                ee.Initialize(credentials)
                return True
    except Exception as e:
        pass
    
    # Pour l'environnement local
    try:
        ee.Initialize()
        return True
    except Exception as e:
        st.error(f"""
        ❌ Erreur d'authentification Earth Engine: {str(e)[:150]}
        
        **Pour l'environnement local :**
        1. Ouvrez un terminal
        2. Exécutez : `earthengine authenticate`
        3. Redémarrez l'application
        
        **Pour Streamlit Cloud :**
        1. Allez dans "Manage app" → "Secrets"
        2. Ajoutez les secrets suivants :
        
        [earth_engine]
        client_email = "votre-service-account@projet.iam.gserviceaccount.com"
        private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
        
        3. Redéployez l'application
        """)
        return None