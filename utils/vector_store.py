# Ce fichier vector_store.py dans le dossier poc/utils : 
#Fonctions pour l'embedding de texte et la recherche dans l'index vectoriel (Faiss).
# Ce fichier est une "coquille vide" prête à accueillir la logique de gestion documentaire dès que je passerai à une phase d'optimisation (Phase 4). 
#Cela permettra de garder indexer.py et MistralChat.py très légers et faciles à lire, en déportant la technique "pure" du vecteur dans ce module dédié.

"""
Module de gestion de la Base Vectorielle (Phase 4 - Optimisation).

Note : Ce module est actuellement une réserve architecturale. 
Il est destiné à centraliser la logique pure de manipulation des vecteurs 
(FAISS) afin d'alléger 'indexer.py' et 'MistralChat.py'.

Objectifs futurs :
- Déportation de la logique de recherche de similarité.
- Gestion des sauvegardes et chargements d'index.
- Optimisation des paramètres de recherche (Top-K, scores de distance).
"""
