# Ce fichier indexer.py dans le dossier poc à la racine du projet : 
# Un script séparé pour préparer notre base de connaissances (création de l'index de recherche)
# Il a un rôle de "chef d'orchestre" pour l'ingestion des données. 
# Il va récupérer les événements via notre fonction fetch_events, les transformer en un format compréhensible par LangChain, 
# les vectoriser avec Mistral, et sauvegarder le tout dans le dossier data/.

import os
import time # Ajout pour gérer une pause entre les appels API si nécessaire
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
# langchain_mistralai est un "adaptateur" (wrapper).
# C'est un outil d'Intégration de Framework (en complément du SDK mistralai)
from langchain_mistralai import MistralAIEmbeddings
# un découpage sémantique (Chunking) via RecursiveCharacterTextSplitter.
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Imports de nos modules locaux
from utils.logging_config import setup_logging
from utils.api_open_agenda import fetch_events

def main():
    # 1. Initialisation
    logger = setup_logging()
    load_dotenv()
    
    api_key_mistral = os.environ.get("MISTRAL_API_KEY")
    if not api_key_mistral:
        logger.error("Clé API Mistral introuvable. Vérifiez votre fichier .env.")
        return

    # Configuration OpenAgenda (utilisez l'ID que nous avons testé)
    AGENDA_ID = "7430297" 
    API_KEY_OPENAGENDA = "69102d97a84c460ea43c400b2529a009"

    logger.info("=== Début du processus d'indexation ===")

    # 2. Récupération et préparation des données
    logger.info("1/3 - Récupération des événements depuis OpenAgenda...")
    df_events = fetch_events(AGENDA_ID, API_KEY_OPENAGENDA)
    
    if df_events.empty:
        logger.warning("Aucune donnée à indexer. Arrêt du script.")
        return

    # 3. Création des documents LangChain avec Métadonnées
    logger.info("2/3 - Formatage des données pour LangChain...")
    documents = []
    for _, row in df_events.iterrows():
        # Nettoyage : .strip() enlève les espaces, on force en string
        page_content = str(row['content_to_index']).strip()
        
        # Sécurité : On ignore les contenus vides ou trop courts (< 5 caractères)
        # Cela évite d'envoyer du "bruit" à l'API qui causerait une erreur 400
        if not page_content or len(page_content) < 5:
            continue

        metadata = {
            "title": str(row.get('title.fr', 'Titre inconnu')),
            "start_date": str(row.get('start_date', '')),
            "end_date": str(row.get('end_date', ''))
        }
        
        doc = Document(page_content=page_content, metadata=metadata)
        documents.append(doc)

    # 4. Vectorisation et Indexation FAISS par LOTS (BATCHING)
    logger.info(f"3/3 - Préparation de {len(documents)} documents pour vectorisation...")
    
    embeddings = MistralAIEmbeddings(
        mistral_api_key=api_key_mistral,
        model="mistral-embed"
    )

    # 4.1 Découpage des documents (Chunking)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        add_start_index=True
    )
    
    raw_chunks = text_splitter.split_documents(documents)
    
    # Nettoyage final des chunks
    docs_to_index = [doc for doc in raw_chunks if doc.page_content and len(doc.page_content.strip()) > 5]
    
    total_chunks = len(docs_to_index)
    logger.info(f"Nombre de chunks valides à vectoriser : {total_chunks}")
    
    if not docs_to_index:
        logger.error("Aucun document valide après nettoyage.")
        return

    # --- STRATÉGIE DE BATCHING (LOTS) ---
    # Au lieu de tout envoyer d'un coup (ce qui cause l'erreur 400),
    # on envoie les données par paquets de 50.
    BATCH_SIZE = 50
    vector_store = None # On l'initialisera au premier lot
    
    save_dir = os.path.join(os.path.dirname(__file__), "data", "faiss_index")
    os.makedirs(save_dir, exist_ok=True)

    try:
        # On boucle par pas de 50 (0, 50, 100, 150...)
        for i in range(0, total_chunks, BATCH_SIZE):
            # Sélection du lot courant
            batch = docs_to_index[i : i + BATCH_SIZE]
            logger.info(f"Vectorisation du lot {i} à {i + len(batch)} sur {total_chunks}...")
            
            if vector_store is None:
                # Pour le premier lot, on CRÉE l'index
                vector_store = FAISS.from_documents(batch, embeddings)
            else:
                # Pour les suivants, on AJOUTE à l'index existant
                vector_store.add_documents(batch)
                # Petite pause pour être gentil avec l'API (Rate Limiting)
                time.sleep(0.5)
        
        # Sauvegarde finale une fois tout terminé
        vector_store.save_local(save_dir)
        logger.info(f"=== Succès ! Index FAISS sauvegardé dans : {save_dir} ===")
        
    except Exception as e:
        logger.error(f"Erreur lors de la vectorisation par lot : {e}")
        # Optionnel : On pourrait sauvegarder ce qu'on a réussi à faire jusqu'ici
        if vector_store:
            logger.info("Sauvegarde partielle de l'index...")
            vector_store.save_local(save_dir)

if __name__ == "__main__":
    main()