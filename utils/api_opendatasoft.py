# Ce fichier api_opendatasoft.py dans le dossier poc/utils : 
# Script de requêtage API pour OpenDataSoft (Jeu de données : evenements-publics-openagenda).
# Cible spécifiquement la ville de Strasbourg sur 30 jours à partir d'aujourd'hui.
# ÉTAPE 10 : Gestion des erreurs unifiée et protection par timeout.
# ÉTAPE 11 : Nettoyage strict (RAG-Ready) et mise en conformité iCalendar.

"""
Module de requêtage pour l'API OpenDataSoft (Étape 10 et 11).

Ce script se connecte au jeu de données 'evenements-publics-openagenda',
cible spécifiquement la ville Strasbourg, et applique un nettoyage strict (RAG-Ready)
pour garantir la conformité iCalendar.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from .base_provider import EventProvider
from utils.logging_config import setup_logging

logger = setup_logging()

class OpenDataSoftProvider(EventProvider):
    """
    Implémentation concrète pour l'API OpenDataSoft.

    Ce provider gère la pagination, les erreurs réseau via timeout, et applique
    un double filtrage temporel pour ne récupérer que les données fraîches.

    Attributes:
        api_key (str): Clé d'API OpenDataSoft récupérée de l'environnement 
                       (souvent optionnelle pour les petits volumes publics).
        base_url (str): Endpoint de l'API (v2.1) pour le catalogue d'événements.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENDATASOFT_API_KEY", "") 
        self.base_url = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records"

    def fetch_events(self) -> pd.DataFrame:
        """
        Récupère et nettoie les événements via l'API ODS avec un filtre SQL-like.

        Étapes de traitement :
        1. Requêtage paginé (par 100) avec filtres 'Strasbourg' et fenêtre de J-30.
        2. Nettoyage strict (suppression des lignes avec titres manquants ou vides).
        3. Mapping des champs ODS vers le standard RFC 5545 défini dans EventProvider.
        4. Sécurisation de la concaténation géographique pour éviter l'effet 'NaN'.

        Returns:
            pd.DataFrame: Un DataFrame de métadonnées prêtes à être ingérées par 
                          le système RAG. Renvoie un DataFrame vide en cas d'erreur 
                          réseau ou d'absence de résultats.

        Notes:
            - Timeout réseau fixé à 15 secondes pour protéger le pipeline.
            - Utilise `firstdate_begin` et `lastdate_end` pour le filtrage temporel.
        """
        
        # 1. Préparation des filtres temporels pour garantir la fraîcheur du RAG
        start_date_filter = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 2. Construction de la clause WHERE sécurisée (SQL-like)
        where_clause = (
            #f"location_region='Grand Est' AND "
            f"location_city='Strasbourg' AND "
            f"lastdate_end >= '{today}' AND "
            f"firstdate_begin >= '{start_date_filter}'"
        )
                
        logger.info(f"Début de la récupération OpenDataSoft (Strasbourg, depuis {start_date_filter})...")

        all_events = []
        offset = 0
        limit = 100 
        
        while True:
            params = {
                'limit': limit,
                'offset': offset,
                'where': where_clause,
                'order_by': 'lastdate_end ASC' 
            }
            
            if self.api_key:
                params['apikey'] = self.api_key

            try:
                response = requests.get(self.base_url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                if not results:
                    break
                
                all_events.extend(results)
                logger.info(f"Page ODS (Offset {offset})... Total cumulé : {len(all_events)}")
                
                if len(results) < limit:
                    break
                offset += limit

            except requests.exceptions.RequestException as e:
                logger.error(f"ERREUR RÉSEAU chez OpenDataSoft : {e}")
                break
            except Exception as e:
                logger.error(f"ERREUR INATTENDUE API ODS : {e}")
                break

        if not all_events:
            logger.warning("Aucun événement récupéré depuis OpenDataSoft.")
            return pd.DataFrame()

        try:
            df = pd.DataFrame(all_events)

            # --- SÉCURISATION DES COLONNES ---
            expected_columns = [
                'title_fr', 'description_fr', 'conditions_fr', 
                'location_name', 'location_address', 'canonicalurl',
                'firstdate_begin', 'lastdate_end', 'uid'
            ]
            
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = ""
                else:
                    df[col] = df[col].fillna("")

            # NETTOYAGE STRICT
            df = df[df['title_fr'].str.strip().astype(bool)]
        
            # Mapping iCalendar
            df['start_dt'] = pd.to_datetime(df['firstdate_begin'], utc=True, errors='coerce')
            df['end_dt'] = pd.to_datetime(df['lastdate_end'], utc=True, errors='coerce')
            df = df.dropna(subset=['start_dt', 'end_dt'])

            # --- FIX : Conversion de l'Index en Series pour fillna ---
            fallback_uids = (df.index.astype(str) + '@ods').to_series(index=df.index)
            
            df[self.COL_UID] = (
                df['uid']
                .apply(lambda x: str(x) if x != "" else "")
                .replace("", pd.NA)
                .fillna(fallback_uids)
            )
            
            df[self.COL_SUMMARY] = df['title_fr']
            
            # Concaténation sécurisée
            df[self.COL_DESCRIPTION] = (
                "Description: " + df['description_fr'] + 
                " - Infos: " + df['conditions_fr']
            )
            
            df[self.COL_DTSTART] = df['start_dt'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            df[self.COL_DTEND] = df['end_dt'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

            # Reconstruction du lieu
            df[self.COL_LOCATION] = (
                df['location_name'] + " (" + df['location_address'] + ")"
            ).replace(" ()", "Lieu inconnu")

            df[self.COL_URL] = df['canonicalurl']

            logger.info(f"Nettoyage et mapping terminés : {len(df)} événements valides.")
            self.validate_schema(df)
            return df[self.REQUIRED_COLUMNS]

        except Exception as e:
            logger.error(f"Erreur lors du traitement/mapping des données ODS : {e}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)