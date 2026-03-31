# utils/random_forest_classifier.py
"""
Classification Random Forest - BASÉ SUR VOTRE CODE EARTH ENGINE
"""

import ee
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static

class RandomForestClassifier:
    """
    Classificateur Random Forest - Reprend exactement votre code Earth Engine
    Classes: 0=buildings, 1=sol_nu, 2=savana, 3=water, 4=foret_galery, 5=culture, 6=forest
    """
    
    def __init__(self):
        self.classes = {
            0: {'name': 'Buildings', 'color': '#FF6347', 'code': 'buildings'},
            1: {'name': 'Sol nu', 'color': '#8B4513', 'code': 'sol_nu'},
            2: {'name': 'Savane', 'color': '#DAA520', 'code': 'savana'},
            3: {'name': 'Eau', 'color': '#4169E1', 'code': 'water'},
            4: {'name': 'Forêt galerie', 'color': '#228B22', 'code': 'foret_galery'},
            5: {'name': 'Culture', 'color': '#FFD700', 'code': 'culture'},
            6: {'name': 'Forêt dense', 'color': '#006400', 'code': 'forest'}
        }
        
        self.palette = ['#FF6347', '#D2B48C', '#32CD32', '#4169E1', '#006400', '#FFD700', '#228B22']
        
        self.classifier = None
        self.validation_metrics = {}
        self.bands = ['B2', 'B3', 'B4', 'B8']
    
    def load_training_zones(self, geojson_path: str) -> ee.FeatureCollection:
        import json
        
        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            buildings_list = []
            sol_nu_list = []
            savana_list = []
            water_list = []
            foret_galery_list = []
            culture_list = []
            forest_list = []
            
            for feature in geojson_data['features']:
                properties = feature.get('properties', {})
                
                class_id = properties.get('class')
                if class_id is None:
                    class_id = properties.get('Class')
                if class_id is None:
                    class_id = properties.get('classe')
                
                if class_id is not None:
                    class_id = int(class_id)
                else:
                    class_name = str(properties.get('name', properties.get('Name', ''))).lower()
                    if 'building' in class_name:
                        class_id = 0
                    elif 'sol_nu' in class_name or 'bare' in class_name:
                        class_id = 1
                    elif 'savana' in class_name:
                        class_id = 2
                    elif 'water' in class_name:
                        class_id = 3
                    elif 'galery' in class_name:
                        class_id = 4
                    elif 'culture' in class_name:
                        class_id = 5
                    elif 'forest' in class_name:
                        class_id = 6
                    else:
                        continue
                
                coords = feature['geometry']['coordinates']
                geom_type = feature['geometry']['type']
                
                if geom_type == 'Polygon':
                    ee_geom = ee.Geometry.Polygon(coords)
                elif geom_type == 'MultiPolygon':
                    ee_geom = ee.Geometry.MultiPolygon(coords)
                else:
                    continue
                
                ee_feature = ee.Feature(ee_geom, {'class': class_id})
                
                if class_id == 0:
                    buildings_list.append(ee_feature)
                elif class_id == 1:
                    sol_nu_list.append(ee_feature)
                elif class_id == 2:
                    savana_list.append(ee_feature)
                elif class_id == 3:
                    water_list.append(ee_feature)
                elif class_id == 4:
                    foret_galery_list.append(ee_feature)
                elif class_id == 5:
                    culture_list.append(ee_feature)
                elif class_id == 6:
                    forest_list.append(ee_feature)
            
            buildings = ee.FeatureCollection(buildings_list) if buildings_list else None
            sol_nu = ee.FeatureCollection(sol_nu_list) if sol_nu_list else None
            savana = ee.FeatureCollection(savana_list) if savana_list else None
            water = ee.FeatureCollection(water_list) if water_list else None
            foret_galery = ee.FeatureCollection(foret_galery_list) if foret_galery_list else None
            culture = ee.FeatureCollection(culture_list) if culture_list else None
            forest = ee.FeatureCollection(forest_list) if forest_list else None
            
            training = None
            for fc in [buildings, sol_nu, savana, water, foret_galery, culture, forest]:
                if fc is not None:
                    if training is None:
                        training = fc
                    else:
                        training = training.merge(fc)
            
            if training is None:
                st.error("Aucune zone d'entraînement chargée")
                return None
            
            for class_id in range(7):
                count = training.filter(ee.Filter.eq('class', class_id)).size().getInfo()
                if count > 0:
                    st.info(f"✅ {self.classes[class_id]['name']}: {count} zone(s)")
            
            return training
            
        except Exception as e:
            st.error(f"Erreur chargement: {str(e)}")
            return None
    
    def get_satellite_image(self, 
                           roi: ee.Geometry,
                           start_date: str,
                           end_date: str,
                           cloud_threshold: int = 30) -> ee.Image:  # MODIFIÉ: 10 → 30
        try:
            collection = ee.ImageCollection("COPERNICUS/S2_SR") \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold))
            
            size = collection.size().getInfo()
            if size == 0:
                st.error(f"Aucune image trouvée du {start_date} au {end_date}")
                return None
            
            st.info(f"📡 {size} image(s) Sentinel-2 trouvée(s)")
            
            def select_bands(image):
                return image.select(self.bands).copyProperties(image, image.propertyNames())
            
            collection_filtered = collection.map(select_bands)
            image = collection_filtered.median().clip(roi)
            
            st.success("✅ Image Sentinel-2 prête (bandes B2,B3,B4,B8)")
            
            return image
            
        except Exception as e:
            st.error(f"Erreur récupération image: {str(e)}")
            return None
    
    # ==================== FONCTION PRINCIPALE ====================
    
    def train_and_classify(self,
                          image: ee.Image,
                          training_zones: ee.FeatureCollection,
                          num_trees: int = 100,
                          training_ratio: float = 0.7,
                          scale: int = 30) -> dict:  # DÉJÀ SUR 30 (correct)
        """
        Entraîne et classifie le Random Forest
        """
        try:
            bands = self.bands
            
            training_data = image.select(bands).sampleRegions(
                collection=training_zones,
                properties=['class'],
                scale=scale
            )
            
            with_random = training_data.randomColumn('random')
            
            training_set = with_random.filter(ee.Filter.lt('random', training_ratio))
            validation_set = with_random.filter(ee.Filter.gte('random', training_ratio))
            
            train_size = training_set.size().getInfo()
            val_size = validation_set.size().getInfo()
            
            if train_size == 0:
                st.error("Aucun point d'entraînement généré")
                return None
            
            st.info(f"🎯 Points d'entraînement: {train_size}, Validation: {val_size} (scale={scale}m)")
            
            classifier = ee.Classifier.smileRandomForest(num_trees).train(
                features=training_set,
                classProperty='class',
                inputProperties=bands
            )
            
            validated = validation_set.classify(classifier)
            confusion_matrix = validated.errorMatrix('class', 'classification')
            
            # Récupérer les métriques
            overall_accuracy = confusion_matrix.accuracy().getInfo()
            kappa = confusion_matrix.kappa().getInfo()
            
            # Extraire correctement les valeurs des sous-listes
            producers_raw = confusion_matrix.producersAccuracy().getInfo()
            consumers_raw = confusion_matrix.consumersAccuracy().getInfo()
            
            producers = []
            consumers = []
            
            if isinstance(producers_raw, list):
                for item in producers_raw:
                    if isinstance(item, list) and len(item) > 0:
                        producers.append(item[0])
                    else:
                        producers.append(item)
            else:
                producers = producers_raw if isinstance(producers_raw, list) else [producers_raw]
            
            if isinstance(consumers_raw, list):
                for item in consumers_raw:
                    if isinstance(item, list) and len(item) > 0:
                        consumers.append(item[0])
                    else:
                        consumers.append(item)
            else:
                consumers = consumers_raw if isinstance(consumers_raw, list) else [consumers_raw]
            
            self.validation_metrics = {
                'overall_accuracy': overall_accuracy,
                'kappa': kappa,
                'producers_accuracy': producers,
                'consumers_accuracy': consumers,
                'training_samples': train_size,
                'validation_samples': val_size,
            }
            
            classified_image = image.select(bands).classify(classifier)
            self.classifier = classifier
            
            return self.validation_metrics
            
        except Exception as e:
            st.error(f"Erreur lors de la classification: {str(e)}")
            return None
    
    # ==================== FONCTIONS D'AFFICHAGE ====================
    
    def display_validation_metrics(self):
        if not self.validation_metrics:
            st.warning("Aucune métrique disponible")
            return
        
        st.markdown("### 📊 Validation du modèle Random Forest")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            acc = self.validation_metrics['overall_accuracy'] * 100
            st.metric("Exactitude globale", f"{acc:.2f}%")
        
        with col2:
            kappa = self.validation_metrics['kappa']
            if kappa > 0.8:
                kappa_text = "Excellent"
            elif kappa > 0.6:
                kappa_text = "Bon"
            elif kappa > 0.4:
                kappa_text = "Modéré"
            else:
                kappa_text = "Faible"
            st.metric("Indice Kappa", f"{kappa:.4f}", delta=kappa_text)
        
        with col3:
            st.metric(
                "Échantillons",
                f"{self.validation_metrics['training_samples']} train | {self.validation_metrics['validation_samples']} val"
            )
        
        st.markdown("#### Précision par classe (Producer & User Accuracy)")
        
        producers = self.validation_metrics['producers_accuracy']
        consumers = self.validation_metrics['consumers_accuracy']
        
        data = []
        for i in range(7):
            class_info = self.classes.get(i, {'name': f'Classe {i}'})
            
            prod_val = producers[i] if i < len(producers) else 0
            cons_val = consumers[i] if i < len(consumers) else 0
            
            try:
                prod_pct = float(prod_val) * 100
                cons_pct = float(cons_val) * 100
            except (ValueError, TypeError):
                prod_pct = 0
                cons_pct = 0
            
            data.append({
                "Classe": class_info['name'],
                "Producer Accuracy": f"{prod_pct:.1f}%",
                "User Accuracy": f"{cons_pct:.1f}%"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # Afficher les valeurs exactes comme dans Earth Engine
        with st.expander("📊 Détail des précisions (valeurs brutes)"):
            col_prod, col_cons = st.columns(2)
            with col_prod:
                st.markdown("**Producer Accuracy:**")
                for i, val in enumerate(producers):
                    class_name = self.classes.get(i, {}).get('name', f'Classe {i}')
                    st.write(f"{class_name}: {val:.4f}")
            with col_cons:
                st.markdown("**User Accuracy:**")
                for i, val in enumerate(consumers):
                    class_name = self.classes.get(i, {}).get('name', f'Classe {i}')
                    st.write(f"{class_name}: {val:.4f}")
    
    def display_classification_stats(self, classified_image: ee.Image, region: ee.Geometry, scale: int = 30):
        """
        Affiche uniquement les statistiques de répartition (sans graphique à barres redondant)
        """
        histogram = classified_image.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=region,
            scale=scale,
            bestEffort=True,
            maxPixels=1e9
        ).getInfo()
        
        if 'classification' not in histogram:
            st.warning("Aucune donnée disponible")
            return
        
        total_pixels = sum(histogram['classification'].values())
        
        st.markdown("### 📊 Répartition des classes")
        
        # Créer une liste des classes avec leur pourcentage
        class_items = []
        for class_id_str, count in histogram['classification'].items():
            class_id = int(class_id_str)
            class_info = self.classes.get(class_id, {'name': f'Classe {class_id}', 'color': '#ccc'})
            percentage = (count / total_pixels) * 100
            class_items.append((class_info, percentage))
        
        # Trier par pourcentage décroissant
        class_items.sort(key=lambda x: x[1], reverse=True)
        
        # Afficher en cartes
        cols = st.columns(4)
        for idx, (class_info, percentage) in enumerate(class_items):
            col_idx = idx % 4
            with cols[col_idx]:
                st.markdown(
                    f"""
                    <div style="text-align:center; margin:10px; padding:10px; 
                                border-radius:10px; background-color:{class_info['color']}20;">
                        <div style="background:{class_info['color']}; width:40px; height:40px; 
                                    border-radius:8px; margin:0 auto;"></div>
                        <strong>{class_info['name']}</strong><br>
                        <span style="font-size:24px; font-weight:bold;">{percentage:.1f}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        
        # Barre de progression globale (compacte, pas redondante)
        st.markdown("#### Vue d'ensemble")
        progress_html = "<div style='display: flex; height: 25px; border-radius: 5px; overflow: hidden; margin: 10px 0;'>"
        for class_info, percentage in class_items:
            if percentage > 0:
                progress_html += f"<div style='background-color: {class_info['color']}; width: {percentage}%; text-align: center; color: white; line-height: 25px; font-size: 11px;'>{class_info['name'][:3]}</div>"
        progress_html += "</div>"
        st.markdown(progress_html, unsafe_allow_html=True)
    
    def display_classification_map(self, classified_image: ee.Image, region: ee.Geometry):
        """
        Affiche UNIQUEMENT la carte de classification (pas de redondance)
        """
        vis_params = {
            'min': 0,
            'max': 6,
            'palette': self.palette
        }
        
        st.markdown("### 🗺️ Carte de classification")
        
        legend_html = '''
        <div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; 
                    background-color: white; padding: 10px; border-radius: 8px;
                    border: 2px solid #ccc; font-size: 12px;">
            <strong>Légende</strong><br>
            <span style="background-color:#FF6347; width:15px; height:15px; display:inline-block;"></span> Buildings<br>
            <span style="background-color:#D2B48C; width:15px; height:15px; display:inline-block;"></span> Sol nu<br>
            <span style="background-color:#32CD32; width:15px; height:15px; display:inline-block;"></span> Savane<br>
            <span style="background-color:#4169E1; width:15px; height:15px; display:inline-block;"></span> Eau<br>
            <span style="background-color:#006400; width:15px; height:15px; display:inline-block;"></span> Forêt galerie<br>
            <span style="background-color:#FFD700; width:15px; height:15px; display:inline-block;"></span> Culture<br>
            <span style="background-color:#228B22; width:15px; height:15px; display:inline-block;"></span> Forêt dense
        </div>
        '''
        
        try:
            bounds = region.bounds().getInfo()
            coords = bounds['coordinates'][0]
            lons = [coord[0] for coord in coords]
            lats = [coord[1] for coord in coords]
            center_lat = (min(lats) + max(lats)) / 2
            center_lon = (min(lons) + max(lons)) / 2
            
            m = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)
            
            map_id = classified_image.getMapId(vis_params)
            folium.TileLayer(
                tiles=map_id['tile_fetcher'].url_format,
                attr='Google Earth Engine',
                name='Classification Random Forest',
                overlay=True,
                opacity=0.85
            ).add_to(m)
            
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                attr='Google Satellite',
                name='Satellite',
                overlay=False
            ).add_to(m)
            
            m.get_root().html.add_child(folium.Element(legend_html))
            folium.LayerControl().add_to(m)
            folium_static(m, width=900, height=500)
            
        except Exception as e:
            st.warning(f"Affichage carte: {str(e)[:100]}")