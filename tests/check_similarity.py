# Ce fichier tests/check_similarity.py (anciennement test_similarity.py) :
# Il sert de banc d'essai visuel pour vérifier que votre base vectorielle "comprend" 
# et "répond" correctement aux questions sémantiques avant de brancher le chatbot.
# OPTIMISATION PHASE 3 : Alignement des affichages sur les métadonnées iCalendar 
# générées par l'indexer.py.

"""
Module d'inspection visuelle et de test de la recherche sémantique.

Ce script sert de banc d'essai pour vérifier que la base vectorielle "comprend" 
et "répond" correctement aux questions sémantiques avant de brancher le chatbot.
Il valide l'alignement des affichages sur les métadonnées iCalendar (Phase 3).
"""

import os
import sys
from dotenv import load_dotenv

# --- Configuration des chemins ---
# Permet d'importer les modules du dossier parent (utils)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from langchain_mistralai import MistralAIEmbeddings
from langchain_community.vectorstores import FAISS

# Import local (via sys.path)
from utils.logging_config import setup_logging

def main():
    """
    Exécute une série de requêtes textuelles contre l'index FAISS et affiche les scores L2.

    Fonctionnement :
    1. Charge l'index FAISS préalablement créé sans lancer Streamlit.
    2. Lance des questions de test (ex: 'Concert de jazz').
    3. Affiche les `k` voisins les plus proches avec leurs métadonnées et scores L2.
    
    Notes:
        Dans la norme FAISS (L2), plus le score est proche de 0, plus la similarité sémantique est forte.
    """
    logger = setup_logging()
    load_dotenv()

    api_key_mistral = os.environ.get("MISTRAL_API_KEY")
    if not api_key_mistral:
        logger.error("Clé API Mistral manquante.")
        return

    # --- Step 19 : Chargement de l'Index de Test ---
    # On charge l'index fraîchement créé sans lancer l'interface Streamlit.
    index_path = os.path.join(parent_dir, "data", "faiss_index")
    
    if not os.path.exists(index_path):
        logger.error(f"L'index n'existe pas dans {index_path}. Lancez d'abord indexer.py.")
        return

    logger.info(f"Chargement de l'index depuis : {index_path}")
    
    try:
        embeddings = MistralAIEmbeddings(mistral_api_key=api_key_mistral, model="mistral-embed")
        
        # allow_dangerous_deserialization=True est requis pour les fichiers pickle locaux 
        # du docstore (.pkl) avec les métadonnées
        vector_store = FAISS.load_local(
            index_path, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        logger.info("Index chargé avec succès.")
    except Exception as e:
        logger.error(f"Erreur critique au chargement de l'index : {e}")
        return

    # --- Step 20 : Définition de Cas de Test (Queries) ---
    # Préparer une liste de questions types pour couvrir différents scénarios.
    test_queries = [
        "Concert de musique classique ou jazz",   # Test sur le genre
        "Spectacle pour enfants gratuit",         # Test sur cible + tarif (dans la description)
        "Exposition de peinture",                 # Test sur type d'événement
        "Événement de ce week-end",               # Test temporel (sémantique)
        "Atelier créatif et numérique"            # Test thématique
    ]

    print("\n" + "="*50)
    print(" DÉBUT DES TESTS DE RECHERCHE SÉMANTIQUE (INSPECTION VISUELLE)")
    print("="*50 + "\n")

    for i, query in enumerate(test_queries, 1):
        print(f"\nTEST {i}/{len(test_queries)} : '{query}'")
        
        # --- Step 21 : Exécution de la Recherche (k=3) ---
        # Pour chaque question, demander les 3 voisins les plus proches.
        # similarity_search_with_score renvoie le document ET le score de distance.
        results_with_scores = vector_store.similarity_search_with_score(query, k=3)

        # --- Step 22 : Analyse des Scores de Distance ---
        # NOTE : Dans FAISS (L2), plus le score est proche de 0, plus la similarité est forte.
        for doc, score in results_with_scores:
            
            # --- Step 23 : Vérification Humaine des Métadonnées ---
            # MISE À JOUR : Les clés doivent correspondre strictement au mapping iCalendar 
            # de la fonction main() dans indexer.py.
            metadata = doc.metadata
            
            print(f"   Score (L2): {score:.4f} (Plus bas = Meilleur)")
            print(f"   > Titre   : {metadata.get('title', 'N/A')}")
            print(f"   > Date    : Du {metadata.get('start_date', 'N/A')} au {metadata.get('end_date', 'N/A')}")
            print(f"   > Lieu    : {metadata.get('location', 'N/A')}")
            print(f"   > Lien    : {metadata.get('url', 'N/A')}")
            print("   " + "-"*30)

    print("\nFin des tests de similarité.")

if __name__ == "__main__":
    main()