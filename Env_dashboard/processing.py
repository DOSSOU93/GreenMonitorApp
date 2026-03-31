# processing.py
"""
Module de traitement des données spatiales
"""
import ee
import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, Tuple, List, Dict

class SpatialProcessor:
    """Classe principale pour le traitement des données spatiales"""
    
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
    
    def get_satellite_image_for_geometry(self, geometry: ee.Geometry, 
                                          sensor_config: dict, 
                                          year: int, 
                                          month: Optional[int] = None, 
                                          annual: bool = False,
                                          cloud_threshold: int = 20) -> Tuple[Optional[ee.Image], Optional[ee.Image]]:
        """
        Récupère une image satellite pour une géométrie donnée
        """
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
    
    def calculate_ndvi(self, image: ee.Image, sensor_config: dict) -> Optional[ee.Image]:
        """Calcule le NDVI"""
        try:
            if sensor_config["name"] == "MODIS":
                return image
            
            bands = sensor_config["bands"]
            ndvi = image.normalizedDifference([bands["nir"], bands["red"]]).rename('NDVI')
            return ndvi
        except:
            return None
    
    def calculate_ndwi(self, image: ee.Image, sensor_config: dict) -> Optional[ee.Image]:
        """Calcule le NDWI"""
        try:
            if sensor_config["name"] == "MODIS":
                return None
            
            bands = sensor_config["bands"]
            ndwi = image.normalizedDifference([bands["green"], bands["nir"]]).rename('NDWI')
            return ndwi
        except:
            return None
    
    def calculate_temperature(self, image: ee.Image, sensor_config: dict) -> Optional[ee.Image]:
        """Calcule la température (Landsat uniquement)"""
        try:
            if sensor_config["name"] == "Landsat":
                temp = image.select('ST_B10').multiply(0.00341802).add(149.0).rename('temperature')
                return temp
            return None
        except:
            return None
    
    def calculate_stats(self, image: ee.Image, geometry: ee.Geometry, scale: int = 1000) -> Optional[Dict]:
        """Calcule les statistiques d'une image"""
        try:
            if geometry.area().getInfo() > 1000000000:
                scale = max(scale, 500)
            
            stats = image.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), None, True
                ).combine(
                    ee.Reducer.min(), None, True
                ).combine(
                    ee.Reducer.max(), None, True
                ),
                geometry=geometry,
                scale=scale,
                bestEffort=True,
                maxPixels=1e10
            )
            return stats.getInfo()
        except Exception as e:
            return None
    
    def compute_timeseries(self, geometry: ee.Geometry, indicator_key: str, 
                          sensor_config: dict, start_year: int, end_year: int, 
                          cloud_threshold: int) -> Tuple[List[int], List[Optional[float]]]:
        """Calcule la série temporelle annuelle"""
        years = list(range(start_year, end_year + 1))
        values = []
        
        for y in years:
            try:
                img, _ = self.get_satellite_image_for_geometry(
                    geometry, sensor_config, y, month=6, annual=False, cloud_threshold=cloud_threshold
                )
                if img is None:
                    values.append(None)
                    continue
                    
                if indicator_key == "NDVI":
                    result = self.calculate_ndvi(img, sensor_config)
                elif indicator_key == "NDWI":
                    result = self.calculate_ndwi(img, sensor_config)
                else:
                    result = self.calculate_temperature(img, sensor_config)
                
                if result is None:
                    values.append(None)
                    continue
                    
                stats = self.calculate_stats(result, geometry, scale=500)
                if stats:
                    if indicator_key == "NDVI":
                        val = stats.get('NDVI_mean', 0) or stats.get('NDVI', 0)
                    elif indicator_key == "NDWI":
                        val = stats.get('NDWI_mean', 0) or stats.get('NDWI', 0)
                    else:
                        val = stats.get('temperature_mean', 0) or stats.get('temperature', 0)
                    values.append(val)
                else:
                    values.append(None)
            except Exception as e:
                values.append(None)
        
        return years, values
    
    def compute_seasonal(self, geometry: ee.Geometry, indicator_key: str,
                        sensor_config: dict, year: int, cloud_threshold: int) -> Tuple[List[int], List[str], List[Optional[float]]]:
        """Calcule la variation saisonnière"""
        months = list(range(1, 13))
        month_names = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin", "Juil", "Aout", "Sep", "Oct", "Nov", "Dec"]
        values = []
        
        for m in months:
            try:
                img, _ = self.get_satellite_image_for_geometry(
                    geometry, sensor_config, year, month=m, annual=False, cloud_threshold=cloud_threshold
                )
                if img is None:
                    values.append(None)
                    continue
                    
                if indicator_key == "NDVI":
                    result = self.calculate_ndvi(img, sensor_config)
                elif indicator_key == "NDWI":
                    result = self.calculate_ndwi(img, sensor_config)
                else:
                    result = self.calculate_temperature(img, sensor_config)
                
                if result is None:
                    values.append(None)
                    continue
                    
                stats = self.calculate_stats(result, geometry, scale=500)
                if stats:
                    if indicator_key == "NDVI":
                        val = stats.get('NDVI_mean', 0) or stats.get('NDVI', 0)
                    elif indicator_key == "NDWI":
                        val = stats.get('NDWI_mean', 0) or stats.get('NDWI', 0)
                    else:
                        val = stats.get('temperature_mean', 0) or stats.get('temperature', 0)
                    values.append(val)
                else:
                    values.append(None)
            except Exception as e:
                values.append(None)
        
        return months, month_names, values