# components/results.py
"""
Composant d'affichage des résultats
"""
import streamlit as st
import matplotlib.pyplot as plt
from utils.visualization import display_color_legend, plot_timeseries, plot_seasonal
from utils.export import export_csv_data, export_pdf
from utils.indicators import interpret_value


def display_results(res, st_session_state, COLOR_PALETTES, show_timeseries, show_seasonal, 
                    year, ts_start, ts_end):
    """Affiche les résultats de l'analyse"""
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Indicateur", res['indicator'])
        st.metric("Moyenne", f"{res['mean']:.3f}")
    with col2:
        st.metric("Periode", res['date'])
        st.metric("Minimum", f"{res['min']:.3f}")
    with col3:
        st.metric("Superficie", res['area'])
        st.metric("Maximum", f"{res['max']:.3f}")
    with col4:
        st.metric("Ecart-type", f"{res['std']:.3f}")
        st.metric("Seuil nuages", f"{res['cloud_threshold']}%")
        interpretation, _ = interpret_value(res['indicator'], res['mean'])
        st.markdown(f"**{interpretation}**")
    
    if res.get('comparison') and res['comparison'] is not None:
        comp = res['comparison']
        variation = res['mean'] - comp['mean']
        var_color = "green" if variation > 0 else "red" if variation < 0 else "gray"
        st.markdown(f"**Comparaison {comp['year']}:** {comp['mean']:.3f} | Variation: <span style='color:{var_color};'>{variation:+.3f}</span>", unsafe_allow_html=True)
    
    display_color_legend(res['indicator'].lower(), COLOR_PALETTES)
    
    st.markdown("---")
    
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        if show_timeseries and st_session_state.get('timeseries_data') is not None and ts_start is not None:
            st.markdown(f"### Evolution annuelle ({ts_start}-{ts_end})")
            if st_session_state.get('fig_timeseries') is not None:
                st.pyplot(st_session_state.fig_timeseries)
                plt.close(st_session_state.fig_timeseries)
            else:
                st.line_chart(st_session_state.timeseries_data.set_index("Annee"))
    
    with col_graph2:
        if show_seasonal and st_session_state.get('seasonal_data') is not None:
            st.markdown(f"### Variation saisonniere ({year})")
            if st_session_state.get('fig_seasonal') is not None:
                st.pyplot(st_session_state.fig_seasonal)
                plt.close(st_session_state.fig_seasonal)
            else:
                st.bar_chart(st_session_state.seasonal_data.set_index("Nom"))
    
    st.markdown("---")
    
    # Export
    col_csv, col_pdf, col_tif = st.columns(3)
    
    with col_csv:
        csv_data = export_csv_data(res, st_session_state.get('timeseries_data'), st_session_state.get('seasonal_data'))
        st.download_button("CSV", data=csv_data, file_name=f"{res['indicator']}_{res['date']}.csv", width='stretch')
    
    with col_pdf:
        pdf_path = export_pdf(
            res, 
            st_session_state.get('timeseries_data'), 
            st_session_state.get('seasonal_data'),
            ts_start if show_timeseries else None,
            ts_end if show_timeseries else None,
            year if show_seasonal else None,
            st_session_state.get('fig_timeseries'),
            st_session_state.get('fig_seasonal'),
            COLOR_PALETTES
        )
        if pdf_path:
            with open(pdf_path, "rb") as f:
                st.download_button("PDF", data=f, file_name=f"rapport_{res['indicator']}_{res['date']}.pdf", width='stretch')
    
    with col_tif:
        if st_session_state.get('geotiff_url'):
            st.markdown(f'<a href="{st_session_state.geotiff_url}" download="{st_session_state.result_image_name}"><button style="width:100%; padding:8px; background:#4CAF50; color:white; border:none; border-radius:5px;">GeoTIFF</button></a>', unsafe_allow_html=True)
        else:
            st.button("GeoTIFF", disabled=True, width='stretch')
    
    st.markdown("---")
    
    if st.button("Fermer", width='stretch'):
        st.session_state.show_results = False
        st.rerun()