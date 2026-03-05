# Ce fichier logging_config.py dans le dossier poc/utils : 
#Configuration du logging pour suivre le comportement de l'application. 
#Suggestion : Le code fourni utilise logging, il serait bon d'avoir un fichier de configuration dédié 
#ou une fonction setup comme utils.setup_logging).

"""
Module de configuration du système de journalisation (logging).

Ce module permet de suivre le comportement de l'application de manière centralisée.
Il configure un logger standard qui affiche les messages formatés dans la console,
facilitant ainsi le débogage et la surveillance du pipeline RAG.
"""
# module standard Python qui gère les messages de journalisation
import logging
# pour afficher les logs dans la console
import sys

def setup_logging():
    """
    Configure et retourne le logger principal de l'application.

    Affiche les logs dans la console au format : '[HEURE] - [NIVEAU] - Message'.
    La fonction est idempotente : elle évite de dupliquer les handlers si elle 
    est appelée plusieurs fois à travers différents modules.

    Returns:
        logging.Logger: L'instance configurée du logger nommé "PulsEvents_RAG".
    """

    # nom de l'instance du logger
    logger = logging.getLogger("PulsEvents_RAG")
    # fixe le niveau de logging minimal à INFO
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger