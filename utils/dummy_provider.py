# Ce fichier dummy_provider.py dans le dossier poc/utils : 
# 8. "Mock" Provider (Test de flexibilité)
#Pour prouver que le système fonctionne sans OpenAgenda, cré un faux fournisseur. 
#Contenu : Une classe qui retourne juste 2 événements "en dur" (hardcoded). 
#Test : Changez .env à EVENT_SOURCE="DUMMY" et lancez l'indexation. Si ça marche, l'architecture est validée.
# C'est un fournisseur factice pour tester la flexibilité de l'architecture.
# Il simule une réponse d'API en renvoyant des données "en dur" au format iCalendar.
# les infos de tests sont aussi utilisées pour l'évaluation du RAG

"""
Module fournissant un jeu de données factice pour les tests d'architecture.

Ce script agit comme un "Mock Provider". Il permet de prouver que le système 
fonctionne de bout en bout sans dépendre d'une connexion Internet.

Note critique : Ce fichier est la source de vérité pour le module d'évaluation 
qualitative (Phase 5). Toute modification ici doit être répercutée dans 
'tests/eval_dataset.json' pour garantir la validité des scores de similarité.
"""

import pandas as pd
from datetime import datetime, timedelta
from .base_provider import EventProvider
from utils.logging_config import setup_logging

logger = setup_logging()

class DummyProvider(EventProvider):
    """
    Provider de test générant des événements statiques calibrés pour l'évaluation.
    """

    def fetch_events(self) -> pd.DataFrame:
        """
        Génère un DataFrame contenant les événements de référence.

        Les données sont choisies pour tester des cas limites (Edge Cases) :
        - Un événement riche en détails (Strasbourg Jazz Festival).
        - Un événement avec des informations manquantes (Atelier Peinture sans prix).
        """
        logger.info("Utilisation du DummyProvider (Mode Test/Simulation)")

        now = datetime.now()
        date_1 = now.strftime('%Y-%m-%dT19:00:00Z')
        date_2 = (now + timedelta(days=1)).strftime('%Y-%m-%dT20:30:00Z')
        # Événement passé (il y a 10 jours)
        date_3 = (now - timedelta(days=10)).strftime('%Y-%m-%dT14:00:00Z')

        # --- Données synchronisées avec tests/eval_dataset.json ---
        data = [
            {
                self.COL_UID: "dummy-001",
                self.COL_SUMMARY: "Strasbourg Jazz Festival - Mock Edition",
                self.COL_DESCRIPTION: "Un concert de jazz factice pour tester le RAG. Artiste : John Doe Quartet.",
                self.COL_DTSTART: date_1,
                self.COL_DTEND: date_1,
                self.COL_LOCATION: "Caveau de Jazz, 10 rue des Orfèvres, Strasbourg",
                self.COL_URL: "https://example.com/jazz-test"
            },
            {
                self.COL_UID: "dummy-002",
                self.COL_SUMMARY: "Atelier Peinture Numérique",
                self.COL_DESCRIPTION: "Initiation à la création sur tablette graphique. Note : aucun tarif disponible.",
                self.COL_DTSTART: date_2,
                self.COL_DTEND: date_2,
                self.COL_LOCATION: "Médiathèque Malraux, Strasbourg",
                self.COL_URL: "https://example.com/art-test"
            },
            {
                self.COL_UID: "dummy-003",
                self.COL_SUMMARY: "Conférence Histoire de l'Art",
                self.COL_DESCRIPTION: "Une rétrospective sur la Renaissance Italienne.",
                self.COL_DTSTART: date_3,
                self.COL_DTEND: date_3,
                self.COL_LOCATION: "Palais Universitaire, Strasbourg",
                self.COL_URL: "https://example.com/past-event"
            }
        ]

        df = pd.DataFrame(data)
        
        # Validation du schéma iCalendar (RFC 5545)
        self.validate_schema(df)
        
        return df[self.REQUIRED_COLUMNS]