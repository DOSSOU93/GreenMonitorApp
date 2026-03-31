# utils/earth_engine.py
"""
Fonctions pour interagir avec Earth Engine
"""
import ee
import streamlit as st
from processor import SpatialProcessor


@st.cache_resource
def load_engine():
    """Charge le moteur Earth Engine"""
    return SpatialProcessor()


def get_geotiff_url(image, geometry, filename, scale=10):
    """Génère l'URL de téléchargement GeoTIFF"""
    try:
        url = image.getDownloadURL({
            'scale': scale,
            'region': geometry,
            'format': 'GeoTIFF',
            'name': filename
        })
        return url
    except Exception as e:
        st.error(f"Erreur URL: {e}")
        return None


def calculate_change(img1, img2):
    """Calcule le changement entre deux images"""
    try:
        change = img2.subtract(img1).rename('change')
        return change
    except:
        return None


def get_satellite_image(geometry, sensor_config, year, month=None, annual=False, cloud_threshold=20):
    """Récupère une image satellite avec un seuil de nuages personnalisable"""
    try:
        if annual:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
        else:
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-28"
        
        if sensor_config["name"] == "MODIS":
            collection = ee.ImageCollection(sensor_config["collection"]) \
                .filterBounds(geometry) \
                .filterDate(start_date, end_date)
            
            size = collection.size().getInfo()
            if size == 0:
                return None, None
            
            image = collection.median().clip(geometry)
            ndvi = image.select('NDVI').rename('NDVI')
            ndvi = ndvi.multiply(0.0001)
            return ndvi, image
        
        else:
            collection = ee.ImageCollection(sensor_config["collection"]) \
                .filterBounds(geometry) \
                .filterDate(start_date, end_date)
            
            if sensor_config["cloud_filter"]:
                collection = collection.filter(ee.Filter.lt(sensor_config["cloud_filter"], cloud_threshold))
            
            size = collection.size().getInfo()
            if size == 0:
                return None, None
            
            image = collection.median().clip(geometry)
            return image, None
            
    except Exception as e:
        return None, None