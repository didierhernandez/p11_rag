# Ce fichier tests/test_api_opendatasoft.py :
# Tests unitaires pour le provider OpenDataSoftProvider.
# ÉTAPE 4, 5 et 6 : Validation du schéma, des dates et de la robustesse réseau.
# Approche : Utilisation de 'pytest-mock' pour simuler les réponses de l'API ODS
# afin de tester la logique de mapping sans réelle connexion internet.

"""
Module de tests unitaires pour le fournisseur de données OpenDataSoft (ODS).

Ce script utilise 'pytest' et 'pytest-mock' pour valider la logique d'extraction 
et de transformation des données sans effectuer de réels appels réseau (Mocking). 
Il garantit que le mapping vers le standard iCalendar (RFC 5545) reste intègre, 
assurant ainsi la stabilité de la Phase 1 du POC.

Étapes de validation couvertes :
- ÉTAPE 4 : Validation du schéma et du contenu mappé.
- ÉTAPE 5 : Conformité du formatage des dates (ISO 8601).
- ÉTAPE 6 : Gestion des erreurs et robustesse en cas de panne réseau.
"""

import pytest
import pandas as pd
from utils.api_opendatasoft import OpenDataSoftProvider

# --- ÉTAPE 4 : Test de validation du schéma et du contenu ---
def test_fetch_events_schema_logic(mocker, mock_ods_api_response):
    """
    Vérifie que la logique de mapping transforme correctement le JSON brut d'ODS 
    en un DataFrame conforme aux REQUIRED_COLUMNS d'iCalendar.

    Args:
        mocker: Fixture de simulation pour intercepter les appels 'requests'.
        mock_ods_api_response: Données JSON factices (fixture) imitant l'API réelle.

    Asserts:
        - La présence de toutes les colonnes obligatoires (SUMMARY, DTSTART, etc.).
        - La correspondance exacte des données (ex: 'title_fr' devient 'SUMMARY').
    """

    # On simule la réponse de requests.get pour qu'elle renvoie notre fixture
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_ods_api_response

    provider = OpenDataSoftProvider()
    df = provider.fetch_events()

    # Assertions sur la structure
    assert isinstance(df, pd.DataFrame)
    assert not df.empty, "Le DataFrame ne devrait pas être vide avec un mock valide"
    for col in provider.REQUIRED_COLUMNS:
        assert col in df.columns, f"La colonne obligatoire {col} est manquante"

    # Vérification d'une valeur mappée (exemple : SUMMARY)
    assert df.iloc[0][provider.COL_SUMMARY] == "Événement de Test ODS"

# --- ÉTAPE 5 : Test du formatage des dates ISO 8601 ---
def test_fetch_events_date_format(mocker, mock_ods_api_response):
    """
    S'assure que les dates de début et de fin sont converties au format 
    string standardisé iCalendar (YYYY-MM-DDTHH:MM:SSZ).

    Ce test est critique pour la Phase 3 (RAG) car le LLM s'appuie sur la 
    structure temporelle pour filtrer les événements passés ou futurs.

    Asserts:
        - La présence du suffixe 'Z' (UTC).
        - La présence du séparateur 'T'.
    """

    mocker.patch("requests.get").return_value.json.return_value = mock_ods_api_response
    
    provider = OpenDataSoftProvider()
    df = provider.fetch_events()

    dt_start = df.iloc[0][provider.COL_DTSTART]
    
    # Vérification du format (doit se terminer par 'Z' pour UTC)
    assert dt_start.endswith("Z"), "La date doit être en format UTC (Z)"
    assert "T" in dt_start, "La date doit respecter le séparateur T de l'ISO 8601"

# --- ÉTAPE 6 : Test de la gestion d'erreurs (Robustesse) ---
def test_fetch_events_network_error(mocker):
    """
    Vérifie la résilience du système face aux incidents réseau.

    Ce test simule une exception de type ConnectionError ou un code d'erreur 
    HTTP (404, 500) pour garantir que le programme ne plante pas (crash) 
    et retourne un DataFrame vide de manière élégante.
    """

    # On simule une levée d'exception réseau
    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = Exception("Erreur réseau simulée")

    provider = OpenDataSoftProvider()
    
    # On vérifie que la fonction gère l'exception au lieu de la propager
    df = provider.fetch_events()
    
    assert isinstance(df, pd.DataFrame)
    assert df.empty, "En cas d'erreur, fetch_events doit retourner un DataFrame vide"