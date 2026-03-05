# Ce fichier api_open_agenda.py dans le dossier poc/utils : 
# script de requêtage API d'évènements d'Open Agenda qui filtre en fonction de l'uid d'un agenda.
# OPTIMISATION MAJEURE : Cette version filtre directement via l'API (timings[gte]) 
# pour ne pas télécharger tout l'historique inutilement.
# Elle gère aussi la pagination et le format de date ISO8601 pour éviter les crashs.

import requests
import pandas as pd
from datetime import datetime, timedelta
# Importation d’un module nommé logging_config qui se trouve dans le package utils
from utils.logging_config import setup_logging

logger = setup_logging()

# agenda_id est l'uid de l'agenda à lire
def fetch_events(agenda_id, api_key):
    """
    Récupère les événements d'un agenda Open Agenda via pagination.
    FILTRE API : Ne demande que les événements qui ont lieu à partir d'il y a 30 jours.
    """
    url = f"https://api.openagenda.com/v2/agendas/{agenda_id}/events"
    all_events = []
    after = None  # Initialise le curseur de pagination
    
    # Calcul de la date de filtre pour l'API (Il y a 30 jours)
    # Format requis par OpenAgenda : YYYY-MM-DD
    # Cela permet de ne récupérer que ce qui est pertinent pour le POC
    start_date_filter = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    logger.info(f"Début de la récupération optimisée de l'agenda {agenda_id} (Events >= {start_date_filter})...")

    while True:
        # Paramètres de la requête API
        params = {
            'key': api_key,
            'size': 100,            # Taille maximale par page
            'after': after,         # Curseur pour la pagination
            'timings[gte]': start_date_filter, # FILTRE CÔTÉ SERVEUR : "Greater Than or Equal" (>=)
            'sort': 'timings.asc'   # On trie par date pour avoir les plus anciens (de la période) en premier
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            events = data.get('events', [])
            if not events:
                break # Arrêt si la page est vide
                
            all_events.extend(events)
            
            # Gestion du curseur pour la page suivante
            after = data.get('after')
            
            # Log de progression (beaucoup moins verbeux car moins de pages)
            logger.info(f"Page récupérée... Total cumulé : {len(all_events)}")
            
            if not after:
                break

        except Exception as e:
            logger.error(f"Erreur durant la récupération API : {e}")
            break

    # Si aucun événement trouvé après filtrage
    if not all_events:
        logger.warning("Aucun événement trouvé pour cette période.")
        return pd.DataFrame()

    # --- Traitement des données (Pandas) ---
    df = pd.json_normalize(all_events)
    
    # 1. CORRECTION DATE CRITIQUE : Ajout de format='ISO8601'
    # Cela force Pandas à comprendre les dates avec ou sans millisecondes (le bug précédent)
    # utc=True harmonise tout le monde sur le temps universel
    try:
        df['start_date'] = pd.to_datetime(df['firstTiming.begin'], utc=True, format='ISO8601')
        df['end_date'] = pd.to_datetime(df['lastTiming.end'], utc=True, format='ISO8601')
    except Exception as conversion_error:
        logger.error(f"Erreur de conversion de date (format mixte) : {conversion_error}")
        # En cas d'erreur fatale sur les dates, on retourne vide pour ne pas crasher l'indexeur
        return pd.DataFrame()
    
    # 2. Filtrage de sécurité (Redondant avec l'API mais bonne pratique Data Engineering)
    # On s'assure ici que les données reçues correspondent bien à notre fenêtre de temps
    one_month_ago = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=30)
    df_filtered = df[df['end_date'] >= one_month_ago].copy()
    
    # 3. Construction du contenu pour l'Embedding (Vectorisation)
    # Utilisation de .fillna() pour gérer les champs vides sans erreur
    df_filtered['content_to_index'] = (
        "Titre: " + df_filtered['title.fr'].fillna('Sans titre') + 
        " - Description: " + df_filtered['description.fr'].fillna('Pas de description') + 
        " - Lieu: " + df_filtered['location.name'].fillna('Lieu non précisé')
    )
    
    logger.info(f"Récupération terminée. {len(df_filtered)} événements prêts à être indexés.")
    
    return df_filtered[['title.fr', 'start_date', 'end_date', 'content_to_index']]