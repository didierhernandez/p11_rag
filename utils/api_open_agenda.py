# Ce fichier api_open_agenda.py dans le dossier poc/utils : 
# script de requêtage API d'évènements d'Open Agenda qui filtre en fonction de l'uid d'un agenda.
# OPTIMISATION MAJEURE : Cette version filtre directement via l'API (timings[gte]) 
# pour ne pas télécharger tout l'historique inutilement.
# Gère la pagination et sécurise les colonnes manquantes (Patch KeyError).
# MISE À JOUR ARCHITECTURE : Implémentation du standard iCalendar (RFC 5545).
# ÉTAPE 10 : Gestion des erreurs unifiée et protection par timeout.

"""
Fournisseur de données OpenAgenda (API V2).

Ce module assure le requêtage haute performance du catalogue OpenAgenda. 
Il est optimisé pour ne récupérer que les données "fraîches" (événements à venir) 
directement via les filtres de l'API, réduisant ainsi la charge réseau.

Optimisations majeures :
- Filtrage natif (timings[gte]) pour limiter le volume de données.
- Gestion de la pagination pour les agendas volumineux.
- Mapping enrichi des métadonnées (Tarifs, Conditions, Horaires) dans la DESCRIPTION.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from .base_provider import EventProvider
from utils.logging_config import setup_logging

logger = setup_logging()

class OpenAgendaProvider(EventProvider):
    """
    Implémentation concrète pour OpenAgenda utilisant le standard iCalendar.
    """

    """
    Interface avec l'API OpenAgenda.
    
    Utilise le 'agenda_id' et la 'api_key' pour extraire les événements 
    et les transformer au format iCalendar (RFC 5545).
    """

    def __init__(self):
        # Récupération des clés depuis l'environnement (config centralisée)
        self.api_key = os.getenv("OPENAGENDA_API_KEY")
        self.agenda_id = os.getenv("OPENAGENDA_ID")

    def fetch_events(self) -> pd.DataFrame:
        """
        Récupère les événements d'un agenda Open Agenda via pagination.
        FILTRE API : Ne demande que les événements qui ont lieu à partir d'il y a 30 jours.
        """

        """
        Exécute le cycle complet de collecte OpenAgenda.
        
        Implémente une boucle de pagination pour garantir l'exhaustivité 
        de la source tout en validant le schéma final (validate_schema).
        """
        
        if not self.api_key or not self.agenda_id:
            logger.error("Clés API ou ID Agenda manquants dans le .env")
            return pd.DataFrame()

        url = f"https://api.openagenda.com/v2/agendas/{self.agenda_id}/events"
        all_events = []
        after = None  
        
        start_date_filter = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        logger.info(f"Début de la récupération optimisée de l'agenda {self.agenda_id} (Events >= {start_date_filter})...")

        # --- BOUCLE DE RÉCUPÉRATION AVEC BLINDAGE ---
        while True:
            params = {
                'key': self.api_key,
                'size': 100,            
                'after': after,         
                'timings[gte]': start_date_filter, 
                'sort': 'timings.asc'   
            }
            
            try:
                # ÉTAPE 10 : Ajout du timeout (10 secondes) pour éviter les blocages infinis
                response = requests.get(url, params=params, timeout=10)
                
                # Vérifie si la requête a réussi (200 OK). Sinon, lève une exception.
                response.raise_for_status()
                
                data = response.json()
                
                events = data.get('events', [])
                if not events:
                    break 
                    
                all_events.extend(events)
                after = data.get('after')
                
                logger.info(f"Page récupérée... Total cumulé : {len(all_events)}")
                
                if not after:
                    break

            # ÉTAPE 10 : Capture des erreurs réseau spécifiques (Connexion, Timeout, DNS)
            except requests.exceptions.RequestException as e:
                logger.error(f"ERREUR RÉSEAU CRITIQUE chez OpenAgenda : {e}")
                # En cas de coupure en plein milieu, on renvoie ce qu'on a déjà récupéré 
                # ou un DF vide si rien n'a été chargé.
                break

            except Exception as e:
                logger.error(f"ERREUR INATTENDUE lors du traitement API : {e}")
                break

        if not all_events:
            logger.warning("Aucun événement trouvé ou erreur lors de la récupération.")
            return pd.DataFrame()

        # --- PHASE 1 : Enrichissement et Préparation des Données ---
        try:
            df = pd.json_normalize(all_events)
            
            # 1. CORRECTION DATE CRITIQUE
            if 'firstTiming.begin' in df.columns:
                df['start_date_converted'] = pd.to_datetime(df['firstTiming.begin'], utc=True, format='ISO8601')
            else:
                df['start_date_converted'] = pd.NaT

            if 'lastTiming.end' in df.columns:
                df['end_date_converted'] = pd.to_datetime(df['lastTiming.end'], utc=True, format='ISO8601')
            else:
                df['end_date_converted'] = pd.NaT
                
            # 2. Filtrage de sécurité (30 jours)
            df = df.dropna(subset=['end_date_converted'])
            one_month_ago = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=30)
            df_filtered = df[df['end_date_converted'] >= one_month_ago].copy()

            # 3. Gestion des colonnes manquantes (Patch KeyError)
            if 'registration' in df_filtered.columns:
                df_filtered['pricing_info'] = df_filtered['registration'].apply(
                    lambda x: x[0].get('value', 'Non précisé') if isinstance(x, list) and len(x) > 0 else 'Non précisé'
                )
            else:
                df_filtered['pricing_info'] = 'Non précisé'

            if 'conditions.fr' in df_filtered.columns:
                df_filtered['conditions'] = df_filtered['conditions.fr'].fillna('Aucune condition spécifique')
            else:
                df_filtered['conditions'] = 'Aucune condition spécifique'

            for col in ['location.address', 'location.city', 'location.name']:
                if col not in df_filtered.columns:
                    df_filtered[col] = '' if 'name' not in col else 'Lieu non précisé'
            
            df_filtered['full_address'] = df_filtered['location.address'].fillna('') + ", " + df_filtered['location.city'].fillna('')

            # --- PHASE 2 : MAPPING VERS LE STANDARD iCalendar (RFC 5545) ---
            df_filtered[self.COL_UID] = df_filtered['uid'].astype(str)
            df_filtered[self.COL_SUMMARY] = df_filtered['title.fr'].fillna('Sans titre')
            
            df_filtered[self.COL_DESCRIPTION] = (
                "Description: " + df_filtered['description.fr'].fillna('Pas de description') + 
                " - Tarifs: " + df_filtered['pricing_info'] +
                " - Conditions: " + df_filtered['conditions'] +
                " - Horaires: " + df_filtered.get('timings.fr', pd.Series(['Voir dates']*len(df_filtered))).fillna('Voir dates')
            )
            
            df_filtered[self.COL_DTSTART] = df_filtered['start_date_converted'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            df_filtered[self.COL_DTEND] = df_filtered['end_date_converted'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            df_filtered[self.COL_LOCATION] = df_filtered['location.name'] + " (" + df_filtered['full_address'] + ")"
            df_filtered[self.COL_URL] = df_filtered.get('canonicalUrl', '')

            # Validation du schéma avant retour
            self.validate_schema(df_filtered)
            
            logger.info(f"Récupération terminée. {len(df_filtered)} événements convertis au format iCalendar.")
            
            return df_filtered[self.REQUIRED_COLUMNS]

        except Exception as e:
            logger.error(f"Erreur fatale lors de la transformation des données : {e}")
            return pd.DataFrame()