# app.py
"""
Application principale - Tableau de bord environnemental
"""
import streamlit as st
import requests
import socket
import pandas as pd
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import ee
import folium
from streamlit_folium import folium_static
import os
from datetime import datetime
import tempfile

# Import des modules
from config import (
    COLOR_PALETTES, SENSORS_BY_INDICATOR, INDICATORS, 
    YEARS, MONTHS, LOGO_PATH
)
from utils import (
    load_engine, get_geotiff_url, calculate_change,
    calculate_indicator,
    calculate_stats, compute_timeseries, compute_seasonal,
    plot_timeseries, plot_seasonal,
    export_csv_data,
    coords_to_ee_polygon, format_area,
    get_satellite_image
)
from utils.export import export_pdf
from components import create_sidebar, create_map
from utils.ndvi import NDVIIndicator
from utils.random_forest_classifier import RandomForestClassifier
from utils.ndvi_alert import NDVIAlert

# ==================== VÉRIFICATION DE CONNEXION INTERNET ====================
def check_internet_connection(timeout=5):
    try:
        hosts = ["8.8.8.8", "1.1.1.1", "google.com", "earthengine.google.com"]
        for host in hosts:
            try:
                socket.setdefaulttimeout(timeout)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 443))
                return True
            except (socket.timeout, socket.error):
                continue
        try:
            response = requests.get("https://earthengine.google.com", timeout=timeout)
            if response.status_code == 200:
                return True
        except (requests.ConnectionError, requests.Timeout):
            pass
        return False
    except Exception:
        return False

if 'connection_ok' not in st.session_state:
    st.session_state.connection_ok = check_internet_connection()

if not st.session_state.connection_ok:
    st.set_page_config(layout="wide", initial_sidebar_state="expanded")
    st.markdown("""
    <div style="text-align:center; padding:50px;">
        <h1>🌐 Pas de connexion internet</h1>
        <p>Veuillez vous connecter à internet et rafraîchir la page.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# ==================== EN-TÊTE ====================
st.markdown("""
<div style="text-align: center; padding: 20px 0 10px 0;">
    <h1 style="color: #2E7D32; margin-bottom: 0;">🌿 GreenMonitor</h1>
    <h3 style="color: #555; margin-top: 0;">Tableau de bord de surveillance environnementale</h3>
    <p style="color: #777; font-size: 14px;">
        Suivi NDVI • NDWI • Température • Classification du sol • Alertes précoces • Export PDF
    </p>
    <hr style="margin: 10px 0;">
</div>
""", unsafe_allow_html=True)

# --------------------------
# Initialisation
# --------------------------
try:
    engine = load_engine()
    if engine is None:
        st.error("❌ Impossible de charger Google Earth Engine")
        st.stop()
except Exception as e:
    st.error(f"❌ Erreur Earth Engine: {str(e)}")
    st.stop()

# Session state
if 'polygon_coords' not in st.session_state:
    st.session_state.polygon_coords = None
if 'shapefile_name' not in st.session_state:
    st.session_state.shapefile_name = None
if 'polygon_bounds' not in st.session_state:
    st.session_state.polygon_bounds = None
if 'ee_polygon' not in st.session_state:
    st.session_state.ee_polygon = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'selected_indicator' not in st.session_state:
    st.session_state.selected_indicator = INDICATORS[0]
if 'selected_sensor' not in st.session_state:
    st.session_state.selected_sensor = list(SENSORS_BY_INDICATOR[INDICATORS[0]].keys())[0]
if 'show_results' not in st.session_state:
    st.session_state.show_results = False
if 'result_image' not in st.session_state:
    st.session_state.result_image = None
if 'result_image_name' not in st.session_state:
    st.session_state.result_image_name = None
if 'geotiff_url' not in st.session_state:
    st.session_state.geotiff_url = None
if 'timeseries_data' not in st.session_state:
    st.session_state.timeseries_data = None
if 'seasonal_data' not in st.session_state:
    st.session_state.seasonal_data = None
if 'fig_timeseries' not in st.session_state:
    st.session_state.fig_timeseries = None
if 'fig_seasonal' not in st.session_state:
    st.session_state.fig_seasonal = None
if 'classification_done' not in st.session_state:
    st.session_state.classification_done = False
if 'rf_classifier' not in st.session_state:
    st.session_state.rf_classifier = None
if 'classified_image' not in st.session_state:
    st.session_state.classified_image = None
if 'rf_scale' not in st.session_state:
    st.session_state.rf_scale = 30

# --------------------------
# Sidebar
# --------------------------
sidebar_params = create_sidebar(
    COLOR_PALETTES, INDICATORS, YEARS, MONTHS, SENSORS_BY_INDICATOR, LOGO_PATH
)

lat = sidebar_params['lat']
lon = sidebar_params['lon']
selected_indicator = sidebar_params['selected_indicator']
selected_sensor = sidebar_params['selected_sensor']
sensor_config = sidebar_params['sensor_config']
analysis_type = sidebar_params['analysis_type']
year = sidebar_params['year']
month = sidebar_params['month']
enable_comparison = sidebar_params['enable_comparison']
compare_year = sidebar_params['compare_year']
analysis_scale = sidebar_params['analysis_scale']
cloud_threshold = sidebar_params['cloud_threshold']
export_geotiff = sidebar_params['export_geotiff']
show_timeseries = sidebar_params['show_timeseries']
ts_start = sidebar_params['ts_start']
ts_end = sidebar_params['ts_end']
show_seasonal = sidebar_params['show_seasonal']
submit = sidebar_params['submit']

# --------------------------
# Créer la carte
# --------------------------
m = create_map(st.session_state, lat, lon)

# --------------------------
# Analyse
# --------------------------
if submit:
    if not st.session_state.polygon_coords:
        st.error("Veuillez d'abord charger un shapefile")
    else:
        with st.spinner("Analyse en cours..."):
            try:
                if not st.session_state.ee_polygon:
                    st.session_state.ee_polygon = coords_to_ee_polygon(st.session_state.polygon_coords)
                
                if st.session_state.ee_polygon:
                    area = st.session_state.ee_polygon.area().getInfo()
                    annual = (analysis_type == "Annuelle")
                    
                    # Définition de period_display (pour tous les cas)
                    if analysis_type == "Annuelle":
                        period_display = f"{year}"
                    else:
                        month_name = MONTHS[month - 1]
                        period_display = f"{month_name} {year}"
                    
                    # ==================== CLASSIFICATION RF ====================
                    if selected_indicator == "Classification RF":
                        geojson_path = os.path.join("data", "zones_entrainement.geojson")
                        
                        if not os.path.exists(geojson_path):
                            st.error(f"❌ Fichier non trouvé: `{geojson_path}`")
                        else:
                            if analysis_type == "Annuelle":
                                start_date = f"{year}-01-01"
                                end_date = f"{year}-12-31"
                            else:
                                start_date = f"{year}-{month:02d}-01"
                                end_date = f"{year}-{month:02d}-28"
                            
                            st.sidebar.markdown("---")
                            st.sidebar.markdown("### 🌲 Paramètres RF")
                            
                            num_trees = st.sidebar.number_input("Arbres", 50, 200, 100, 25)
                            rf_scale = st.sidebar.selectbox("Échelle", [10, 20, 30, 50, 100], index=2)
                            training_ratio = st.sidebar.slider("Ratio train", 0.5, 0.9, 0.7, 0.05)
                            
                            rf_classifier = RandomForestClassifier()
                            
                            with st.spinner("📡 Récupération image..."):
                                image = rf_classifier.get_satellite_image(
                                    roi=st.session_state.ee_polygon,
                                    start_date=start_date,
                                    end_date=end_date,
                                    cloud_threshold=cloud_threshold
                                )
                            
                            if image:
                                with st.spinner("📁 Chargement zones..."):
                                    training_zones = rf_classifier.load_training_zones(geojson_path)
                                
                                if training_zones:
                                    with st.spinner(f"🌲 Entraînement (scale={rf_scale}m)..."):
                                        metrics = rf_classifier.train_and_classify(
                                            image=image, training_zones=training_zones,
                                            num_trees=num_trees, training_ratio=training_ratio, scale=rf_scale
                                        )
                                    
                                    if metrics:
                                        classified = image.select(rf_classifier.bands).classify(rf_classifier.classifier)
                                        
                                        m.addLayer(classified, {'min': 0, 'max': 6, 'palette': rf_classifier.palette},
                                                  f"Classification RF ({period_display})")
                                        
                                        st.session_state.result_image = classified
                                        st.session_state.analysis_results = {
                                            'indicator': 'Classification RF', 'date': period_display,
                                            'area': format_area(area), 'sensor': selected_sensor,
                                            'cloud_threshold': cloud_threshold, 'mean': 0, 'std': 0, 'min': 0, 'max': 6
                                        }
                                        st.session_state.analysis_done = True
                                        st.session_state.show_results = True
                                        st.session_state.classification_done = True
                                        st.session_state.rf_classifier = rf_classifier
                                        st.session_state.classified_image = classified
                                        st.session_state.rf_scale = rf_scale
                                        
                                        st.success(f"✅ Classification terminée ({rf_scale}m, {num_trees} arbres)")
                    
                    # ==================== ALERTE NDVI ====================
                    elif selected_indicator == "Alerte NDVI":
                        st.info("🚨 Lancement du système d'alerte NDVI...")
                        
                        # Récupérer l'image NDVI
                        img, _ = get_satellite_image(st.session_state.ee_polygon, sensor_config, year, month, annual, cloud_threshold)
                        
                        if img is None:
                            st.error("Aucune image NDVI disponible")
                        else:
                            ndvi_result = calculate_indicator(img, sensor_config, "NDVI")
                            
                            if ndvi_result is None:
                                st.error("Erreur lors du calcul du NDVI")
                            else:
                                alert_system = NDVIAlert()
                                
                                # Sélection de la méthode dans la sidebar
                                st.sidebar.markdown("---")
                                st.sidebar.markdown("### 🚨 Paramètres d'alerte")
                                
                                alert_method = st.sidebar.radio(
                                    "Méthode d'alerte",
                                    ["Seuils absolus", "Anomalies NDVI (5 ans)"],
                                    key="alert_method_ndvi"
                                )
                                
                                if alert_method == "Seuils absolus":
                                    with st.spinner("Classification par seuils absolus..."):
                                        alert_map = alert_system.classify_absolute(ndvi_result, st.session_state.ee_polygon)
                                        stats = alert_system.get_stats(alert_map, st.session_state.ee_polygon, analysis_scale)
                                        
                                        m.addLayer(alert_map, {'min': 1, 'max': 5, 'palette': alert_system.alert_palette}, 
                                                  f"Alertes NDVI ({period_display})")
                                        
                                        st.session_state.result_image = alert_map
                                        st.session_state.analysis_results = {
                                            'indicator': 'Alerte NDVI',
                                            'date': period_display,
                                            'area': format_area(area),
                                            'sensor': selected_sensor,
                                            'cloud_threshold': cloud_threshold,
                                            'method': 'Seuils absolus',
                                            'stats': stats
                                        }
                                else:
                                    # Méthode des anomalies
                                    with st.spinner("Calcul des anomalies historiques (5 ans)..."):
                                        if analysis_type == "Annuelle":
                                            hist_start = f"{year-5}-01-01"
                                            hist_end = f"{year}-12-31"
                                        else:
                                            hist_start = f"{year-5}-{month:02d}-01"
                                            hist_end = f"{year}-{month:02d}-28"
                                        
                                        anomaly, hist_mean = alert_system.calculate_anomaly(
                                            ndvi_result, hist_start, hist_end, 
                                            st.session_state.ee_polygon, sensor_config
                                        )
                                        
                                        if anomaly is not None:
                                            alert_map = alert_system.classify_anomaly(anomaly, st.session_state.ee_polygon)
                                            stats = alert_system.get_stats(alert_map, st.session_state.ee_polygon, analysis_scale)
                                            
                                            m.addLayer(anomaly, {'min': -0.3, 'max': 0.3, 'palette': ['#D73027', '#FFFFBF', '#1A9850']},
                                                      f"Anomalies NDVI ({period_display})")
                                            m.addLayer(alert_map, {'min': 1, 'max': 5, 'palette': alert_system.alert_palette},
                                                      f"Alertes NDVI anomalies ({period_display})")
                                            
                                            st.session_state.result_image = alert_map
                                            st.session_state.analysis_results = {
                                                'indicator': 'Alerte NDVI',
                                                'date': period_display,
                                                'area': format_area(area),
                                                'sensor': selected_sensor,
                                                'cloud_threshold': cloud_threshold,
                                                'method': 'Anomalies NDVI',
                                                'stats': stats
                                            }
                                        else:
                                            st.error("Erreur calcul des anomalies")
                                
                                st.session_state.analysis_done = True
                                st.session_state.show_results = True
                                st.session_state.classification_done = False
                                st.success(f"✅ Alerte NDVI terminée - {alert_method}")
                    
                    # ==================== INDICATEURS STANDARDS (NDVI, NDWI, Temperature) ====================
                    else:
                        img, _ = get_satellite_image(st.session_state.ee_polygon, sensor_config, year, month, annual, cloud_threshold)
                        
                        if img is None:
                            st.error("Aucune image disponible")
                        else:
                            result = calculate_indicator(img, sensor_config, selected_indicator)
                            
                            if result:
                                palette = COLOR_PALETTES[selected_indicator.lower()]
                                date_label = f"{year}" if annual else f"{year}-{month:02d}"
                                vis = {'min': palette['min'], 'max': palette['max'], 'palette': palette['palette']}
                                m.addLayer(result, vis, f"{selected_indicator} ({date_label})")
                                
                                if export_geotiff:
                                    filename = f"{selected_indicator}_{year}{MONTHS[month-1][:3] if not annual else ''}.tif"
                                    st.session_state.result_image = result
                                    st.session_state.result_image_name = filename
                                    geotiff_url = get_geotiff_url(result, st.session_state.ee_polygon, filename, scale=analysis_scale)
                                    if geotiff_url:
                                        st.session_state.geotiff_url = geotiff_url
                                
                                stats = calculate_stats(result, st.session_state.ee_polygon, scale=analysis_scale)
                                
                                if stats:
                                    if selected_indicator == "NDVI":
                                        mean_val = stats.get('NDVI_mean', 0) or stats.get('NDVI', 0)
                                        std_val = stats.get('NDVI_stdDev', 0)
                                        min_val = stats.get('NDVI_min', 0)
                                        max_val = stats.get('NDVI_max', 0)
                                    elif selected_indicator == "NDWI":
                                        mean_val = stats.get('NDWI_mean', 0) or stats.get('NDWI', 0)
                                        std_val = stats.get('NDWI_stdDev', 0)
                                        min_val = stats.get('NDWI_min', 0)
                                        max_val = stats.get('NDWI_max', 0)
                                    else:
                                        mean_val = stats.get('temperature_mean', 0) or stats.get('temperature', 0)
                                        std_val = stats.get('temperature_stdDev', 0)
                                        min_val = stats.get('temperature_min', 0)
                                        max_val = stats.get('temperature_max', 0)
                                
                                if show_timeseries and ts_start:
                                    timeseries_years, timeseries_vals = compute_timeseries(
                                        st.session_state.ee_polygon, selected_indicator, sensor_config, ts_start, ts_end, cloud_threshold
                                    )
                                    st.session_state.timeseries_data = pd.DataFrame({"Annee": timeseries_years, "Valeur": timeseries_vals})
                                    st.session_state.fig_timeseries = plot_timeseries(timeseries_years, timeseries_vals, selected_indicator, selected_indicator)
                                
                                if show_seasonal:
                                    seasonal_months, month_names, seasonal_vals = compute_seasonal(
                                        st.session_state.ee_polygon, selected_indicator, sensor_config, year, cloud_threshold
                                    )
                                    st.session_state.seasonal_data = pd.DataFrame({"Mois": seasonal_months, "Nom": month_names, "Valeur": seasonal_vals})
                                    st.session_state.fig_seasonal = plot_seasonal(seasonal_months, month_names, seasonal_vals, selected_indicator, selected_indicator, year)
                                
                                st.session_state.analysis_results = {
                                    'indicator': selected_indicator, 'date': period_display, 'area': format_area(area),
                                    'sensor': selected_sensor, 'cloud_threshold': cloud_threshold,
                                    'mean': mean_val, 'std': std_val, 'min': min_val, 'max': max_val
                                }
                                st.session_state.analysis_done = True
                                st.session_state.show_results = True
                                st.session_state.classification_done = False
                            
            except Exception as e:
                st.error(f"Erreur: {str(e)[:100]}")

# --------------------------
# AFFICHAGE DES RÉSULTATS ALERTE NDVI
# --------------------------
if (st.session_state.analysis_done and st.session_state.show_results and 
    st.session_state.analysis_results.get('indicator') == "Alerte NDVI" and not st.session_state.classification_done):
    
    st.markdown("---")
    st.markdown("## 🚨 Système d'Alerte NDVI")
    
    res = st.session_state.analysis_results
    alert_system = NDVIAlert()
    
    # Informations
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Méthode", res.get('method', 'N/A'))
    with col2:
        st.metric("Période", res['date'])
    with col3:
        st.metric("Surface", res['area'])
    with col4:
        st.metric("Capteur", res['sensor'])
    
    st.markdown("---")
    
    # Légende
    alert_system.display_legend()
    
    st.markdown("---")
    
    # Statistiques des alertes
    if 'stats' in res and res['stats']:
        alert_system.display_stats(res['stats'])
        alert_system.display_recommendations(res['stats'])
    
    st.markdown("---")
    
    # Export des résultats
    st.markdown("### 💾 Export des résultats")
    
    col_csv, col_pdf = st.columns(2)
    
    with col_csv:
        if 'stats' in res and res['stats']:
            export_data = []
            for level, pct in res['stats'].items():
                export_data.append({"Niveau d'alerte": level, "Pourcentage": f"{pct:.1f}%"})
            export_df = pd.DataFrame(export_data)
            st.download_button(
                "📊 CSV",
                data=export_df.to_csv(index=False, encoding='utf-8-sig'),
                file_name=f"alerte_ndvi_{res['date']}.csv",
                width='stretch'
            )
        else:
            st.download_button("📊 CSV", data="", disabled=True, width='stretch')
    
    with col_pdf:
        # Utiliser la fonction export_pdf modifiée
        pdf_path = export_pdf(
            results=res,
            timeseries_df=None,
            seasonal_df=None,
            COLOR_PALETTES=COLOR_PALETTES,
            indicator_name="Alerte NDVI"
        )
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "📄 PDF",
                    data=f,
                    file_name=f"rapport_alerte_ndvi_{res['date']}.pdf",
                    width='stretch'
                )
        else:
            st.download_button("📄 PDF", data="", disabled=True, width='stretch')
    
    st.markdown("---")
    st.info("💡 La carte des alertes est visible sur la carte principale ci-dessous")

# --------------------------
# AFFICHAGE DES RÉSULTATS CLASSIFICATION RF
# --------------------------
if (st.session_state.analysis_done and st.session_state.show_results and 
    st.session_state.analysis_results.get('indicator') == "Classification RF" and st.session_state.classification_done):
    
    st.markdown("---")
    st.markdown("## 🌲 Classification Random Forest")
    
    if st.session_state.rf_classifier is not None and st.session_state.classified_image is not None:
        rf_classifier = st.session_state.rf_classifier
        classified = st.session_state.classified_image
        
        # Métriques de validation
        if hasattr(rf_classifier, 'validation_metrics') and rf_classifier.validation_metrics:
            metrics = rf_classifier.validation_metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Exactitude globale", f"{metrics['overall_accuracy']*100:.1f}%")
            with col2:
                kappa = metrics['kappa']
                st.metric("Indice Kappa", f"{kappa:.3f}")
            with col3:
                st.metric("Échantillons", f"{metrics['training_samples']} train | {metrics['validation_samples']} val")
        
        # Graphique de répartition
        st.markdown("### 📊 Répartition des classes")
        
        try:
            histogram = classified.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=st.session_state.ee_polygon,
                scale=30,
                bestEffort=True,
                maxPixels=1e9
            ).getInfo()
        except Exception as e:
            st.warning(f"Erreur calcul histogramme: {str(e)[:100]}")
            histogram = None
        
        if histogram and 'classification' in histogram:
            total_pixels = sum(histogram['classification'].values())
            class_items = []
            for class_id_str, count in histogram['classification'].items():
                class_id = int(class_id_str)
                class_info = rf_classifier.classes.get(class_id, {'name': f'Classe {class_id}', 'color': '#ccc'})
                percentage = (count / total_pixels) * 100
                class_items.append((class_info['name'], percentage, class_info['color']))
            
            class_items.sort(key=lambda x: x[1], reverse=True)
            
            fig, ax = plt.subplots(figsize=(10, 5))
            names = [item[0] for item in class_items]
            pcts = [item[1] for item in class_items]
            colors = [item[2] for item in class_items]
            
            bars = ax.barh(names, pcts, color=colors, edgecolor='black', linewidth=0.5)
            ax.set_xlabel('Pourcentage (%)', fontsize=12)
            ax.set_title('Occupation du sol', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='x')
            for bar, pct in zip(bars, pcts):
                ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, f'{pct:.1f}%', va='center', fontsize=10)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
        else:
            st.info("Aucune donnée de répartition disponible")
        
        st.info("💡 La carte de classification est visible sur la carte principale ci-dessous (calque 'Classification RF')")
        
        # Export des résultats
        st.markdown("---")
        st.markdown("### 💾 Export des résultats")
        
        col_csv, col_pdf = st.columns(2)
        
        with col_csv:
            if histogram and 'classification' in histogram:
                export_data = []
                for name, pct, color in class_items:
                    export_data.append({"Classe": name, "Pourcentage": f"{pct:.1f}%", "Couleur": color})
                export_df = pd.DataFrame(export_data)
                st.download_button(
                    "📊 CSV",
                    data=export_df.to_csv(index=False, encoding='utf-8-sig'),
                    file_name=f"rf_classification_{st.session_state.analysis_results.get('date', 'unknown')}.csv",
                    width='stretch'
                )
            else:
                st.download_button(
                    "📊 CSV",
                    data=pd.DataFrame({"Information": ["Aucune donnée disponible"]}).to_csv(index=False),
                    file_name=f"rf_classification_{st.session_state.analysis_results.get('date', 'unknown')}.csv",
                    width='stretch',
                    disabled=True
                )
        
        with col_pdf:
            try:
                pdf_path = export_pdf(
                    results=st.session_state.analysis_results,
                    timeseries_df=None,
                    seasonal_df=None,
                    COLOR_PALETTES=COLOR_PALETTES,
                    classified_image=classified,
                    region=st.session_state.ee_polygon,
                    palette=rf_classifier.palette
                )
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "📄 PDF",
                            data=f,
                            file_name=f"rapport_RF_{st.session_state.analysis_results.get('date', 'unknown')}.pdf",
                            width='stretch'
                        )
                else:
                    st.download_button("📄 PDF", data="", disabled=True, width='stretch')
            except Exception as e:
                st.error(f"Erreur génération PDF: {str(e)[:100]}")
                st.download_button("📄 PDF", data="", disabled=True, width='stretch')

# --------------------------
# AFFICHAGE DES RÉSULTATS STANDARDS (NDVI, NDWI, Temperature)
# --------------------------
if (st.session_state.analysis_done and st.session_state.show_results and 
    st.session_state.analysis_results.get('indicator') not in ["Classification RF", "Alerte NDVI"] and not st.session_state.classification_done):
    
    res = st.session_state.analysis_results
    st.markdown("### 📈 Résultats")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**{res['indicator']}** | {res['date']}")
        st.markdown(f"Surface: {res['area']}")
    with col2:
        st.markdown(f"Moyenne: {res['mean']:.3f} | Min: {res['min']:.3f}")
    with col3:
        st.markdown(f"Max: {res['max']:.3f} | Écart-type: {res['std']:.3f}")
    
    st.markdown("---")
    
    col_graph1, col_graph2 = st.columns(2)
    with col_graph1:
        if show_timeseries and st.session_state.fig_timeseries:
            st.pyplot(st.session_state.fig_timeseries)
            plt.close(st.session_state.fig_timeseries)
    with col_graph2:
        if show_seasonal and st.session_state.fig_seasonal:
            st.pyplot(st.session_state.fig_seasonal)
            plt.close(st.session_state.fig_seasonal)
    
    st.markdown("---")
    
    col_csv, col_pdf, col_tif = st.columns(3)
    with col_csv:
        csv_data = export_csv_data(res, st.session_state.timeseries_data, st.session_state.seasonal_data)
        st.download_button("📊 CSV", data=csv_data, file_name=f"{res['indicator']}_{res['date']}.csv", width='stretch')
    with col_pdf:
        pdf_path = export_pdf(
            results=res,
            timeseries_df=st.session_state.timeseries_data,
            seasonal_df=st.session_state.seasonal_data,
            ts_start=ts_start if show_timeseries else None,
            ts_end=ts_end if show_timeseries else None,
            seasonal_year=year if show_seasonal else None,
            fig_ts=st.session_state.fig_timeseries,
            fig_seas=st.session_state.fig_seasonal,
            COLOR_PALETTES=COLOR_PALETTES,
            geotiff_url=st.session_state.geotiff_url,
            geotiff_filename=st.session_state.result_image_name,
            indicator_name=selected_indicator
        )
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button("📄 PDF", data=f, file_name=f"rapport_{res['indicator']}_{res['date']}.pdf", width='stretch')
        else:
            st.download_button("📄 PDF", data="", disabled=True, width='stretch')
    with col_tif:
        if st.session_state.geotiff_url:
            st.markdown(f'<a href="{st.session_state.geotiff_url}" download="{st.session_state.result_image_name}"><button style="width:100%; padding:8px; background:#4CAF50; color:white; border:none; border-radius:5px;">🗺️ GeoTIFF</button></a>', unsafe_allow_html=True)
        else:
            st.button("🗺️ GeoTIFF", disabled=True, width='stretch')
    
    st.markdown("---")
    
    if st.button("❌ Fermer", width='stretch'):
        st.session_state.show_results = False
        st.session_state.classification_done = False
        st.rerun()

# --------------------------
# Carte principale
# --------------------------
st.components.v1.html(m.to_html(), height=600)

# Aide compacte
with st.expander("ℹ️ Aide"):
    st.markdown("""
    **Utilisation rapide:**
    1. Chargez un shapefile (ZIP)
    2. Choisissez NDVI, NDWI, Température, Classification RF ou Alerte NDVI
    3. Sélectionnez la période
    4. Cliquez "Lancer l'analyse"
    
    **Alerte NDVI:**
    - **Seuils absolus**: Classification directe (Normal >0.5, Vigilance 0.3-0.5, Alerte 0.2-0.3, Critique <0.2)
    - **Anomalies NDVI**: Compare avec l'historique 5 ans (recommandé)
    - Les zones d'eau et sol nu (NDVI ≤ 0) sont exclues de l'analyse (affichées en gris)
    
    **Classification RF:** Utilisez échelle 30m pour un calcul rapide (10m = très lent)
    """)