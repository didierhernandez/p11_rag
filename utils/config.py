# Ce fichier config.py dans le dossier poc/utils : 
# Script de Gestion de la configuration (clés API, chemins de fichiers ...).
# Il centralise l'accès aux variables d'environnement et définit les constantes du projet.
# Dette technique volontaire : la fonction check_config() qui est utilisée dans indexer.py et MistralChat.py
#ne tient pas compte des besoins spécifiques des contextes respectifs de ces deux fichiers

"""
Module de gestion de la configuration du projet Puls-Events.

Ce script centralise l'accès aux variables d'environnement (clés API, identifiants) 
et définit les constantes globales du projet (chemins de fichiers, modèles utilisés).
Il charge automatiquement le fichier `.env` à son importation, garantissant que 
l'ensemble du code partage la même configuration.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# --- CHEMIN SÉCURISÉ POUR LA RACINE 'poc' ---
# On part de poc/utils/config.py, on remonte d'UN seul niveau pour être dans 'poc'
BASE_DIR = Path(__file__).resolve().parent.parent 
ENV_PATH = BASE_DIR / ".env"

# Chargement avec override pour nettoyer les anciennes variables système et donne la priorité à la variable de .env
#load_dotenv(dotenv_path=ENV_PATH, override=True)
# Chargement sans override pour que Python regarde si la variable existe déjà dans le système (ton export DUMMY). Si oui, il n'y touche pas. Si non, il prend celle du .env
load_dotenv(dotenv_path=ENV_PATH, override=False)

# --- DEBUG ---
# print(f"DEBUG: BASE_DIR est {BASE_DIR}")
# print(f"DEBUG: .env cherché ici : {ENV_PATH}")

# --- RÉPERTOIRES ---
DATA_DIR = BASE_DIR / "data"
FAISS_INDEX_DIR = DATA_DIR / "faiss_index"
DATA_DIR.mkdir(exist_ok=True)

# --- CONFIGURATION DES SOURCES ---
EVENT_SOURCE = os.getenv("EVENT_SOURCE", "DUMMY").strip().upper()

# --- CLÉS API ---
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
OPENAGENDA_ID = os.getenv("OPENAGENDA_ID")
OPENAGENDA_API_KEY = os.getenv("OPENAGENDA_API_KEY")

# --- PARAMÈTRES RAG ---
EMBEDDING_MODEL = "mistral-embed"
CHAT_MODEL = "mistral-large-latest"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

def check_config():
    """Vérification stricte de la config 
    didier : à faire évoluer pour mieux intégrer automatiquement les différents providers."""
    missing = []
    if not MISTRAL_API_KEY: missing.append("MISTRAL_API_KEY")
    
    if EVENT_SOURCE == "OPENAGENDA":
        if not OPENAGENDA_API_KEY: missing.append("OPENAGENDA_API_KEY")
        if not OPENAGENDA_ID: missing.append("OPENAGENDA_ID")
    
    if missing:
        raise ValueError(f"Variables manquantes dans {ENV_PATH} : {', '.join(missing)}")