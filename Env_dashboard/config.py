# config.py
"""
Configuration globale de l'application
"""
import os

# Palettes de couleurs
COLOR_PALETTES = {
    'ndvi': {
        'palette': ['#8B0000', '#FF4500', '#FFA500', '#FFFFE0', '#90EE90', '#32CD32', '#006400'],
        'min': -1,
        'max': 1,
        'legend': [
            {"value": -1.0, "color": "#8B0000", "label": "Eau"},
            {"value": 0.0, "color": "#FFA500", "label": "Sol nu"},
            {"value": 0.4, "color": "#90EE90", "label": "Vegetation"},
            {"value": 0.6, "color": "#32CD32", "label": "Foret"},
            {"value": 1.0, "color": "#006400", "label": "Foret dense"}
        ]
    },
    'ndwi': {
        'palette': ['#8B0000', '#FF4500', '#FFA500', '#FFFFE0', '#87CEEB', '#4682B4', '#00008B'],
        'min': -1,
        'max': 1,
        'legend': [
            {"value": -1.0, "color": "#8B0000", "label": "Tres sec"},
            {"value": 0.0, "color": "#FFA500", "label": "Sec"},
            {"value": 0.2, "color": "#FFFFE0", "label": "Humide"},
            {"value": 0.4, "color": "#87CEEB", "label": "Eau"},
            {"value": 1.0, "color": "#00008B", "label": "Eau abondante"}
        ]
    },
    'temperature': {
        'palette': ['#FFFFFF', '#FFE0E0', '#FFC0C0', '#FFA0A0', '#FF8080', '#FF6060', '#FF4040', '#FF2020', '#FF0000', '#CC0000', '#990000'],
        'min': 273,
        'max': 350,
        'legend': [
            {"value": 273, "color": "#FFFFFF", "label": "Froid"},
            {"value": 293, "color": "#FFC0C0", "label": "Tempere"},
            {"value": 303, "color": "#FFA0A0", "label": "Chaud"},
            {"value": 313, "color": "#FF8080", "label": "Tres chaud"},
            {"value": 350, "color": "#FF0000", "label": "Extreme"}
        ]
    },
    'change': {
        'palette': ['#8B0000', '#FF4500', '#FFFFE0', '#90EE90', '#006400'],
        'min': -0.5,
        'max': 0.5,
        'legend': [
            {"value": -0.5, "color": "#8B0000", "label": "Degradation"},
            {"value": 0.0, "color": "#FFFFE0", "label": "Stable"},
            {"value": 0.5, "color": "#006400", "label": "Amelioration"}
        ]
    },
    'classification_rf': {
        'palette': ['#FF6347', '#8B4513', '#DAA520', '#4169E1', '#228B22', '#FFD700', '#006400'],
        'min': 0,
        'max': 6,
        'legend': [
            {"value": 0, "color": "#FF6347", "label": "Buildings"},
            {"value": 1, "color": "#8B4513", "label": "Sol nu"},
            {"value": 2, "color": "#DAA520", "label": "Savane"},
            {"value": 3, "color": "#4169E1", "label": "Eau"},
            {"value": 4, "color": "#228B22", "label": "Foret galerie"},
            {"value": 5, "color": "#FFD700", "label": "Culture"},
            {"value": 6, "color": "#006400", "label": "Foret dense"}
        ]
    },
    'alerte_ndvi': {
        'palette': ['#4CAF50', '#FFC107', '#FF9800', '#F44336'],
        'min': 1,
        'max': 4,
        'legend': [
            {"value": 1, "color": "#4CAF50", "label": "Normal"},
            {"value": 2, "color": "#FFC107", "label": "Vigilance"},
            {"value": 3, "color": "#FF9800", "label": "Alerte"},
            {"value": 4, "color": "#F44336", "label": "Alerte critique"}
        ]
    }
}

# Configuration des capteurs par indicateur
SENSORS_BY_INDICATOR = {
    "NDVI": {
        "Sentinel-2 (10m)": {
            "name": "Sentinel-2",
            "collection": "COPERNICUS/S2_SR_HARMONIZED",
            "bands": {"red": "B4", "nir": "B8", "green": "B3"},
            "resolution": 10,
            "cloud_filter": "CLOUDY_PIXEL_PERCENTAGE"
        },
        "Landsat 8/9 (30m)": {
            "name": "Landsat",
            "collection": "LANDSAT/LC08/C02/T1_L2",
            "bands": {"red": "SR_B4", "nir": "SR_B5", "green": "SR_B3"},
            "resolution": 30,
            "cloud_filter": "CLOUD_COVER"
        },
        "MODIS (250m)": {
            "name": "MODIS",
            "collection": "MODIS/061/MOD13Q1",
            "bands": {"ndvi": "NDVI", "evi": "EVI"},
            "resolution": 250,
            "cloud_filter": None
        }
    },
    "NDWI": {
        "Sentinel-2 (10m)": {
            "name": "Sentinel-2",
            "collection": "COPERNICUS/S2_SR_HARMONIZED",
            "bands": {"red": "B4", "nir": "B8", "green": "B3"},
            "resolution": 10,
            "cloud_filter": "CLOUDY_PIXEL_PERCENTAGE"
        },
        "Landsat 8/9 (30m)": {
            "name": "Landsat",
            "collection": "LANDSAT/LC08/C02/T1_L2",
            "bands": {"red": "SR_B4", "nir": "SR_B5", "green": "SR_B3"},
            "resolution": 30,
            "cloud_filter": "CLOUD_COVER"
        }
    },
    "Temperature": {
        "Landsat 8/9 (30m)": {
            "name": "Landsat",
            "collection": "LANDSAT/LC08/C02/T1_L2",
            "bands": {"thermal": "ST_B10"},
            "resolution": 30,
            "cloud_filter": "CLOUD_COVER"
        }
    },
    # NOUVEAU : Classification Random Forest
    "Classification RF": {
        "Sentinel-2 (10m)": {
            "name": "Sentinel-2",
            "collection": "COPERNICUS/S2_SR_HARMONIZED",
            "bands": {"b2": "B2", "b3": "B3", "b4": "B4", "b8": "B8"},
            "resolution": 10,
            "cloud_filter": "CLOUDY_PIXEL_PERCENTAGE"
        }
    },
    # NOUVEAU : Alerte NDVI
    "Alerte NDVI": {
        "Sentinel-2 (10m)": {
            "name": "Sentinel-2",
            "collection": "COPERNICUS/S2_SR_HARMONIZED",
            "bands": {"red": "B4", "nir": "B8", "green": "B3"},
            "resolution": 10,
            "cloud_filter": "CLOUDY_PIXEL_PERCENTAGE"
        },
        "Landsat 8/9 (30m)": {
            "name": "Landsat",
            "collection": "LANDSAT/LC08/C02/T1_L2",
            "bands": {"red": "SR_B4", "nir": "SR_B5", "green": "SR_B3"},
            "resolution": 30,
            "cloud_filter": "CLOUD_COVER"
        }
    }
}

# Liste des indicateurs (avec les nouveaux)
INDICATORS = ["NDVI", "NDWI", "Temperature", "Classification RF", "Alerte NDVI"]

YEARS = list(range(2000, 2026))
MONTHS = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin", "Juil", "Aout", "Sep", "Oct", "Nov", "Dec"]

# Logo path
LOGO_PATH = os.path.join("asset", "logo.png")