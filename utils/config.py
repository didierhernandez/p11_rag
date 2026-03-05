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
# module standard Python qui gère les messages de journalisation
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- RÉPERTOIRES DU PROJET ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FAISS_INDEX_DIR = DATA_DIR / "faiss_index"

DATA_DIR.mkdir(exist_ok=True)

# --- CONFIGURATION DES SOURCES ---
EVENT_SOURCE = os.getenv("EVENT_SOURCE", "OPENAGENDA").upper()

# --- CLÉS API ET IDS ---
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
OPENAGENDA_ID = os.getenv("OPENAGENDA_ID")
OPENAGENDA_API_KEY = os.getenv("OPENAGENDA_API_KEY")

# --- PARAMÈTRES DU MODÈLE RAG ---
EMBEDDING_MODEL = "mistral-embed"
CHAT_MODEL = "mistral-large-latest"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

def check_config():
    """
    Vérifie que les variables essentielles sont présentes dans l'environnement.

    Cette fonction est appelée au démarrage de l'application pour s'assurer
    que les clés d'API nécessaires (Mistral, OpenAgenda, ODS, etc.) sont bien définies
    en fonction de la source d'événements sélectionnée (`EVENT_SOURCE`).

    Raises:
        ValueError: Si une ou plusieurs variables de configuration critiques sont manquantes.
    """
    missing = []

    # 1. Clé critique pour tous les modes (LLM + Embeddings)
    if not MISTRAL_API_KEY: 
        missing.append("MISTRAL_API_KEY")
    
    # 2. Vérifications spécifiques par source
    source = EVENT_SOURCE.upper()
    
    if source == "OPENAGENDA":
        if not OPENAGENDA_API_KEY: missing.append("OPENAGENDA_API_KEY")
        if not OPENAGENDA_ID: missing.append("OPENAGENDA_ID")
        
    elif source == "ODS":
        # OpenDataSoft peut être public, mais si une clé est requise pour certains datasets :
        # if not ODS_API_KEY: missing.append("ODS_API_KEY")
        pass
        
    elif source == "NEXTCLOUD":
        if not os.getenv("NEXTCLOUD_URL"): missing.append("NEXTCLOUD_URL")
        if not os.getenv("NEXTCLOUD_USER"): missing.append("NEXTCLOUD_USER")
        if not os.getenv("NEXTCLOUD_PASSWORD"): missing.append("NEXTCLOUD_PASSWORD")
        
    elif source == "DUMMY":
        # Mode simulation : aucune clé source requise
        logging.info("Mode DUMMY activé : Validation des sources externes ignorée.")
    
    if missing:
        error_msg = f"Configuration incomplète pour la source {source}. Variables manquantes : {', '.join(missing)}"
        logging.error(error_msg)
        raise ValueError(error_msg)
        
    logging.info(f"Configuration validée avec succès pour la source : {source}")