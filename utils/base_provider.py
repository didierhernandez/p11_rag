# fichier dans utils/base_provider.py. 
#Il définit les clés que tous les scripts de fournisseurs d'évènement devront respecter.

"""
Module définissant le contrat de base pour les fournisseurs d'événements.

Ce fichier (base_provider.py) établit la structure fondamentale que tous les scripts 
de récupération de données (providers) doivent respecter. Il garantit que le reste 
de l'application (notamment le RAG) travaille avec un format de données unifié.
"""

from abc import ABC, abstractmethod
import pandas as pd

class EventProvider(ABC):
    """
    Classe abstraite définissant le contrat pour tout fournisseur d'événements.
    
    Cette classe force l'utilisation du vocabulaire iCalendar (RFC 5545) pour 
    standardiser les métadonnées envoyées au système de vectorisation (FAISS).

    Attributes:
        COL_UID (str): Identifiant unique de l'événement (ex: '12345@openagenda.com').
        COL_SUMMARY (str): Titre de l'événement.
        COL_DESCRIPTION (str): Description textuelle complète.
        COL_DTSTART (str): Date de début (ISO 8601, UTC).
        COL_DTEND (str): Date de fin (ISO 8601, UTC).
        COL_LOCATION (str): Nom du lieu et adresse combinés.
        COL_URL (str): Lien canonique vers l'événement original.
        REQUIRED_COLUMNS (list): Liste des colonnes obligatoires pour valider le schéma.
    """

    COL_UID = "UID"                 
    COL_SUMMARY = "SUMMARY"         
    COL_DESCRIPTION = "DESCRIPTION" 
    COL_DTSTART = "DTSTART"         
    COL_DTEND = "DTEND"             
    COL_LOCATION = "LOCATION"       
    COL_URL = "URL"                 
    
    REQUIRED_COLUMNS = [
        COL_UID, COL_SUMMARY, COL_DESCRIPTION, 
        COL_DTSTART, COL_DTEND, COL_LOCATION, COL_URL
    ]

    @abstractmethod
    def fetch_events(self) -> pd.DataFrame:
        """
        Méthode obligatoire à implémenter par chaque provider concret.

        Returns:
            pd.DataFrame: Un DataFrame contenant les événements formatés. 
                          Doit obligatoirement inclure les colonnes définies 
                          dans `REQUIRED_COLUMNS`.
        """
        pass

    def validate_schema(self, df: pd.DataFrame) -> bool:
        """
        Helper pour vérifier que le DataFrame généré respecte le standard iCalendar.

        Args:
            df (pd.DataFrame): Le DataFrame d'événements à valider.

        Returns:
            bool: True si le schéma est valide ou si le DataFrame est vide.

        Raises:
            ValueError: Si des colonnes obligatoires (REQUIRED_COLUMNS) sont manquantes.
        """
        if df.empty:
            return True
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes dans le DataFrame du provider : {missing}")
        return True