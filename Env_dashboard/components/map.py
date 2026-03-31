# components/map.py
"""
Module de création de la carte - Version sans geemap
"""
import folium
import streamlit as st
from streamlit_folium import folium_static
from ..utils import add_polygon_to_map, get_polygon_bounds


def create_map(session_state, lat, lon):
    """
    Crée la carte principale de l'application avec Folium uniquement
    
    Args:
        session_state: Session state Streamlit
        lat: Latitude par défaut
        lon: Longitude par défaut
    
    Returns:
        folium.Map: Carte Folium
    """
    # Déterminer le centre et le zoom
    if session_state.polygon_bounds:
        center_lat, center_lon, zoom = session_state.polygon_bounds
    else:
        center_lat, center_lon, zoom = lat, lon, 7
    
    # Créer la carte Folium
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        control_scale=True
    )
    
    # Ajouter le fond satellite
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite',
        name='Satellite'
    ).add_to(m)
    
    # Ajouter le contrôle des couches
    folium.LayerControl().add_to(m)
    
    # Ajouter le polygone si présent
    if session_state.polygon_coords:
        add_polygon_to_map(m, session_state.polygon_coords, color='red', weight=3)
    
    return m