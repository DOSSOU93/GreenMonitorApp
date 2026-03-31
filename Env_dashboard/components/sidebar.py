# components/sidebar.py
"""
Composant de la sidebar
"""
import streamlit as st
import tempfile
import os
import zipfile
import geopandas as gpd
from PIL import Image
from utils.geometry import get_polygon_bounds


def create_sidebar(COLOR_PALETTES, INDICATORS, YEARS, MONTHS, SENSORS_BY_INDICATOR, LOGO_PATH):
    """Crée la sidebar de l'application"""
    
    with st.sidebar:
        # Logo
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH)
            logo.thumbnail((200, 200))
            st.sidebar.image(logo, width=180)
        else:
            st.sidebar.warning("Logo non trouve")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("**Coordonnees**")
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", value=6.5, format="%.4f", key="lat")
        with col2:
            lon = st.number_input("Longitude", value=1.2, format="%.4f", key="lon")
        
        st.markdown("<hr style='margin: 5px 0'>", unsafe_allow_html=True)
        
        st.markdown("**Zone d'etude**")
        uploaded_zip = st.file_uploader("Shapefile (ZIP)", type=['zip'], key="shp")
        
        if uploaded_zip:
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_path = os.path.join(tmpdir, "shapefile.zip")
                    with open(zip_path, 'wb') as f:
                        f.write(uploaded_zip.getbuffer())
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(tmpdir)
                    shp_files = [os.path.join(root, f) for root, dirs, files in os.walk(tmpdir) for f in files if f.endswith('.shp')]
                    if shp_files:
                        gdf = gpd.read_file(shp_files[0])
                        if len(gdf) > 0 and gdf.geometry.iloc[0].geom_type == 'Polygon':
                            coords = list(gdf.geometry.iloc[0].exterior.coords)
                            coords_latlon = [[coord[1], coord[0]] for coord in coords]
                            st.session_state.polygon_coords = coords_latlon
                            st.session_state.shapefile_name = os.path.basename(shp_files[0])
                            center = get_polygon_bounds(coords_latlon)
                            st.session_state.polygon_bounds = center
                            st.success(f"Charge: {st.session_state.shapefile_name}")
            except Exception as e:
                st.error(f"Erreur: {e}")
        
        if st.session_state.get('polygon_coords'):
            if st.button("Effacer", width='stretch', key="clear"):
                for key in ['polygon_coords', 'shapefile_name', 'polygon_bounds', 'ee_polygon', 
                           'analysis_results', 'analysis_done', 'show_results', 'result_image', 
                           'geotiff_url', 'timeseries_data', 'seasonal_data']:
                    st.session_state[key] = None if key not in ['analysis_done', 'show_results'] else False
                st.rerun()
        
        st.markdown("<hr style='margin: 5px 0'>", unsafe_allow_html=True)
        
        # Indicateur
        with st.expander("Indicateur", expanded=True):
            selected_indicator = st.selectbox(
                "Indicateur",
                INDICATORS,
                index=INDICATORS.index(st.session_state.get('selected_indicator', INDICATORS[0])) if st.session_state.get('selected_indicator') in INDICATORS else 0,
                key="indicator"
            )
            st.session_state.selected_indicator = selected_indicator
            
            available_sensors = list(SENSORS_BY_INDICATOR[selected_indicator].keys())
            selected_sensor_name = st.radio(
                "Capteur",
                available_sensors,
                index=0,
                key="sensor"
            )
            st.session_state.selected_sensor = selected_sensor_name
            sensor_config = SENSORS_BY_INDICATOR[selected_indicator][selected_sensor_name]
        
        # Periode
        with st.expander("Periode", expanded=True):
            analysis_type = st.radio("Type d'analyse", ["Mensuelle", "Annuelle"], horizontal=True, key="type")
            
            if analysis_type == "Mensuelle":
                col1, col2 = st.columns(2)
                with col1:
                    year = st.selectbox("Annee", YEARS, index=YEARS.index(2023), key="y")
                with col2:
                    month_name = st.selectbox("Mois", MONTHS, index=5, key="m")
                    month = MONTHS.index(month_name) + 1
            else:
                year = st.selectbox("Annee", YEARS, index=YEARS.index(2023), key="y2")
                month = None
        
        # Comparaison
        enable_comparison = st.checkbox("Comparer avec une autre annee", key="comp")
        compare_year = None
        if enable_comparison:
            compare_year = st.selectbox("Annee de reference", YEARS, index=YEARS.index(2020), key="comp_y")
        
        # Options
        with st.expander("Options", expanded=False):
            resolution = st.select_slider(
                "Resolution",
                options=["Basse (1000m)", "Moyenne (500m)", "Haute (100m)"],
                value="Moyenne (500m)",
                key="res"
            )
            scale_map = {"Basse (1000m)": 1000, "Moyenne (500m)": 500, "Haute (100m)": 100}
            analysis_scale = scale_map[resolution]
            
            st.markdown("**Filtre nuages**")
            cloud_threshold = st.slider(
                "Seuil de couverture nuageuse (%)",
                min_value=0,
                max_value=100,
                value=20,
                step=5,
                key="cloud_threshold",
                help="Pourcentage de nuages maximal accepte dans une image. 20% est un bon compromis."
            )
            
            export_geotiff = st.checkbox("Exporter GeoTIFF", key="geotiff")
            
            st.markdown("**Graphiques**")
            show_timeseries = st.checkbox("Evolution annuelle (plage personnalisable)", value=False)
            
            if show_timeseries:
                col1, col2 = st.columns(2)
                with col1:
                    ts_start = st.number_input("Annee debut", min_value=2000, max_value=2024, value=2017, key="ts_start")
                with col2:
                    ts_end = st.number_input("Annee fin", min_value=2001, max_value=2025, value=2024, key="ts_end")
            else:
                ts_start, ts_end = None, None
            
            show_seasonal = st.checkbox("Variation saisonniere (annee selectionnee)", value=True)
        
        st.markdown("<hr style='margin: 5px 0'>", unsafe_allow_html=True)
        
        submit = st.button("Lancer l'analyse", type="primary", width='stretch', key="run")
    
    return {
        'lat': lat,
        'lon': lon,
        'selected_indicator': selected_indicator,
        'selected_sensor': selected_sensor_name,
        'sensor_config': sensor_config,
        'analysis_type': analysis_type,
        'year': year,
        'month': month,
        'enable_comparison': enable_comparison,
        'compare_year': compare_year,
        'analysis_scale': analysis_scale,
        'cloud_threshold': cloud_threshold,
        'export_geotiff': export_geotiff,
        'show_timeseries': show_timeseries,
        'ts_start': ts_start,
        'ts_end': ts_end,
        'show_seasonal': show_seasonal,
        'submit': submit
    }