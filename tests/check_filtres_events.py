# ce fichier ./tests/check_filtres_events.py
# vérifie le respect des filtrages definis dans api_opendatasoft.py par un test unitaire des évènements à indexer :
#dates : 1 an d'historique et événements à venir, localisation : Strasbourg
#NB : type d'évènements : événements culturels, n'est pas vérifié par ce script
#NB : ce script ne gére pour l'instant que le filtre d'ODS défini en dur dans api_opendatasoft.py et il est appelé depuis indexer.py

# module standard Python qui gère les messages de journalisation
import logging
from datetime import datetime, timedelta

def check_events(documents_filtres, nom_provider):
    """
    Vérifie l'intégrité des filtres appliqués aux documents avant vectorisation.
    
    Contrôles :
    1. Localisation : Présence obligatoire de 'Strasbourg'.
    2. Fraîcheur : La date de fin ne doit pas être antérieure à J-30 (fenêtre de fraîcheur).
    """
    missing = []
    
    # Seuil de fraîcheur : 180 jours dans le passé (voir filtre à api_opendatasoft.py)
    freshness_threshold = datetime.now() - timedelta(days=180)

    for i, doc in enumerate(documents_filtres):
        # --- 1. Vérification Localisation ---
        location = doc.metadata.get("location", "").lower()
        if "strasbourg" not in location:
            # On ne bloque pas tout pour un seul événement, mais on logue l'erreur
            msg = f"Document {i} (Titre: {doc.metadata.get('title')}) hors zone géographique : {location}"
            if "LOCALISATION" not in missing: missing.append("LOCALISATION")
            logging.warning(msg)

        # --- 2. Vérification Fraîcheur des dates ---
        # Format attendu iCalendar : YYYY-MM-DDTHH:MM:SSZ
        end_date_str = doc.metadata.get("end_date", "")
        if end_date_str:
            try:
                # Parsing simplifié de la date iCalendar
                end_date = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M:%SZ")
                if end_date < freshness_threshold:
                    msg = f"Document {i} expiré (Date fin: {end_date_str})"
                    if "DATE_FRAICHEUR" not in missing: missing.append("DATE_FRAICHEUR")
                    logging.warning(msg)
            except ValueError:
                logging.error(f"Format de date invalide pour le document {i} : {end_date_str}")

    # --- 3. Verdict final ---
    # Note : On peut être plus ou moins strict ici selon le besoin POC
    # Pour ODS, dès qu'un type d'anomalie est détecté (même sur un seul document), on arréte le processus et on informe
    if missing:
        error_msg = f"Filtres invalidés pour le provider {nom_provider}. Anomalies détectées sur : {', '.join(missing)}"
        # logging.error(error_msg) # Optionnel si on raise juste après
        raise ValueError(error_msg)
        
    logging.info(f"Filtres validés avec succès pour le provider : {nom_provider}")