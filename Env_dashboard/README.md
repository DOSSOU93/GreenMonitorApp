# 🌿 GreenMonitor - Tableau de bord de surveillance environnementale

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://earthengine.google.com)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

## 📋 Table des matières
- [Présentation](#présentation)
- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Structure du projet](#structure-du-projet)
- [Dépendances](#dépendances)
- [Dépannage](#dépannage)
- [Auteurs](#auteurs)

---

## 🎯 Présentation

**GreenMonitor** est une application interactive de surveillance environnementale développée avec Streamlit et Google Earth Engine. Elle permet aux décideurs locaux, gestionnaires de l'environnement et chercheurs de suivre en temps réel l'état de la végétation, des ressources en eau et des températures, avec un système d'alerte précoce des dégradations.

### Objectifs
- 📊 **Surveillance multi-indicateurs** : NDVI, NDWI, Température
- 🌍 **Classification du sol** : Cartographie de l'occupation du sol (7 classes)
- 🚨 **Détection précoce** : Alertes NDVI par seuils absolus ou anomalies historiques
- 📈 **Analyse temporelle** : Évolution annuelle et variation saisonnière
- 📄 **Export de rapports** : Génération de rapports PDF et CSV

---

## ⚡ Fonctionnalités

### 1. Indicateurs environnementaux
| Indicateur | Description | Capteurs |
|------------|-------------|----------|
| **NDVI** | Indice de végétation | Sentinel-2, Landsat, MODIS |
| **NDWI** | Indice d'eau | Sentinel-2, Landsat |
| **Température** | Température de surface | Landsat |
| **Classification RF** | Occupation du sol (7 classes) | Sentinel-2 |
| **Alerte NDVI** | Détection précoce des dégradations | Sentinel-2, Landsat |

### 2. Classes d'occupation du sol (Random Forest)
| Classe | Code | Couleur |
|--------|------|--------|
| Buildings | 0 | 🔴 Rouge |
| Sol nu | 1 | 🟤 Marron |
| Savane | 2 | 🟡 Jaune |
| Eau | 3 | 🔵 Bleu |
| Forêt galerie | 4 | 🟢 Vert |
| Culture | 5 | 🟡 Or |
| Forêt dense | 6 | 🌲 Vert foncé |

### 3. Niveaux d'alerte NDVI
| Niveau | NDVI | Signification | Action |
|--------|------|---------------|--------|
| 🟢 **Normal** | > 0.5 | Végétation saine | Surveillance routine |
| 🟡 **Vigilance** | 0.3 - 0.5 | Stress léger | Surveillance rapprochée |
| 🟠 **Alerte** | 0.2 - 0.3 | Dégradation | Intervention préventive |
| 🔴 **Alerte critique** | < 0.2 | Dégradation sévère | Action immédiate |
| ⚪ **Eau/Sol nu** | ≤ 0 | Exclu de l'analyse | Non concerné |

### 4. Export des résultats
- 📊 **CSV** : Données statistiques et séries temporelles
- 📄 **PDF** : Rapport complet avec graphiques et carte
- 🗺️ **GeoTIFF** : Image raster pour SIG

---

## 🏗️ Architecture


---

## 🚀 Installation

### Prérequis
- Python 3.11.9 ou supérieur
- Compte Google Earth Engine (authentification requise)
- Connexion internet

### Étapes d'installation

1. **Cloner le dépôt**
```bash
git clone https://github.com/votre-username/greenmonitor.git
cd greenmonitor

### Étapes d'installation
python -m venv env
# Windows
env\Scripts\activate
# Linux/Mac
source env/bin/activate
### Installer les dépendances
pip install -r requirements.txt

### Configurer Google Earth Engine
earthengine authenticate

###Lancer l'application

streamlit run app.py

##Auteurs
Développeur : [DOSSOU, KOFFI, NVONDO]

Contexte : Projet de surveillance environnementale

Version : 1.0.0