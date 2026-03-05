# le "Sélecteur" (Factory) : un petit fichier qui décide quelle classe charger. 
# Fichier : utils/provider_factory.py 
# Logique : Une fonction get_event_provider() qui utilise la config pour retourner l'instance appropriée.

"""
Module implémentant le design pattern "Factory" (Sélecteur) pour les providers.

Ce script décide dynamiquement quelle classe d'extraction de données charger
en fonction de la configuration de l'environnement. Cela permet de basculer
facilement d'une source à l'autre (ex: de OpenAgenda vers OpenDataSoft, Dummy, ... etc )
sans modifier la logique métier.
"""

import logging
from .base_provider import EventProvider
from .config import EVENT_SOURCE 

from .api_open_agenda import OpenAgendaProvider 
from .dummy_provider import DummyProvider
from .api_opendatasoft import OpenDataSoftProvider
from .api_nextcloud import NextcloudProvider

logger = logging.getLogger(__name__)

def get_event_provider() -> EventProvider:
    """
    Instancie et retourne le bon fournisseur d'événements.

    Cette fabrique lit la variable d'environnement `EVENT_SOURCE` centralisée 
    et initialise la classe correspondante.

    Returns:
        EventProvider: Une instance concrète héritant de EventProvider 
                       (ex: OpenDataSoftProvider, DummyProvider).

    Raises:
        ValueError: Si la variable `EVENT_SOURCE` contient une source inconnue.
        NotImplementedError: Si le provider demandé est défini mais pas encore implémenté.

    Example:
        >>> provider = get_event_provider()
        >>> df = provider.fetch_events()
    """
    
    logger.info(f"Initialisation du provider d'événements : {EVENT_SOURCE}")

    if EVENT_SOURCE == "OPENAGENDA":
        return OpenAgendaProvider()
        
    elif EVENT_SOURCE == "OPENDATASOFT":
        return OpenDataSoftProvider()
        
    elif EVENT_SOURCE == "DUMMY":
        return DummyProvider()

    elif EVENT_SOURCE == "NEXTCLOUD":
        return NextcloudProvider()

    else:
        raise ValueError(f"Source d'événement inconnue : {EVENT_SOURCE}. Vérifiez votre fichier .env.")