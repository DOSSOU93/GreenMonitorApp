# processor.py
"""
Module de base pour le traitement Earth Engine
"""
import ee
import streamlit as st

class SpatialProcessor:
    """Classe de base pour le traitement Earth Engine"""
    
    def __init__(self):
        """Initialise la connexion à Earth Engine via les secrets Streamlit"""
        try:
            creds_dict = st.secrets["earth_engine"]
            credentials = ee.ServiceAccountCredentials(
                creds_dict['client_email'],
                key_data=creds_dict['private_key'].replace('\\n', '\n')
            )
            ee.Initialize(credentials=credentials)
        except Exception as e:
            st.error(f"Erreur d'initialisation Earth Engine : {e}")

    def mask_clouds(self, image: ee.Image) -> ee.Image:
        """
        Masque les nuages pour Sentinel-2 SR.
        QA60 contient les informations de nuages et cirrus.
        """
        qa = image.select('QA60')
        cloud_mask = qa.bitwiseAnd(1 << 10).eq(0).And(qa.bitwiseAnd(1 << 11).eq(0))
        return image.updateMask(cloud_mask)

    def get_satellite_image(self, lat: float, lon: float) -> ee.Image:
        """
        Récupère la dernière image Sentinel-2 pour un point donné,
        en filtrant les nuages et en prenant l'image avec le moins de nuages.
        """
        point = ee.Geometry.Point([lon, lat])

        collection = (ee.ImageCollection("COPERNICUS/S2_SR")
                      .filterBounds(point)
                      .filterDate('2022-01-01', '2023-12-31')
                      .map(self.mask_clouds)
                      .sort('CLOUDY_PIXEL_PERCENTAGE'))

        image = collection.first()
        return image