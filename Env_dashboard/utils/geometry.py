# utils/geometry.py
"""
Gestion des géométries
"""
import ee
import folium
import streamlit as st


def coords_to_ee_polygon(coords):
    """Convertit une liste de coordonnées en polygone Earth Engine"""
    try:
        if not coords or len(coords) < 3:
            return None
        ee_coords = []
        for coord in coords:
            if len(coord) == 2:
                ee_coords.append([coord[1], coord[0]])
        return ee.Geometry.Polygon(ee_coords)
    except:
        return None


def format_area(area_m2):
    """Formate la surface de manière lisible"""
    if area_m2 is None:
        return "N/A"
    if area_m2 < 10000:
        return f"{area_m2:.0f}m²"
    elif area_m2 < 1000000:
        return f"{area_m2/10000:.1f}ha"
    else:
        return f"{area_m2/1000000:.1f}km²"


def add_polygon_to_map(m, coords, color='red', weight=3):
    """Ajoute un polygone à la carte"""
    try:
        if coords and len(coords) >= 3:
            folium_coords = [[coord[0], coord[1]] for coord in coords]
            folium.Polygon(
                locations=folium_coords,
                color=color,
                weight=weight,
                fill=False,
                popup='Zone'
            ).add_to(m)
            return coords_to_ee_polygon(coords)
    except:
        pass
    return None


def get_polygon_bounds(coords):
    """Calcule les limites du polygone"""
    if coords and len(coords) > 0:
        lats = [coord[0] for coord in coords]
        lons = [coord[1] for coord in coords]
        center_lat = (max(lats) + min(lats)) / 2
        center_lon = (max(lons) + min(lons)) / 2
        lat_span = max(lats) - min(lats)
        lon_span = max(lons) - min(lons)
        max_span = max(lat_span, lon_span)
        
        if max_span > 5: zoom = 6
        elif max_span > 2: zoom = 7
        elif max_span > 1: zoom = 8
        elif max_span > 0.5: zoom = 9
        elif max_span > 0.2: zoom = 10
        elif max_span > 0.1: zoom = 11
        else: zoom = 12
            
        return center_lat, center_lon, zoom
    return None, None, 10