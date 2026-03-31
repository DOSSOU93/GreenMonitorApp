# utils/export.py
"""
Fonctions d'export
"""
import os
import tempfile
import pandas as pd
import io
import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from .indicators import interpret_value


def fig_to_bytes(fig):
    """Convertit une figure matplotlib en bytes"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    return buf


def export_pdf(results, timeseries_df=None, seasonal_df=None, ts_start=None, ts_end=None, 
               seasonal_year=None, fig_ts=None, fig_seas=None, COLOR_PALETTES=None,
               geotiff_url=None, geotiff_filename=None, indicator_name=None,
               ee_image=None, region=None, classified_image=None, palette=None):
    """
    Exporte les résultats au format PDF
    """
    try:
        path = os.path.join(tempfile.gettempdir(), f"rapport_{results['indicator']}_{results['date']}.pdf")
        doc = SimpleDocTemplate(path, pagesize=A4)
        styles = getSampleStyleSheet()
        content = []
        
        # Titre
        content.append(Paragraph(f"Rapport d'analyse environnementale - {results['indicator']}", styles["Title"]))
        content.append(Spacer(1, 12))
        
        # Informations générales (adaptées selon le type d'indicateur)
        content.append(Paragraph("Informations générales", styles["Heading2"]))
        content.append(Spacer(1, 6))
        
        # Adapter les informations pour l'alerte NDVI
        if results['indicator'] == "Alerte NDVI":
            info_data = [
                ["Indicateur", results.get('indicator', 'N/A')],
                ["Méthode", results.get('method', 'N/A')],
                ["Période", results.get('date', 'N/A')],
                ["Surface", results.get('area', 'N/A')],
                ["Capteur", results.get('sensor', 'N/A')],
                ["Seuil nuages", f"{results.get('cloud_threshold', 20)}%"],
            ]
        else:
            info_data = [
                ["Indicateur", results.get('indicator', 'N/A')],
                ["Période", results.get('date', 'N/A')],
                ["Surface", results.get('area', 'N/A')],
                ["Capteur", results.get('sensor', 'N/A')],
                ["Seuil nuages", f"{results.get('cloud_threshold', 20)}%"],
                ["Moyenne", f"{results.get('mean', 0):.3f}"],
                ["Écart-type", f"{results.get('std', 0):.3f}"],
                ["Minimum", f"{results.get('min', 0):.3f}"],
                ["Maximum", f"{results.get('max', 0):.3f}"]
            ]
        
        table = Table(info_data, colWidths=[100, 150])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        content.append(table)
        content.append(Spacer(1, 12))
        
        # Interprétation (uniquement pour les indicateurs standards)
        if results['indicator'] not in ["Alerte NDVI", "Classification RF"]:
            interpretation, _ = interpret_value(results['indicator'], results.get('mean', 0))
            content.append(Paragraph(f"Interprétation: {interpretation}", styles["Normal"]))
            content.append(Spacer(1, 12))
        
        # Statistiques d'alerte si disponibles
        if 'stats' in results and results['stats']:
            content.append(Paragraph("Distribution des alertes", styles["Heading2"]))
            content.append(Spacer(1, 6))
            alert_data = [["Niveau d'alerte", "Pourcentage"]]
            for level, pct in results['stats'].items():
                alert_data.append([level, f"{pct:.1f}%"])
            alert_table = Table(alert_data, colWidths=[150, 100])
            alert_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            content.append(alert_table)
            content.append(Spacer(1, 12))
        
        # Légende des couleurs
        if COLOR_PALETTES and results['indicator'] not in ["Alerte NDVI", "Classification RF"]:
            indicator_key = results['indicator'].lower()
            if indicator_key in COLOR_PALETTES and 'legend' in COLOR_PALETTES[indicator_key]:
                content.append(Paragraph("Légende des couleurs", styles["Heading2"]))
                content.append(Spacer(1, 6))
                legend_data = [["Valeur", "Interprétation"]]
                for item in COLOR_PALETTES[indicator_key]['legend']:
                    legend_data.append([f"{item['value']:.1f}", item['label']])
                legend_table = Table(legend_data, colWidths=[80, 200])
                legend_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                content.append(legend_table)
                content.append(Spacer(1, 12))
        
        # Graphiques
        if timeseries_df is not None and fig_ts is not None:
            content.append(Paragraph(f"Évolution annuelle ({ts_start}-{ts_end})", styles["Heading2"]))
            content.append(Spacer(1, 6))
            img_bytes = fig_to_bytes(fig_ts)
            img = RLImage(img_bytes, width=450, height=250)
            content.append(img)
            content.append(Spacer(1, 12))
        
        if seasonal_df is not None and fig_seas is not None:
            content.append(Paragraph(f"Variation saisonnière ({seasonal_year})", styles["Heading2"]))
            content.append(Spacer(1, 6))
            img_bytes = fig_to_bytes(fig_seas)
            img = RLImage(img_bytes, width=450, height=250)
            content.append(img)
            content.append(Spacer(1, 12))
        
        doc.build(content)
        return path
    except Exception as e:
        st.error(f"Erreur PDF: {e}")
        return None


def export_csv_data(results, timeseries_df=None, seasonal_df=None):
    """Exporte les données au format CSV"""
    if timeseries_df is not None and seasonal_df is not None:
        return timeseries_df.to_csv(index=False) + "\n" + seasonal_df.to_csv(index=False)
    elif timeseries_df is not None:
        return timeseries_df.to_csv(index=False)
    else:
        # Pour l'alerte NDVI, exporter les stats
        if 'stats' in results and results['stats']:
            df = pd.DataFrame([{"Niveau d'alerte": k, "Pourcentage": f"{v:.1f}%"} for k, v in results['stats'].items()])
            return df.to_csv(index=False)
        return pd.DataFrame([results]).to_csv(index=False)