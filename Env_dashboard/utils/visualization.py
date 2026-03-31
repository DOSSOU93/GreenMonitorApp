# utils/visualization.py
"""
Fonctions de visualisation
"""
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st


def plot_timeseries(years, values, title, indicator):
    """Crée un graphique de série temporelle"""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    clean_years = []
    clean_values = []
    for y, v in zip(years, values):
        if v is not None and v != 0:
            clean_years.append(y)
            clean_values.append(v)
    
    if clean_years:
        ax.plot(clean_years, clean_values, marker='o', linewidth=2, markersize=6, color='#4CAF50')
        ax.fill_between(clean_years, clean_values, alpha=0.3, color='#4CAF50')
        ax.set_xlabel('Annee', fontsize=12)
        ax.set_ylabel(title, fontsize=12)
        ax.set_title(f'Evolution temporelle - {indicator}', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%d'))
        
        if clean_years:
            ax.set_xlim(min(clean_years) - 0.5, max(clean_years) + 0.5)
        
        if len(clean_years) > 2:
            z = np.polyfit(clean_years, clean_values, 1)
            p = np.poly1d(z)
            ax.plot(clean_years, p(clean_years), '--', color='orange', alpha=0.7, label='Tendance')
            ax.legend()
        
        plt.tight_layout()
        return fig
    return None


def plot_seasonal(months, month_names, values, title, indicator, year):
    """Crée un graphique de variation saisonnière"""
    fig, ax = plt.subplots(figsize=(12, 5))
    
    display_values = []
    bar_colors = []
    
    for i, (m, v, name) in enumerate(zip(months, values, month_names)):
        if v is not None and v != 0:
            display_values.append(v)
            bar_colors.append('#4CAF50')
        else:
            display_values.append(0)
            bar_colors.append('#dddddd')
    
    if display_values:
        bars = ax.bar(months, display_values, color=bar_colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        ax.set_xlabel('Mois', fontsize=12)
        ax.set_ylabel(title, fontsize=12)
        ax.set_title(f'Variation saisonniere - {indicator} ({year})', fontsize=14, fontweight='bold')
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(month_names, rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(bottom=0)
        
        for i, (bar, v) in enumerate(zip(bars, display_values)):
            if v > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                        f'{v:.2f}', ha='center', va='bottom', fontsize=9)
            elif values[i] is None:
                ax.text(bar.get_x() + bar.get_width()/2., 0.05,
                        'N/A', ha='center', va='bottom', fontsize=8, color='red')
        
        plt.tight_layout()
        return fig
    return None


def display_color_legend(indicator_key, COLOR_PALETTES):
    """Affiche la légende des couleurs"""
    palette_config = COLOR_PALETTES.get(indicator_key.lower(), COLOR_PALETTES['ndvi'])
    if 'legend' in palette_config:
        cols = st.columns(len(palette_config['legend']))
        for i, item in enumerate(palette_config['legend']):
            with cols[i]:
                st.markdown(
                    f'<div style="text-align:center;"><div style="background: {item["color"]}; width: 25px; height: 15px; margin: 0 auto; border: 1px solid #666;"></div>'
                    f'<span style="font-size: 10px;">{item["label"]}</span></div>',
                    unsafe_allow_html=True
                )