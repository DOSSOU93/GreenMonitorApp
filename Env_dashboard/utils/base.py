# utils/base.py
"""
Classe de base pour tous les indicateurs
"""
from abc import ABC, abstractmethod
import ee
import streamlit as st


class BaseIndicator(ABC):
    """Classe abstraite pour les indicateurs environnementaux"""
    
    def __init__(self, name, palette_config):
        self.name = name
        self.palette = palette_config['palette']
        self.min_value = palette_config['min']
        self.max_value = palette_config['max']
        self.legend = palette_config.get('legend', [])
        
    @abstractmethod
    def calculate(self, image, sensor_config):
        """Calcule l'indicateur à partir de l'image"""
        pass
    
    @abstractmethod
    def interpret(self, value):
        """Interprète la valeur de l'indicateur"""
        pass
    
    def get_visualization_params(self):
        """Retourne les paramètres de visualisation"""
        return {
            'min': self.min_value,
            'max': self.max_value,
            'palette': self.palette
        }
    
    def display_legend(self):
        """Affiche la légende de l'indicateur"""
        if self.legend:
            cols = st.columns(len(self.legend))
            for i, item in enumerate(self.legend):
                with cols[i]:
                    st.markdown(
                        f'<div style="text-align:center;">'
                        f'<div style="background: {item["color"]}; width: 25px; height: 15px; margin: 0 auto; border: 1px solid #666;"></div>'
                        f'<span style="font-size: 10px;">{item["label"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )