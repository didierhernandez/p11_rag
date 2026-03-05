# Ce fichier indexer.py dans le dossier poc à la racine du projet : 
#Un script séparé pour préparer notre base de connaissances (création de l'index de recherche)
# Il a un rôle de "chef d'orchestre" pour l'ingestion des données. 
#Il va récupérer les événements via notre fonction fetch_events, les transformer en un format compréhensible par LangChain, 
#les vectoriser avec Mistral, et sauvegarder le tout dans le dossier data/.

import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
# langchain_mistralai est un "adaptateur" (wrapper).
#c'est un outil d'Intégration de Framework (en complément du SDK mistralai)
#Il traduit le langage universel de LangChain vers le langage spécifique de Mistral.
from langchain_mistralai import MistralAIEmbeddings

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
    # Clé publique OpenAgenda utilisée dans notre test
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
        # Le texte brut qui sera converti en vecteur
        page_content = str(row['content_to_index'])
        
        # Les métadonnées (très utiles pour filtrer ou sourcer la réponse de l'IA)
        metadata = {
            "title": str(row.get('title.fr', 'Titre inconnu')),
            "start_date": str(row.get('start_date', '')),
            "end_date": str(row.get('end_date', ''))
        }
        
        # Création de l'objet Document de LangChain
        doc = Document(page_content=page_content, metadata=metadata)
        documents.append(doc)

    # 4. Vectorisation et Indexation FAISS
    logger.info(f"3/3 - Vectorisation de {len(documents)} documents avec Mistral et création de l'index FAISS...")
    
    # On initialise le modèle d'embedding de Mistral
    embeddings = MistralAIEmbeddings(
        mistral_api_key=api_key_mistral,
        model="mistral-embed"
    )
    
    # Création de la base vectorielle en mémoire
    vector_store = FAISS.from_documents(documents, embeddings)
    
    # Sauvegarde sur le disque (dans le dossier data/)
    save_dir = os.path.join(os.path.dirname(__file__), "data", "faiss_index")
    
    # Création du dossier s'il n'existe pas
    os.makedirs(save_dir, exist_ok=True)
    
    vector_store.save_local(save_dir)
    logger.info(f"=== Succès ! Index FAISS sauvegardé dans : {save_dir} ===")

if __name__ == "__main__":
    main()