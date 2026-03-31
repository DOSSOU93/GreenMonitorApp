# utils/ndvi_alert.py
"""
Module d'alerte NDVI - Détection précoce des dégradations de la végétation
"""

import ee
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static


class NDVIAlert:
    """
    Système d'alerte NDVI pour la détection précoce des dégradations
    """
    
    def __init__(self):
        # Définition des seuils d'alerte (uniquement pour la végétation)
        self.alert_levels = {
            1: {'name': 'Normal', 'color': '#4CAF50', 'ndvi_min': 0.5, 'ndvi_max': 1.0, 'priority': 4},
            2: {'name': 'Vigilance', 'color': '#FFC107', 'ndvi_min': 0.3, 'ndvi_max': 0.5, 'priority': 3},
            3: {'name': 'Alerte', 'color': '#FF9800', 'ndvi_min': 0.2, 'ndvi_max': 0.3, 'priority': 2},
            4: {'name': 'Alerte critique', 'color': '#F44336', 'ndvi_min': 0.0, 'ndvi_max': 0.2, 'priority': 1},
            5: {'name': 'Eau / Sol nu', 'color': '#808080', 'ndvi_min': -1.0, 'ndvi_max': 0.0, 'priority': 0}
        }
        
        self.alert_palette = ['#4CAF50', '#FFC107', '#FF9800', '#F44336', '#808080']
        self.alert_labels = ['Normal', 'Vigilance', 'Alerte', 'Alerte critique', 'Eau/Sol nu']
    
    def classify_absolute(self, ndvi_image: ee.Image, region: ee.Geometry = None) -> ee.Image:
        """
        Classification par seuils absolus (limitée à la zone d'étude)
        
        Args:
            ndvi_image: Image NDVI
            region: Zone d'étude pour le masquage
            
        Returns:
            ee.Image: Image classifiée (1=Normal, 2=Vigilance, 3=Alerte, 4=Alerte critique, 5=Eau/Sol nu)
        """
        # Classification avec exclusion des zones d'eau (NDVI < 0)
        alert_map = ndvi_image.expression(
            "("
            "(ndvi > 0.5) ? 1 : "
            "(ndvi > 0.3 && ndvi <= 0.5) ? 2 : "
            "(ndvi > 0.2 && ndvi <= 0.3) ? 3 : "
            "(ndvi > 0 && ndvi <= 0.2) ? 4 : "
            "(ndvi <= 0) ? 5 : 0"
            ")", {
                'ndvi': ndvi_image
            }
        ).rename('alert')
        
        # Limiter à la zone d'étude si fournie
        if region:
            alert_map = alert_map.clip(region)
        
        return alert_map
    
    def classify_anomaly(self, anomaly: ee.Image, region: ee.Geometry = None) -> ee.Image:
        """
        Classification basée sur les anomalies (limitée à la zone d'étude)
        
        Args:
            anomaly: Image d'anomalie NDVI
            region: Zone d'étude pour le masquage
            
        Returns:
            ee.Image: Image classifiée des alertes
        """
        alert_map = anomaly.expression(
            "("
            "(anomaly > 0.05) ? 1 : "
            "(anomaly > -0.05 && anomaly <= 0.05) ? 2 : "
            "(anomaly > -0.15 && anomaly <= -0.05) ? 3 : "
            "(anomaly <= -0.15) ? 4 : 0"
            ")", {
                'anomaly': anomaly
            }
        ).rename('alert')
        
        # Limiter à la zone d'étude si fournie
        if region:
            alert_map = alert_map.clip(region)
        
        return alert_map
    
    def get_stats(self, alert_map: ee.Image, region: ee.Geometry, scale: int = 30) -> dict:
        """
        Calcule les statistiques des alertes (uniquement sur la zone d'étude)
        """
        # S'assurer que le calcul est limité à la région
        histogram = alert_map.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=region,
            scale=scale,
            bestEffort=True,
            maxPixels=1e9
        ).getInfo()
        
        stats = {}
        if 'alert' in histogram:
            total = sum(histogram['alert'].values())
            for i in range(1, 6):
                count = histogram['alert'].get(str(i), 0)
                pct = (count / total) * 100 if total > 0 else 0
                stats[self.alert_labels[i-1]] = pct
        
        return stats
    
    def display_stats(self, stats: dict):
        """
        Affiche les statistiques des alertes
        """
        if not stats:
            st.warning("Aucune donnée disponible")
            return
        
        st.markdown("### 📊 Distribution des alertes")
        
        cols = st.columns(5)
        for i, (level, color) in enumerate(zip(self.alert_labels, self.alert_palette)):
            pct = stats.get(level, 0)
            with cols[i]:
                st.markdown(
                    f"""
                    <div style="text-align:center; background-color:{color}20; padding:10px; border-radius:10px; margin:5px;">
                        <div style="background-color:{color}; width:30px; height:30px; border-radius:50%; margin:0 auto;"></div>
                        <strong>{level}</strong><br>
                        <span style="font-size:20px; font-weight:bold;">{pct:.1f}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        
        # Barre de progression (exclure Eau/Sol nu si nécessaire)
        st.markdown("#### Vue d'ensemble (végétation uniquement)")
        progress_html = "<div style='display: flex; height: 35px; border-radius: 8px; overflow: hidden; margin: 10px 0;'>"
        for i, (level, color) in enumerate(zip(self.alert_labels[:4], self.alert_palette[:4])):
            pct = stats.get(level, 0)
            if pct > 0:
                progress_html += f"<div style='background-color: {color}; width: {pct}%; text-align: center; color: white; line-height: 35px; font-size: 12px;'>{level}: {pct:.0f}%</div>"
        progress_html += "</div>"
        st.markdown(progress_html, unsafe_allow_html=True)
        
        # Afficher le pourcentage d'eau/sol nu
        water_pct = stats.get('Eau/Sol nu', 0)
        if water_pct > 0:
            st.caption(f"ℹ️ Zones d'eau ou sol nu exclues de l'analyse: {water_pct:.1f}%")
    
    def display_recommendations(self, stats: dict):
        """
        Affiche les recommandations basées sur les statistiques
        """
        st.markdown("### 🎯 Recommandations")
        
        critique = stats.get('Alerte critique', 0)
        alerte = stats.get('Alerte', 0)
        vigilance = stats.get('Vigilance', 0)
        normal = stats.get('Normal', 0)
        
        if critique > 20:
            st.error(f"""
            ⚠️ **ALERTE CRITIQUE** : {critique:.1f}% de la végétation en dégradation sévère
            
            **Actions recommandées :**
            - 🚨 Intervention immédiate sur site
            - 📊 Évaluation approfondie des causes
            - 📋 Plan de restauration d'urgence
            - 👥 Mobilisation des équipes terrain
            """)
        elif alerte > 30:
            st.warning(f"""
            ⚠️ **ALERTE** : {alerte:.1f}% de la végétation en dégradation significative
            
            **Actions recommandées :**
            - 🔍 Surveillance renforcée
            - 📈 Analyse des facteurs de stress
            - 🛡️ Mesures préventives
            - 📞 Consultation des experts
            """)
        elif vigilance > 40:
            st.info(f"""
            ℹ️ **VIGILANCE** : {vigilance:.1f}% de la végétation montre des signes de stress
            
            **Actions recommandées :**
            - 👁️ Surveillance régulière
            - 📊 Collecte de données supplémentaires
            - 📝 Préparation d'un plan d'action
            """)
        elif normal > 70:
            st.success(f"""
            ✅ **SITUATION NORMALE** : {normal:.1f}% de la végétation en bonne santé
            
            **Actions recommandées :**
            - 🔄 Poursuivre la surveillance de routine
            - 📝 Maintenir les observations
            - 📸 Documenter les conditions normales
            """)
        else:
            st.info(f"""
            📊 **SITUATION MIXTE** : {normal:.1f}% normal, {vigilance:.1f}% vigilance, {alerte:.1f}% alerte
            
            **Actions recommandées :**
            - 🔍 Analyser les zones à risque
            - 📊 Planifier des visites terrain ciblées
            - 📈 Suivre l'évolution dans le temps
            """)
    
    def add_to_map(self, alert_map: ee.Image, map_obj, name: str):
        """
        Ajoute la carte des alertes à la carte Folium
        """
        vis_params = {
            'min': 1,
            'max': 5,
            'palette': self.alert_palette
        }
        map_obj.addLayer(alert_map, vis_params, name)
    
    def display_legend(self):
        """
        Affiche la légende des alertes
        """
        st.markdown("### 📋 Légende des alertes")
        cols = st.columns(5)
        for i, (level, color) in enumerate(zip(self.alert_labels, self.alert_palette)):
            with cols[i]:
                st.markdown(
                    f"""
                    <div style="text-align:center;">
                        <div style="background-color:{color}; width:40px; height:40px; border-radius:5px; margin:0 auto;"></div>
                        <strong style="font-size:12px;">{level}</strong>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        st.caption("⚠️ Les zones d'eau et sol nu (NDVI ≤ 0) sont exclues de l'analyse d'alerte")


def create_alert_map(alert_map: ee.Image, region: ee.Geometry, alert_palette: list):
    """
    Crée une carte Folium pour l'affichage des alertes
    """
    try:
        bounds = region.bounds().getInfo()
        coords = bounds['coordinates'][0]
        lons = [coord[0] for coord in coords]
        lats = [coord[1] for coord in coords]
        center_lat = (min(lats) + max(lats)) / 2
        center_lon = (min(lons) + max(lons)) / 2
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)
        
        vis_params = {
            'min': 1,
            'max': 5,
            'palette': alert_palette
        }
        
        map_id = alert_map.getMapId(vis_params)
        folium.TileLayer(
            tiles=map_id['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name='Alertes NDVI',
            overlay=True,
            opacity=0.85
        ).add_to(m)
        
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite',
            name='Satellite',
            overlay=False
        ).add_to(m)
        
        folium.LayerControl().add_to(m)
        folium_static(m, width=900, height=500)
        
    except Exception as e:
        st.warning(f"Affichage carte: {str(e)[:100]}")