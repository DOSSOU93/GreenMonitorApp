# utils/ndwi.py
"""
Indicateur NDWI (Normalized Difference Water Index)
"""
import ee
import streamlit as st
from .base import BaseIndicator


class NDWIIndicator(BaseIndicator):
    """Indice d'eau NDWI"""
    
    def __init__(self, palette_config):
        super().__init__("NDWI", palette_config)
        
    def calculate(self, image, sensor_config):
        """Calcule le NDWI à partir de l'image"""
        try:
            if sensor_config["name"] == "MODIS":
                st.warning("MODIS ne supporte pas le NDWI")
                return None
            
            bands = sensor_config["bands"]
            ndwi = image.normalizedDifference([bands["green"], bands["nir"]]).rename('NDWI')
            return ndwi
        except Exception as e:
            st.error(f"Erreur calcul NDWI: {e}")
            return None
    
    def interpret(self, value):
        """Interprète la valeur du NDWI"""
        if value > 0.3:
            return "Eau abondante", "success"
        elif value > 0:
            return "Humidite", "info"
        else:
            return "Sec", "warning"
    
    def get_stats_band_name(self):
        """Retourne le nom de la bande pour les statistiques"""
        return 'NDWI'