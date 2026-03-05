# Ce fichier api_nextcloud.py dans le dossier poc/utils : 
# Script de récupération d'événements via un export iCalendar (.ics).
# Spécialement configuré pour Nextcloud/Framaspace (WebDAV/CalDAV).
# ÉTAPE 10 : Gestion des erreurs unifiée, protection par timeout et AUTHENTIFICATION.

"""
Fournisseur de données Nextcloud / Framaspace (WebDAV/CalDAV).

Ce module implémente l'extraction d'événements à partir de calendriers distants 
au format iCalendar (.ics). Il gère l'authentification sécurisée, le téléchargement 
du flux et la conversion des objets temporels vers le standard du POC.

Caractéristiques techniques :
- ÉTAPE 10 : Gestion robuste des erreurs réseau et protection par timeout.
- Normalisation : Conversion systématique des fuseaux horaires vers UTC (Z).
- Authentification : Support des identifiants via variables d'environnement.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timezone
import icalendar
from .base_provider import EventProvider
from utils.logging_config import setup_logging

logger = setup_logging()

class NextcloudProvider(EventProvider):
    """
    Implémentation pour un agenda Nextcloud/Framaspace avec authentification.
    """

    """
    Implémentation concrète pour l'accès aux agendas Nextcloud.
    
    Le processus suit trois phases :
    1. Connexion et téléchargement du fichier ICS.
    2. Parsing de l'objet Calendar (via icalendar).
    3. Mapping vers le schéma iCalendar interne (REQUIRED_COLUMNS).
    """

    def __init__(self):
        # Récupération des informations depuis le .env
        self.ics_url = os.getenv("NEXTCLOUD_ICS_URL")
        self.user = os.getenv("NEXTCLOUD_USER")
        self.password = os.getenv("NEXTCLOUD_PASSWORD")

    def _convert_to_utc_string(self, dt_prop) -> str:
        if not dt_prop:
            return pd.NaT
        dt_obj = dt_prop.dt
        if hasattr(dt_obj, 'astimezone'):
            return dt_obj.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            return dt_obj.strftime('%Y-%m-%dT00:00:00Z')

    def fetch_events(self) -> pd.DataFrame:
        """
        Télécharge le .ics avec authentification et parse les événements.
        """

        """
        Récupère et standardise les événements du calendrier Nextcloud.

        Returns:
            pd.DataFrame: Données formatées selon le standard iCalendar.
            Retourne un DataFrame vide en cas d'échec de connexion ou d'auth.
        """

        if not self.ics_url or not self.user or not self.password:
            logger.error("Identifiants ou URL Nextcloud manquants dans le .env")
            return pd.DataFrame()

        logger.info(f"Connexion à Nextcloud pour l'utilisateur : {self.user}")

        # --- CONFIGURATION DE LA REQUÊTE ---
        # 1. Authentification Basique
        auth = (self.user, self.password)
        
        # 2. Header User-Agent pour éviter d'être bloqué comme "robot"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            # ÉTAPE 10 : Requête avec auth, headers et timeout
            response = requests.get(
                self.ics_url, 
                auth=auth, 
                headers=headers, 
                timeout=15
            )
            
            # Si le mot de passe est faux, raise_for_status() déclenchera une erreur 401
            response.raise_for_status()
            ics_content = response.content
            logger.info("Authentification Nextcloud réussie et données récupérées.")

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("ERREUR 401 : Identifiants Nextcloud incorrects. Vérifiez votre .env")
            else:
                logger.error(f"ERREUR HTTP chez Nextcloud : {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"ERREUR INATTENDUE lors de l'accès Nextcloud : {e}")
            return pd.DataFrame()

        # --- PHASE DE PARSING (identique à la précédente) ---
        try:
            cal = icalendar.Calendar.from_ical(ics_content)
            events_data = []

            for component in cal.walk('vevent'):
                # Extraction des données
                start_dt = self._convert_to_utc_string(component.get('dtstart'))
                if pd.isna(start_dt): continue

                events_data.append({
                    self.COL_UID: str(component.get('uid', '')),
                    self.COL_SUMMARY: str(component.get('summary', 'Sans titre')),
                    self.COL_DESCRIPTION: f"Description: {str(component.get('description', ''))}",
                    self.COL_DTSTART: start_dt,
                    self.COL_DTEND: self._convert_to_utc_string(component.get('dtend')) or start_dt,
                    self.COL_LOCATION: str(component.get('location', 'Lieu non précisé')),
                    self.COL_URL: str(component.get('url', ''))
                })

            df = pd.DataFrame(events_data)
            self.validate_schema(df)
            
            logger.info(f"Nextcloud : {len(df)} événements indexés.")
            return df[self.REQUIRED_COLUMNS]

        except Exception as e:
            logger.error(f"Erreur lors du parsing ICS : {e}")
            return pd.DataFrame()