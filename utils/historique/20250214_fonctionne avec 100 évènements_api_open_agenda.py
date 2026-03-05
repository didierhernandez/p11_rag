# Ce fichier api_open_agenda.py dans le dossier poc/utils : 
#script de requêtage API d'évènements d'Open Agenda qui filtre en fonction de l'uid d'un agenda
#en filtrant les Événements se terminant après il y a un an
#et en combinant titre et description pour le futur embedding dans content_to_index
# cette version sélectionne 100 évènements

import requests
import pandas as pd
from datetime import datetime, timedelta
# Importation d’un module nommé logging_config qui se trouve dans le package utils
#puis mportation de l’objet setup_logging (ici la fonction) depuis ce module, 
#afin de pouvoir l’utiliser directement dans le code sans préfixe de module
from utils.logging_config import setup_logging

logger = setup_logging()

# agenda_id est l'uid de l'agenda à lire
def fetch_events(agenda_id, api_key):
    """
    Récupère les événements d'un agenda Open Agenda et les filtres
    """
    url = f"https://api.openagenda.com/v2/agendas/{agenda_id}/events"
    params = {
        'key': api_key,
        'size': 100  # On en prend 100 pour le POC
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Arrête tout si erreur HTTP 4xxx ou 5xxx
        data = response.json()
        events = data.get('events', []) # Permet de traquer un JSON malformé ou `events` absent
        
        if not events:
            logger.warning("Aucun événement trouvé dans l'agenda.")
            return pd.DataFrame()

        # Transformation en DataFrame pour manipulation facile
        df = pd.json_normalize(events)
        
        # Nettoyage et conversion des dates avec utc=True pour éviter le mixage
        df['start_date'] = pd.to_datetime(df['firstTiming.begin'], utc=True)
        df['end_date'] = pd.to_datetime(df['lastTiming.end'], utc=True)
        
        # Filtrage : On définit 'one_year_ago' en UTC également
        one_year_ago = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=365)
        df_filtered = df[df['end_date'] >= one_year_ago].copy()
        
        logger.info(f"{len(df_filtered)} événements récupérés et filtrés.")
        
        # Sélection des colonnes utiles pour le RAG
        # On combine titre et description pour le futur embedding
        df_filtered['content_to_index'] = (
            "Titre: " + df_filtered['title.fr'] + 
            " - Description: " + df_filtered['description.fr'] + 
            " - Lieu: " + df_filtered['location.name']
        )
        
        return df_filtered[['title.fr', 'start_date', 'end_date', 'content_to_index']]

    except Exception as e:
        logger.error(f"Erreur lors de la récupération API : {e}")
        return pd.DataFrame()
