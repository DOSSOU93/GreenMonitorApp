# utils/indicators.py
"""
Calcul des indicateurs environnementaux
"""
import ee
import streamlit as st


def calculate_indicator(image, sensor_config, indicator_type):
    """Calcule l'indicateur selon le type et le capteur"""
    try:
        if sensor_config["name"] == "MODIS":
            return image
        
        bands = sensor_config["bands"]
        
        if indicator_type == "NDVI":
            band_names = image.bandNames().getInfo()
            if bands["nir"] not in band_names or bands["red"] not in band_names:
                return None
            ndvi = image.normalizedDifference([bands["nir"], bands["red"]]).rename('NDVI')
            return ndvi
            
        elif indicator_type == "NDWI":
            band_names = image.bandNames().getInfo()
            if bands["green"] not in band_names or bands["nir"] not in band_names:
                return None
            ndwi = image.normalizedDifference([bands["green"], bands["nir"]]).rename('NDWI')
            return ndwi
            
        elif indicator_type == "Temperature":
            if sensor_config["name"] == "Landsat":
                temp = image.select('ST_B10').multiply(0.00341802).add(149.0).rename('temperature')
                return temp
            return None
            
        return None
    except Exception as e:
        return None


def interpret_value(indicator, value):
    """Interprète la valeur de l'indicateur"""
    if indicator == "NDVI":
        if value > 0.6:
            return "Foret dense", "success"
        elif value > 0.4:
            return "Vegetation dense", "success"
        elif value > 0.2:
            return "Vegetation moderee", "info"
        elif value > 0:
            return "Sol nu", "warning"
        else:
            return "Eau", "info"
    elif indicator == "NDWI":
        if value > 0.3:
            return "Eau abondante", "success"
        elif value > 0:
            return "Humidite", "info"
        else:
            return "Sec", "warning"
    else:
        temp_c = value - 273.15
        if temp_c > 35:
            return f"Extreme {temp_c:.0f}°C", "error"
        elif temp_c > 30:
            return f"Chaud {temp_c:.0f}°C", "warning"
        elif temp_c > 20:
            return f"Tempere {temp_c:.0f}°C", "info"
        else:
            return f"Frais {temp_c:.0f}°C", "info"