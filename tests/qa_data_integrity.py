# fichier tests/qa_data_integrity.py (ancien tests/test_data_integrity.py avant mise en place pytests)
# pour garantir la qualité des données (QA).
# module unittest (standard en Python) qui est compatible avec le lanceur de tests pytest. 
# Cela permet d'utiliser la méthode setUp, tout en bénéficiant de la puissance de rapport de pytest.
# Ce script va agir comme un "Gatekeeper" : si ces tests échouent, le RAG ne doit pas être mis en production.
# à lancer manuellement avec python qa_data_integrity.py quand l'indexation sera terminée
# OPTIMISATION PHASE 3 : Alignement strict des tests sur le standard de métadonnées iCalendar (RFC 5545).

"""
Module de tests d'intégrité des données (Quality Assurance - Gatekeeper).

Ce script agit comme un "Garde-fou" (Gatekeeper) de la chaîne de données. 
Si ces tests échouent, le RAG ne doit pas être mis en production. Il vérifie 
la qualité des documents vectorisés en s'alignant strictement sur le standard 
de métadonnées iCalendar (RFC 5545). Compatible avec le lanceur de tests `pytest`.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# --- Configuration des chemins pour les imports ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from langchain_mistralai import MistralAIEmbeddings
from langchain_community.vectorstores import FAISS
from utils.logging_config import setup_logging

class TestDataIntegrity(unittest.TestCase):
    """
    Suite de tests garantissant la validité de l'index FAISS généré.
    """    
    # --- Step 24 : Setup du Test Unitaire ---
    def setUp(self):
        """
        Configuration exécutée avant chaque test.
        Charge l'index FAISS en mémoire et prépare l'environnement de test.
        """
        self.logger = setup_logging()
        load_dotenv()
        
        api_key_mistral = os.environ.get("MISTRAL_API_KEY")
        if not api_key_mistral:
            self.fail("Clé API Mistral manquante dans le fichier .env")

        self.index_path = os.path.join(parent_dir, "data", "faiss_index")
        
        if not os.path.exists(self.index_path):
            self.fail(f"L'index FAISS est introuvable dans {self.index_path}. Lancez 'indexer.py' d'abord.")

        try:
            embeddings = MistralAIEmbeddings(mistral_api_key=api_key_mistral, model="mistral-embed")
            # Chargement de la base vectorielle
            self.vector_store = FAISS.load_local(
                self.index_path, 
                embeddings, 
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            self.fail(f"Impossible de charger l'index FAISS : {e}")

    # --- Step 25 : Extraction de toutes les Métadonnées (Helper) ---
    def get_all_documents(self):
        """
        Fonction utilitaire pour itérer sur tous les documents stockés.
        FAISS stocke les documents dans un 'docstore' sous forme de dictionnaire.
        """
        # Accès au dictionnaire interne du docstore {id: Document}
        return list(self.vector_store.docstore._dict.values())

    # --- Step 26 : Test de la Fenêtre Temporelle (Date > NOW-30j) ---
    def test_time_window(self):
        """
        Vérifie que tous les événements ont une date de début >= Aujourd'hui - 30 jours.
        Garantit que l'API a bien filtré les vieux événements selon le standard iCalendar.
        """
        documents = self.get_all_documents()
        self.assertGreater(len(documents), 0, "L'index est vide, impossible de tester la fenêtre temporelle.")

        # Définition de la date butoir (aware timezone UTC pour comparaison)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        failures = []
        for doc in documents:
            start_date_str = doc.metadata.get('start_date')
            title = doc.metadata.get('title', 'Sans titre')
            
            if not start_date_str or start_date_str == 'NaT':
                continue 

            try:
                # Sécurité : remplacer le "Z" par "+00:00" pour éviter les crashs fromisoformat sur d'anciens Python
                clean_date_str = start_date_str.replace("Z", "+00:00")
                event_date = datetime.fromisoformat(clean_date_str)
                
                # Assertion
                if event_date < cutoff_date:
                    failures.append(f"Événement périmé : {title} ({start_date_str}) < Cutoff ({cutoff_date})")
            except ValueError:
                failures.append(f"Format de date invalide pour : {title} ({start_date_str})")

        self.assertEqual(len(failures), 0, f"Échec Test Temporel :\n" + "\n".join(failures))

    # --- Step 27 : Test de la Géolocalisation ---
    def test_geolocation(self):
        """
        Vérifie que les événements contiennent une info géographique valide.
        Adapté pour lire l'unique champ 'location' du standard iCalendar.
        """
        documents = self.get_all_documents()
        failures = []
        
        for doc in documents:
            location = doc.metadata.get('location', '')
            title = doc.metadata.get('title')

            # Test simple : Le lieu standardisé doit être présent (au moins 3 caractères)
            if len(location) < 3 or location == 'Lieu inconnu':
                failures.append(f"Lieu manquant ou invalide pour : {title}")

        self.assertEqual(len(failures), 0, f"Échec Test Géo :\n" + "\n".join(failures[:5]))

    # --- Step 28 : Test de Présence des Champs Critiques ---
    def test_critical_fields(self):
        """
        Assure que les champs indispensables au RAG sont bien peuplés.

        Vérifie :
        1. La présence et la validité du Titre (SUMMARY).
        2. La taille minimale de la description (contenu vectorisé).
        3. La présence d'une traçabilité (URL ou UID) pour que le RAG puisse citer ses sources.

        Raises:
            AssertionError: Si un ou plusieurs documents ne possèdent pas les métadonnées requises.
        """
        documents = self.get_all_documents()
        failures = []

        for doc in documents:
            title = doc.metadata.get('title')
            
            # 1. Titre
            if not title or title == 'Sans titre':
                failures.append("Titre manquant")

            # 2. Description (contenue dans le page_content vectorisé)
            if not doc.page_content or len(doc.page_content) < 10:
                failures.append(f"Contenu trop court pour : {title}")

            # 3. Traçabilité : URL ou UID (Indispensable pour que le RAG puisse citer ses sources)
            url = doc.metadata.get('url', '')
            uid = doc.metadata.get('uid', '')
            if not url and not uid:
                failures.append(f"Identifiant (UID) et URL manquants pour la traçabilité : {title}")

        self.assertEqual(len(failures), 0, f"Échec Champs Critiques ({len(failures)} erreurs) :\n" + "\n".join(failures[:5]))

# --- Step 30 : Rapport de Test (Exécution) ---
if __name__ == "__main__":
    print("=== DÉBUT DES TESTS D'INTÉGRITÉ DES DONNÉES (QA) ===")
    unittest.main(verbosity=2)