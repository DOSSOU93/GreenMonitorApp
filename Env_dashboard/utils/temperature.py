# utils/temperature.py
"""
Indicateur de température (Landsat)
"""
import ee
import streamlit as st
from .base import BaseIndicator


class TemperatureIndicator(BaseIndicator):
    """Indicateur de température de brillance"""
    
    def __init__(self, palette_config):
        super().__init__("Temperature", palette_config)
        
    def calculate(self, image, sensor_config):
        """Calcule la température à partir de l'image Landsat"""
        try:
            if sensor_config["name"] == "Landsat":
                temp = image.select('ST_B10').multiply(0.00341802).add(149.0).rename('temperature')
                return temp
            else:
                st.warning("La température n'est disponible que pour Landsat")
                return None
        except Exception as e:
            st.error(f"Erreur calcul température: {e}")
            return None
    
    def interpret(self, value):
        """Interprète la valeur de température (en Kelvin)"""
        temp_c = value - 273.15
        if temp_c > 35:
            return f"Extreme {temp_c:.0f}°C", "error"
        elif temp_c > 30:
            return f"Chaud {temp_c:.0f}°C", "warning"
        elif temp_c > 20:
            return f"Tempere {temp_c:.0f}°C", "info"
        else:
            return f"Frais {temp_c:.0f}°C", "info"
    
    def get_stats_band_name(self):
        """Retourne le nom de la bande pour les statistiques"""
        return 'temperature'