"""
Module Chef d'orchestre : Ingestion, Transformation et Indexation Vectorielle.
Version corrigée : Centralisation de la logique Document et intégration des filtres.
"""

import os
import time
import logging
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_mistralai import MistralAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path # Didier : peut-être plus nécessaire

# Didier : à titre d'historique--- FIX CRITIQUE : Localiser le .env à la racine du projet ---
# On part de poc/indexer.py, on remonte d'un niveau pour trouver .env
#env_path = Path(__file__).resolve().parent.parent / ".env"
#load_dotenv(dotenv_path=env_path)

# récupératoin des variables d'environnement, le fichier .env est dans ./pov qui est la racine du projet
load_dotenv()

# Imports locaux
from utils.logging_config import setup_logging
from utils.provider_factory import get_event_provider
from tests.check_filtres_events import check_events
from utils.config import MISTRAL_API_KEY, FAISS_INDEX_DIR, CHUNK_SIZE, CHUNK_OVERLAP, check_config

def create_documents(df, provider):
    """
    Transforme un DataFrame en une liste de Documents LangChain.
    Centralise la logique de mapping iCalendar pour la production ET les tests.
    """
    documents = []
    for _, row in df.iterrows():
        page_content = str(row.get(provider.COL_DESCRIPTION, "")).strip()
        
        # Sécurité anti-bruit : on ignore les contenus vides ou trop courts
        if not page_content or len(page_content) < 5:
            continue

        metadata = {
            "title": str(row.get(provider.COL_SUMMARY, 'Titre inconnu')),
            "start_date": str(row.get(provider.COL_DTSTART, '')),
            "end_date": str(row.get(provider.COL_DTEND, '')),
            "location": str(row.get(provider.COL_LOCATION, 'Lieu non précisé')),
            "url": str(row.get(provider.COL_URL, '')),
            "uid": str(row.get(provider.COL_UID, ''))
        }
        # création par Langchain des données page_content correspondants à COL_DESCRIPTION à vectoriser 
        #et des données brutes à stocker dans le dictionnaire
        documents.append(Document(page_content=page_content, metadata=metadata))
    return documents
    
def main():
    # 1. Initialisation
    logger = setup_logging()
    #load_dotenv()
    
    try:
        check_config()
    except ValueError as e:
        logger.error(f"L'indexation ne peut pas démarrer : {e}")
        return 

    logger.info("=== Début du processus d'indexation (Mode Multi-Source iCalendar) ===")

    # 2. Récupération des données
    try:
        provider = get_event_provider()
        logger.info(f"1/3 - Récupération via {provider.__class__.__name__}...")
        df_events = provider.fetch_events()
    except Exception as e:
        logger.error(f"Erreur initialisation provider : {e}")
        return
    
    if df_events.empty:
        logger.warning("Aucune donnée à indexer. Arrêt.")
        return

    # 3. Standardisation (Mapping iCalendar) via la fonction centralisée
    logger.info("2/3 - Formatage LangChain (Mapping iCalendar)...")
    documents = create_documents(df_events, provider)

    # 3 bis. Validation des filtres (Spécifique ODS pour le POC)
    provider_name = provider.__class__.__name__
    if provider_name == 'OpenDataSoftProvider':
        logger.info(f"Contrôle qualité filtres pour : {provider_name}...")
        try:
            check_events(documents, provider_name)
            logger.info("=== Filtres validés pour ODS ===")
        except ValueError as e:
            logger.error(f"Filtres non respectés : {e}")
            return 
 
    # 4. Préparation de l'Indexation
    logger.info(f"3/3 - Préparation de {len(documents)} documents...")
    
    embeddings = MistralAIEmbeddings(
        mistral_api_key=MISTRAL_API_KEY,
        model="mistral-embed"
    )

    # Chunking sémantique
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True
    )
    
    raw_chunks = text_splitter.split_documents(documents)
    docs_to_index = [doc for doc in raw_chunks if len(doc.page_content.strip()) > 5]
    
    count_source = len(docs_to_index)
    logger.info(f"Step 12 - Chunks à vectoriser (Source) : {count_source}")
    
    if count_source == 0:
        logger.error("Aucun document valide après découpage.")
        return

    # 5. Indexation FAISS par lots (Batches)
    BATCH_SIZE = 50
    vector_store = None 
    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)

    try:
        for i in range(0, count_source, BATCH_SIZE):
            batch = docs_to_index[i : i + BATCH_SIZE]
            logger.info(f"Vectorisation lot {i} à {i + len(batch)}...")
            
            if vector_store is None:
                vector_store = FAISS.from_documents(batch, embeddings)
            else:
                vector_store.add_documents(batch)
                time.sleep(0.5) # Anti Rate-limiting

        # 6. Vérification d'Intégrité et Sauvegarde
        count_target = vector_store.index.ntotal
        logger.info(f"Step 16 - Vecteurs stockés (Target) : {count_target}")

        if count_source == count_target:
            logger.info("Step 17 - Succès : Intégrité validée.")
            vector_store.save_local(FAISS_INDEX_DIR)
            logger.info(f"Step 18 - Index sauvegardé : {FAISS_INDEX_DIR}")
        else:
            logger.error(f"Step 17 - ALERTE : Incohérence Source({count_source}) != Target({count_target})")

    except Exception as e:
        logger.error(f"Erreur fatale lors de l'indexation : {e}")

if __name__ == "__main__":
    main()