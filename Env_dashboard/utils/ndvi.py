# utils/ndvi.py
"""
Indicateur NDVI (Normalized Difference Vegetation Index)
"""
import ee
import streamlit as st
import folium
from streamlit_folium import folium_static
from .base import BaseIndicator


class NDVIIndicator(BaseIndicator):
    """Indice de végétation NDVI"""
    
    def __init__(self, palette_config):
        super().__init__("NDVI", palette_config)
        self.historical_collection = None
        
    def calculate(self, image, sensor_config):
        """Calcule le NDVI à partir de l'image"""
        try:
            if sensor_config["name"] == "MODIS":
                return image
            
            bands = sensor_config["bands"]
            ndvi = image.normalizedDifference([bands["nir"], bands["red"]]).rename('NDVI')
            return ndvi
        except Exception as e:
            st.error(f"Erreur calcul NDVI: {e}")
            return None
    
    def reclassify_absolute(self, ndvi_image, region):
        """
        Reclassification par seuils absolus avec clipping sur la région
        
        Classes:
        1: NDVI > 0.5 -> Normal
        2: NDVI 0.3-0.5 -> Vigilance  
        3: NDVI 0.2-0.3 -> Alerte
        4: NDVI < 0.2 -> Alerte critique
        """
        # Appliquer le clip sur la région
        ndvi_clipped = ndvi_image.clip(region)
        
        # Créer les conditions
        normal = ndvi_clipped.gt(0.5)
        vigilance = ndvi_clipped.gt(0.3).And(ndvi_clipped.lte(0.5))
        alerte = ndvi_clipped.gt(0.2).And(ndvi_clipped.lte(0.3))
        critique = ndvi_clipped.lte(0.2)
        
        # Assigner les valeurs
        reclassified = ee.Image(1).where(normal, 1)\
                                 .where(vigilance, 2)\
                                 .where(alerte, 3)\
                                 .where(critique, 4)\
                                 .rename('NDVI_Alert_Class')
        
        return reclassified.clip(region)
    
    def calculate_anomaly(self, current_ndvi, start_date, end_date, region, sensor_config):
        """Calcule l'anomalie NDVI"""
        try:
            # Clipper l'image actuelle
            current_clipped = current_ndvi.clip(region)
            
            # Collection historique
            collection = ee.ImageCollection(sensor_config["collection"])
            collection = collection.filterDate(start_date, end_date)\
                                 .filterBounds(region)\
                                 .filterMetadata('CLOUD_COVER', 'less_than', sensor_config["max_cloud"])
            
            # Vérifier la collection
            size = collection.size().getInfo()
            if size == 0:
                st.warning(f"Aucune donnée historique trouvée pour {start_date} à {end_date}")
                return None, None
            
            # Calculer NDVI pour chaque image
            def add_ndvi(img):
                ndvi = self.calculate(img, sensor_config)
                return img.addBands(ndvi)
            
            ndvi_collection = collection.map(add_ndvi).select('NDVI')
            
            # Moyenne historique
            historical_mean = ndvi_collection.mean().rename('NDVI_Historical_Mean')
            
            # Anomalie
            anomaly = current_clipped.subtract(historical_mean).rename('NDVI_Anomaly')
            
            return anomaly.clip(region), historical_mean.clip(region)
            
        except Exception as e:
            st.error(f"Erreur calcul anomalie: {e}")
            return None, None
    
    def reclassify_anomaly(self, anomaly_image, region):
        """Reclassification des anomalies"""
        if anomaly_image is None:
            return None
        
        # Clipper l'anomalie
        anomaly_clipped = anomaly_image.clip(region)
        
        # Créer les conditions
        normal = anomaly_clipped.gt(0)
        vigilance = anomaly_clipped.gt(-0.1).And(anomaly_clipped.lte(0))
        alerte = anomaly_clipped.gt(-0.2).And(anomaly_clipped.lte(-0.1))
        critique = anomaly_clipped.lte(-0.2)
        
        # Assigner les valeurs
        reclassified = ee.Image(1).where(normal, 1)\
                                 .where(vigilance, 2)\
                                 .where(alerte, 3)\
                                 .where(critique, 4)\
                                 .rename('Anomaly_Alert_Class')
        
        return reclassified.clip(region)
    
    def display_alert_map(self, alert_map, region, map_title="Carte des alertes", analysis_scale=500):
        """
        Affiche la carte des alertes sur toute la zone du shapefile
        
        Args:
            alert_map: Image reclassifiée (valeurs 1-4)
            region: Zone d'étude (Geometry)
            map_title: Titre de la carte
            analysis_scale: Échelle d'analyse en mètres (défaut: 500m)
        """
        try:
            # Palette de couleurs pour les alertes
            vis_params = {
                'min': 1,
                'max': 4,
                'palette': ['#4CAF50', '#FFC107', '#FF9800', '#F44336']  # Vert, Jaune, Orange, Rouge
            }
            
            # Obtenir les bounds de la région pour centrer la carte
            bounds = region.bounds().getInfo()
            coords = bounds['coordinates'][0]
            
            # Calculer le centre et les limites
            lons = [coord[0] for coord in coords]
            lats = [coord[1] for coord in coords]
            center_lat = (min(lats) + max(lats)) / 2
            center_lon = (min(lons) + max(lons)) / 2
            
            # Calculer le zoom automatique basé sur la taille de la zone
            lat_span = max(lats) - min(lats)
            lon_span = max(lons) - min(lons)
            zoom_start = self._calculate_zoom(lat_span, lon_span)
            
            # Créer la carte Folium
            m = folium.Map(
                location=[center_lat, center_lon], 
                zoom_start=zoom_start,
                control_scale=True
            )
            
            # Ajouter la couche d'alertes avec la bonne échelle
            map_id = alert_map.getMapId(vis_params)
            
            folium.TileLayer(
                tiles=map_id['tile_fetcher'].url_format,
                attr='Google Earth Engine',
                name=map_title,
                overlay=True,
                opacity=0.85
            ).add_to(m)
            
            # Ajouter un fond de carte satellite pour référence
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                attr='Google Satellite',
                name='Satellite',
                overlay=False,
                control=True
            ).add_to(m)
            
            # Ajouter le contrôle des couches
            folium.LayerControl().add_to(m)
            
            # Ajouter une légende
            self._add_legend(m)
            
            # Afficher dans Streamlit avec une taille adaptée
            folium_static(m, width=900, height=650)
            
            return m
            
        except Exception as e:
            st.error(f"Erreur affichage carte: {e}")
            return None
    
    def _calculate_zoom(self, lat_span, lon_span):
        """Calcule le niveau de zoom automatique basé sur l'étendue"""
        # Niveaux de zoom approximatifs
        if lat_span < 0.01 and lon_span < 0.01:
            return 15
        elif lat_span < 0.05 and lon_span < 0.05:
            return 13
        elif lat_span < 0.2 and lon_span < 0.2:
            return 11
        elif lat_span < 0.5 and lon_span < 0.5:
            return 9
        elif lat_span < 1 and lon_span < 1:
            return 8
        elif lat_span < 2 and lon_span < 2:
            return 7
        elif lat_span < 5 and lon_span < 5:
            return 6
        else:
            return 5
    
    def _add_legend(self, map_object):
        """Ajoute une légende à la carte"""
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; 
                    right: 50px; 
                    z-index: 1000; 
                    background-color: white; 
                    padding: 15px;
                    border-radius: 8px;
                    border: 2px solid #ccc;
                    font-family: Arial;
                    font-size: 14px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
            <strong>🚨 Niveaux d'alerte</strong><br>
            <span style="color: #4CAF50;">🟢</span> Normal (>0.5)<br>
            <span style="color: #FFC107;">🟡</span> Vigilance (0.3-0.5)<br>
            <span style="color: #FF9800;">🟠</span> Alerte (0.2-0.3)<br>
            <span style="color: #F44336;">🔴</span> Alerte critique (<0.2)
        </div>
        '''
        map_object.get_root().html.add_child(folium.Element(legend_html))
    
    def get_alert_stats(self, alert_map, region, analysis_scale=500):
        """
        Calcule les statistiques des alertes sur toute la zone
        
        Args:
            alert_map: Image reclassifiée
            region: Zone d'étude
            analysis_scale: Échelle d'analyse en mètres
            
        Returns:
            dict: Pourcentages par niveau d'alerte
        """
        try:
            # Calculer l'histogramme sur toute la région
            histogram = alert_map.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=region,
                scale=analysis_scale,
                maxPixels=1e9,
                bestEffort=True,
                tileScale=4  # Augmenter tileScale pour les grandes zones
            )
            
            # Récupérer les données
            hist_data = histogram.getInfo()
            
            # Déterminer le nom de la bande
            band_name = None
            for key in hist_data.keys():
                if 'Alert_Class' in key or 'NDVI_Alert' in key:
                    band_name = key
                    break
            
            if band_name and hist_data[band_name]:
                hist = hist_data[band_name]
                total = sum(hist.values())
                
                if total > 0:
                    stats = {
                        'Normal': (hist.get('1', 0) / total) * 100,
                        'Vigilance': (hist.get('2', 0) / total) * 100,
                        'Alerte': (hist.get('3', 0) / total) * 100,
                        'Alerte critique': (hist.get('4', 0) / total) * 100
                    }
                    return stats
                else:
                    st.warning("Aucun pixel valide trouvé dans la zone")
                    return None
            else:
                st.warning("Impossible de calculer les statistiques")
                return None
                
        except Exception as e:
            st.error(f"Erreur calcul stats: {e}")
            return None
    
    def get_stats_band_name(self):
        return 'NDVI'