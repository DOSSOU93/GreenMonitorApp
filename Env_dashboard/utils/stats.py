# utils/stats.py
"""
Calcul des statistiques
"""
import ee
import pandas as pd
import streamlit as st
from .earth_engine import get_satellite_image
from .indicators import calculate_indicator


def calculate_stats(image, geometry, scale=1000):
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


def compute_timeseries(geometry, indicator_key, sensor_config, start_year, end_year, cloud_threshold):
    """Calcule la série temporelle annuelle pour une plage d'années choisie"""
    years = list(range(start_year, end_year + 1))
    values = []
    
    for y in years:
        try:
            img, _ = get_satellite_image(geometry, sensor_config, y, month=6, annual=False, cloud_threshold=cloud_threshold)
            if img is None:
                values.append(None)
                continue
                
            result = calculate_indicator(img, sensor_config, indicator_key)
            if result is None:
                values.append(None)
                continue
                
            stats = calculate_stats(result, geometry, scale=500)
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


def compute_seasonal(geometry, indicator_key, sensor_config, year, cloud_threshold):
    """Calcule la variation saisonnière pour une année donnée"""
    months = list(range(1, 13))
    month_names = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin", "Juil", "Aout", "Sep", "Oct", "Nov", "Dec"]
    values = []
    
    for m in months:
        try:
            img, _ = get_satellite_image(geometry, sensor_config, year, month=m, annual=False, cloud_threshold=cloud_threshold)
            if img is None:
                values.append(None)
                continue
                
            result = calculate_indicator(img, sensor_config, indicator_key)
            if result is None:
                values.append(None)
                continue
                
            stats = calculate_stats(result, geometry, scale=500)
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