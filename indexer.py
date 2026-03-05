# Ce fichier indexer.py dans le dossier poc à la racine du projet : 
# Un script séparé pour préparer notre base de connaissances (création de l'index de recherche)
# Il a un rôle de "chef d'orchestre" pour l'ingestion des données. 
# Mise à jour PHASE 3 : Indexation Robuste et Vérification d'intégrité.
# OPTIMISATION ARCHITECTURE : Utilisation du ProviderFactory et du standard iCalendar.
# CENTRALISATION : Les paramètres (clés, chemins) sont désormais pilotés par utils.config.
# Dette technique volontaire : ce script ne gére pour l'instant que la vérification du filtre d'ODS 
#défini en dur dans api_opendatasoft.py et implémenté dans check_filtres_events.py

"""
Module Chef d'orchestre : Ingestion, Transformation et Indexation Vectorielle.

Ce script assure le rôle de pipeline ETL (Extract, Transform, Load) pour le projet Puls-Events.
Il orchestre la récupération des données via la Factory, leur conversion au standard 
iCalendar (RFC 5545), le découpage sémantique (Chunking) et la persistance dans 
la base vectorielle FAISS.

Points clés du processus :
- Abstraction des sources : Utilisation du ProviderFactory.
- Intégrité des données : Vérification stricte de la correspondance Source vs Target (Steps 16-17).
- Résilience : Sauvegarde atomique de l'index pour éviter les corruptions (Step 18).

Optimisation Phase 3 : Centralisation de la configuration via 'utils.config'.
"""

import os
import time
import logging  # AJOUT : Nécessaire pour capturer les erreurs de check_config
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_mistralai import MistralAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Imports de nos modules locaux
from utils.logging_config import setup_logging
from utils.provider_factory import get_event_provider
from tests.check_filtres_events import check_events
# Importation de la configuration centralisée :
from utils.config import MISTRAL_API_KEY, FAISS_INDEX_DIR, CHUNK_SIZE, CHUNK_OVERLAP, check_config

def main():
    """
    Point d'entrée principal du processus d'indexation.

    Déroulement technique :
    1. Initialisation : Configuration du logger et chargement des clés API.
    2. Collecte : Appel au provider (ODS, OpenAgenda ou Dummy) via la Factory.
    3. Standardisation : Mapping des champs vers le format iCalendar.
    3 bis. Vérification des filtres d'évènements avant vectorisation.
    4. Chunking : Découpage des descriptions pour optimiser la recherche sémantique.
    5. Vectorisation : Envoi des documents par lots (batches) à Mistral AI.
    6. Validation (Step 16-17) : Comparaison du nombre de vecteurs pour garantir l'intégrité.
    7. Persistance (Step 18) : Sauvegarde locale de l'index FAISS.
    
    Raises:
        Exception: Capture et logue toute erreur survenant durant le pipeline pour 
                   éviter une corruption de la base existante.
    """

    # 1. Initialisation
    logger = setup_logging()
    load_dotenv()
    
    # On utilise la variable centralisée depuis config.py
    #if not MISTRAL_API_KEY:
    #    logger.error("Clé API Mistral introuvable. Vérifiez votre fichier .env.")
    #    return
    # --- VÉRIFICATION AVANT RÉCUPÉRATION DES DONNÉES ---
    try:
        check_config()
    except ValueError as e:
        logging.error(f"L'indexation ne peut pas démarrer : {e}")
        return # Sortie propre du script
    logger.info("=== Début du processus d'indexation (Mode Multi-Source iCalendar) ===")

    # 2. Récupération et préparation des données via le Provider
    # La Factory choisit la source (OpenAgenda, Google, etc.) via le .env
    try:
        provider = get_event_provider()
        logger.info(f"1/3 - Récupération des événements via le provider {provider.__class__.__name__}...")
        df_events = provider.fetch_events()
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du provider : {e}")
        return
    
    if df_events.empty:
        logger.warning("Aucune donnée à indexer (DataFrame vide). Arrêt du script.")
        return

    # 3. Création des documents LangChain avec vocabulaire iCalendar (RFC 5545)
    logger.info("2/3 - Formatage des données pour LangChain (Mapping iCalendar)...")
    documents = []
    
    for _, row in df_events.iterrows():
        # Le contenu à indexer correspond désormais à la DESCRIPTION standardisée par le provider
        page_content = str(row[provider.COL_DESCRIPTION]).strip()
        
        # Sécurité anti-bruit
        if not page_content or len(page_content) < 5:
            continue

        # Récupération des métadonnées standardisées pour l'affichage futur par le chatbot
        # L'usage des constantes COL_XXX garantit la compatibilité quel que soit le provider choisi
        metadata = {
            "title": str(row.get(provider.COL_SUMMARY, 'Titre inconnu')),
            "start_date": str(row.get(provider.COL_DTSTART, '')),
            "end_date": str(row.get(provider.COL_DTEND, '')),
            "location": str(row.get(provider.COL_LOCATION, 'Lieu non précisé')),
            "url": str(row.get(provider.COL_URL, '')),
            "uid": str(row.get(provider.COL_UID, ''))
        }
        
        doc = Document(page_content=page_content, metadata=metadata)
        documents.append(doc)

    # 3 bis. vérifie le respect des filtrages des évènements à indexer
        # --- VÉRIFICATION FILTRES EVENEMENTS AVANT VECTORISATION DES DONNÉES pour ODS ---
# Utilisation du nom de classe pour le switch de validation
    provider_name = provider.__class__.__name__
    logger.info(f"Contrôle qualité filtres pour : {provider_name}...")

    if provider_name == 'OpenDataSoftProvider':
        try:
            # On passe les documents pour vérification de la localisation et des dates
            check_events(documents, provider_name)
        except ValueError as e:
            logger.error(f"Filtres des évènements non respectés : {e}")
            return 
        logger.info("=== Filtres ok, suite du processus d'indexation pour ODS===")
 
    # 4. Vectorisation et Indexation FAISS
    logger.info(f"3/3 - Préparation de {len(documents)} documents pour vectorisation...")
    
    embeddings = MistralAIEmbeddings(
        mistral_api_key=MISTRAL_API_KEY,
        model="mistral-embed"
    )

    # 4.1 Découpage des documents (Chunking) piloté par la config
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True
    )
    
    raw_chunks = text_splitter.split_documents(documents)
    
    # Nettoyage final des chunks pour éviter d'indexer du vide
    docs_to_index = [doc for doc in raw_chunks if doc.page_content and len(doc.page_content.strip()) > 5]
    
    # --- STEP 12 : Comptage Pré-Indexation (Source) ---
    count_source = len(docs_to_index)
    logger.info(f"Step 12 - Nombre exact de chunks à vectoriser (Source) : {count_source}")
    
    if count_source == 0:
        logger.error("Aucun document valide après nettoyage.")
        return

    # --- STEP 13 : Batch Processing (Lots) ---
    # On utilise FAISS_INDEX_DIR importé de config.py pour localiser l'index
    BATCH_SIZE = 50
    vector_store = None 
    
    # Assurer la présence du dossier de destination (géré aussi par config.py normalement)
    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)

    try:
        # --- STEP 15 : Création de l'Index (Boucle de vectorisation par lots) ---
        for i in range(0, count_source, BATCH_SIZE):
            batch = docs_to_index[i : i + BATCH_SIZE]
            logger.info(f"Vectorisation du lot {i} à {i + len(batch)} sur {count_source}...")
            
            if vector_store is None:
                # Création initiale de l'index FAISS
                vector_store = FAISS.from_documents(batch, embeddings)
            else:
                # Ajout incrémental des vecteurs
                vector_store.add_documents(batch)
                time.sleep(0.5) # Protection contre le rate-limiting de l'API Mistral

        # --- STEP 16 : Comptage Post-Indexation (Target) ---
        count_target = vector_store.index.ntotal
        logger.info(f"Step 16 - Nombre de vecteurs stockés dans l'index (Target) : {count_target}")

        # --- STEP 17 : Assertion de Complétude ---
        if count_source == count_target:
            logger.info("Step 17 - Succès : Intégrité des données validée (Source == Target).")
            
            # --- STEP 18 : Sauvegarde Atomique via le chemin configuré ---
            vector_store.save_local(FAISS_INDEX_DIR)
            logger.info(f"Step 18 - Index sauvegardé avec succès dans : {FAISS_INDEX_DIR}")
            
        else:
            # Alerte si le nombre de vecteurs en sortie ne correspond pas à l'entrée
            logger.error(f"Step 17 - ALERTE CRITIQUE : Incohérence détectée. Source={count_source}, Target={count_target}")
            logger.error("La sauvegarde a été annulée pour préserver l'intégrité de la base.")

    except Exception as e:
        logger.error(f"Erreur fatale lors du processus d'indexation : {e}")

if __name__ == "__main__":
    main()