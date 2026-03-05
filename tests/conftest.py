# Ce fichier conftest.py dans le dossier poc/tests : 
# Script de configuration global pour pytest (Fixtures partagées).
# Il centralise les fausses données (mocks) pour éviter d'appeler les vraies API
# pendant les tests unitaires et garantir une isolation totale (Scénario 1).
# OPTIMISATION ARCHITECTURE : Les fixtures fournies ici respectent scrupuleusement
# le standard iCalendar (RFC 5545) défini dans utils.base_provider.
# dette technique volontaire : seule la simulation de l'API OpenDataSoft (ODS) est réalisée dans ce script

"""
Module de configuration globale et de Fixtures pour Pytest.

Ce script centralise les jeux de données simulés (Mocks) utilisés à travers 
toute la suite de tests du projet Puls-Events. Il assure une isolation totale 
(Scénario 1) en évitant tout appel aux API réelles (OpenDataSoft, Mistral) 
pendant les phases de tests unitaires.

Fixtures fournies :
- mock_ods_api_response : Simule le flux JSON brut en provenance d'OpenDataSoft.
- valid_icalendar_df : Simule le DataFrame normalisé prêt pour l'indexation.

Le respect strict du standard iCalendar (RFC 5545) dans ces fixtures garantit 
que les tests valident la réalité du pipeline de production.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta, timezone

# --- FIXTURE 1 : Simulation de l'API OpenDataSoft ---
@pytest.fixture
def mock_ods_api_response():
    """
    Simule un dictionnaire JSON renvoyé par l'API ODS V2.1.
    Contient un événement valide pour tester le 'chemin heureux' (happy path)
    de notre méthode fetch_events().
    """
    """
    Simule une réponse JSON de l'API OpenDataSoft V2.1.
    
    Cette fixture est utilisée pour tester la couche 'Provider' (utils/api_opendatasoft.py).
    Elle génère dynamiquement des dates dans le futur pour éviter que les filtres 
    de fraîcheur du code ne rejettent l'événement de test.
    
    Returns:
        dict: Un dictionnaire imitant la structure 'results' de l'API ODS.
    """

    # Création d'une date dans le futur respectant le fuseau UTC
    future_date = (datetime.now(timezone.utc) + timedelta(days=2))
    
    return {
        "results": [
            {
                "uid": "ods-mock-001",
                "title_fr": "Événement de Test ODS",
                "description_fr": "Ceci est une description injectée pour les tests.",
                "firstdate_begin": future_date.isoformat(),
                "lastdate_end": (future_date + timedelta(hours=2)).isoformat(),
                "location_name": "Salle de Test Automatisé",
                "location_address": "123 Rue du Code",
                "conditions_fr": "Entrée libre",
                "canonicalurl": "https://test.opendatasoft.com/event/1"
            }
        ]
    }

# --- FIXTURE 2 : Simulation du format cible (Standard iCalendar) ---
@pytest.fixture
def valid_icalendar_df():
    """
    Simule le DataFrame propre généré par un Provider après son mapping.
    Ce DataFrame respecte strictement les REQUIRED_COLUMNS de base_provider.py.
    Il sera très utile pour tester l'indexer.py sans passer par un vrai Provider.
    """
    """
    Simule un DataFrame Pandas parfaitement mappé au standard iCalendar.
    
    Cette fixture est le pivot entre la Phase 1 (Collecte) et la Phase 2 (Indexation).
    Elle permet de tester 'indexer.py' et 'test_indexer.py' sans dépendre de 
    la réussite d'un appel API.
    
    Colonnes garanties : UID, SUMMARY, DESCRIPTION, DTSTART, DTEND, LOCATION, URL.
    
    Returns:
        pd.DataFrame: Un DataFrame de test conforme à REQUIRED_COLUMNS.
    """
    
    data = [{
        "UID": "mock-ical-123",
        "SUMMARY": "Titre Standardisé Test",
        "DESCRIPTION": "Description: Test unitaire en cours - Infos: NA",
        "DTSTART": "2026-12-01T14:00:00Z",
        "DTEND": "2026-12-01T16:00:00Z",
        "LOCATION": "Lieu Test (123 Rue du Test)",
        "URL": "https://dummy.url"
    }]
    return pd.DataFrame(data)