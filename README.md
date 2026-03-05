# Puls-Events RAG Chatbot - Proof of Concept (POC)

**Un chatbot intelligent pour découvrir des événements culturels en temps réel, basé sur un système RAG (Retrieval-Augmented Generation) et les données d'[OpenAgenda](https://openagenda.com/) via [OpenDataSoft](https://public.opendatasoft.com/) et un début d'architecture multi-sources standardisée.**

---
## Procédure de maintenance GitHub

La **procédure stricte** pour maintenir ce dépôt propre et respecter le `.gitignore`.

---

### 1. Pourquoi certains dossiers sont ignorés ?

Le fichier `.gitignore` est configuré pour exclure les dossiers volumineux ou sensibles :

- **venv/** : Environnement virtuel (trop lourd).  
- **data/** : Index FAISS locaux (générés dynamiquement par `indexer.py`).  
- **.env** : Clés API privées (Sécurité).  
- **__pycache__/** : Fichiers de compilation Python.  

---

### 2. Procédure de mise à jour sécurisée

Si vous modifiez le code et souhaitez envoyer vos changements sur  
[github.com/didierhernandez/p11_rag](https://github.com/didierhernandez/p11_rag) :

### Bash

```bash
# 1. Vérifier l'état (ne doit pas afficher 'data' ou 'venv' dans les fichiers à ajouter)
git status

# 2. Ajouter uniquement les modifications de code
git add .

# 3. Valider avec un message clair
git commit -m "Description de la modification (ex: mise à jour du prompt RAG)"

# 4. Envoyer sur GitHub
git push origin main
```
## Présentation du projet

### Contexte métier
Puls-Events souhaite tester l’intégration d’un **chatbot intelligent** capable de fournir des **recommandations personnalisées** sur des événements culturels, en s’appuyant sur des données structurées et mises à jour en temps réel.
Ce POC démontre la faisabilité d’un système RAG pour répondre à des questions précises sur des événements (ex: concerts, expositions), avec un focus sur :
- **La pertinence des réponses** (filtres par lieu, date, catégorie).
- **La fidélité aux sources** (pas d’hallucinations, réponses basées sur les données OpenAgenda).
- **La robustesse** (gestion des questions hors contexte, événements passés).

### Objectifs du POC
| Type               | Détails                                                                                     |
|--------------------|---------------------------------------------------------------------------------------------|
| **Fonctionnels**   | - Répondre à des questions sur des événements culturels (ex: *"Qui joue au festival de jazz de Strasbourg ?"*).<br>- Filtrer les résultats par lieu/date.<br>- Gérer les cas limites (événements passés, questions hors sujet). |
| **Techniques**     | - Intégrer une architecture multi-sources (OpenAgenda, OpenDataSoft, Nextcloud) unifiée via le standard iCalendar (RFC 5545).<br>- Vectoriser les données avec **FAISS** et **Mistral Embeddings**.<br>- Évaluer la qualité des réponses avec des tests de Vérité Terrain (pytest + environnement Dummy). |

### Publics cibles
- **Utilisateurs finaux** : Amateurs de culture, touristes, ou habitants cherchant des idées de sorties qui est la cible de Plus-Events.
- **Équipes Plus-Events** : Mon responsable Jérémy projet et les équipes produit et marketing de Puls-Events pour évaluation et extension.

---

## Architecture technique

### Diagramme d’architecture
Utilisateur → [Streamlit UI] → [RAG Chain] → [FAISS Index] ← [Format iCalendar] ← [ProviderFactory] ← [ODS / OpenAgenda / Nextcloud]
1. **Sources de données (Multi-Source Connector)** :
   - OpenAgenda & OpenDataSoft : Flux publics pour les événements culturels.
   - Nextcloud / Framaspace : Connecteur WebDAV/ICS pour l'intégration d'agendas privés ou associatifs.
   - Les données sont **nettoyées**, standardisées en objets iCalendar (RFC 5545) via une ProviderFactory avant indexation, puis vectorisées.

2. **Traitement et indexation** :
   - **Nettoyage** : Suppression des doublons, normalisation des dates (UTC), enrichissement des métadonnées.
   - **Vectorisation** : Utilisation de **FAISS** + **Mistral Embeddings** pour créer un index rechercheable (CHUNK_SIZE=1000, CHUNK_OVERLAP=100).
   - **Gestion des index** : Stockage dans `/poc/data/faiss_index/`.

3. **Interface utilisateur** :
   - **Streamlit** (`MistralChat.py`) : Chatbot interactif avec historique des conversations et streaming des réponses.
   - **Pages supplémentaires dans les futures versions** : `pages/1_Feedback_Viewer.py` pour visualiser les logs d’évaluation.

4. **Évaluation** :
   - **Tests filtres ODS** (`check_filtres_events.py`) : Validation de l’efficacité des filtres d'évènements avant vectorisation.
   - **Tests unitaires** (`pytest`) : Validation de l’intégrité des données et de la similarité des embeddings.
   - **Vérité Terrain (Le Juge de Paix)** : Mode d'évaluation en circuit fermé via un DummyProvider pour comparer sémantiquement l'IA à des attentes fixes (ex: précision).

### Technologies clés
| Composant          | Technologies                                                                 |
|--------------------|------------------------------------------------------------------------------|
| **Backend**        | Python 3.10+, LangChain, FAISS, MistralAI                                   |
| **APIs**           | OpenDataSoft (`requests`, `pandas`)                                          |
| **UI**             | Streamlit                                                                     |
| **Tests**          | `pytest`, `pytest-mock`                                                       |
| **Vectorisation**  | FAISS (index local), Mistral Embeddings (`mistral-embed`)                   |
| **Logs**           | Logging personnalisé (`utils/logging_config.py`)                            |

---

## Instructions pour la reproduction

### Prérequis
- **Matériel** :
  - Machine avec **8 Go de RAM minimum** (recommandé pour Mistral Embeddings).
  - Espace disque : ~500 Mo pour les index FAISS (variable selon la taille des données).
- **Logiciels** :
  - Python 3.10+ ([téléchargement](https://www.python.org/downloads/)).
  - `git` pour cloner le dépôt.
  - Environnement virtuel (`venv`) recommandé.
- **Comptes/APIs** :
  - **Clé API Mistral** (pour les embeddings) : À ajouter dans `.env`.
  - **OpenDataSoft** : Aucune clé requise pour le dataset public `evenements-publics-openagenda`.
  - Variables **OpenAgenda/Nextcloud** optionnelles selon la source choisie.

### Installation
1. **Cloner le dépôt** :
   ```bash
   git clone [URL_DU_DEPOT]
   cd poc
   ```
2. **Créer un environnement virtuel** :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
4. **Configurer les variables d’environnement** :
Copier le fichier .env.example en .env et ajouter ta clé API Mistral :
   ```bash
   MISTRAL_API_KEY=ta_clé_ici
   ```
Note : Aucune clé n’est requise pour OpenDataSoft dans ce POC.
5. **Indexer les données** :
   ```bash
   python indexer.py
   ```
6. Lancer l’interface Streamlit :
   ```bash
   streamlit run MistralChat.py
   ```
L’interface s’ouvre dans ton navigateur par défaut (généralement http://localhost:8501).
## Description des fichiers et dossiers
| Chemin                     | Description                                                                                                                                                                                                 |
|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `/poc/`                    | Racine du projet.                                                                                                                                                                                                         |
| `.env`                     | Fichier de configuration pour la clé API Mistral. **À ne pas commiter.**                                                                                                                                   |
| `requirements.txt`         | Liste des dépendances Python (ex: `langchain`, `faiss-cpu`, `streamlit`).                                                                                                                                   |
| `MistralChat.py`           | **Point d’entrée** : Interface Streamlit du chatbot. Instancie la chaîne LangChain et le prompt RAG.                                                                                     |
| `indexer.py`               | Script pour **créer/gérer l’index FAISS**. Orchestre l’ingestion des données via le Provider choisi.                                                                                          |
| `/data/`                   | Dossier de stockage des **index FAISS** (`faiss_index.index`, `faiss_index.pkl`).                                                                                                                          |
| `/pages/1_Feedback_Viewer.py` | Page Streamlit pour **visualiser les logs d’évaluation** (réponses, scores de similarité) non implémentée pour ce POC.                                                                                                               |
| `/tests/`                  | Dossier contenant les tests unitaires et scripts d’évaluation (Vérité terrain).                                                                                                                                             |
| `/tests/check_filtres_events.py`            | **évaluation des filtres d'ODS** : vérifie le respect des filtrages definis dans api_opendatasoft.py.                                                                                                           |
| `/tests/eval_logs.csv`            | **Logs d’évaluation** : Résultats des tests (ex: scores de similarité, intégrité des données).                                                                                                           |
| `/tests/eval_dataset.json`        | Jeu de données de test pour évaluer le RAG. Contient des **scénarios prédéfinis** (questions, réponses attendues, contextes).                                                                           |
| `/tests/evaluate_rag.py`          | **Le Juge de Paix** : Évalue le RAG en comparant sémantiquement (cosinus) les réponses générées à celles de `eval_dataset.json`                                                                                                                           |
| `/tests/conftest.py`              | Configuration pour `pytest` (fixtures partagées pour les tests).                                                                                                                                         |
| `/tests/test_api_opendatasoft.py` | Tests unitaires pour `api_opendatasoft.py` (ex: validation du schéma des données, gestion des erreurs API).                                                                                             |
| `/tests/test_indexer.py`          | Tests unitaires pour `indexer.py` (ex: vérification de l’intégrité des chunks, sauvegarde de l’index).                                                                                                     |
| `/tests/check_similarity.py`      | Vérifie la **similarité entre embeddings** pour détecter les doublons ou évaluer la qualité de la vectorisation. C'est une vérification de la recherche d'information (Retrieval) via les scores L2 de la base vectorielle.                                                                                       |
| `/tests/qa_data_integrity.py`      | **Contrôle Qualité (Data QA)** : Vérifie la conformité technique des données indexées (ex : présence des champs obligatoires, validité des formats de date, détection des champs vides ou incohérents).                                                                                       |
| `/tests/test_data_integrity.py`   | Test unitaire pour valider l’**intégrité des données** (ex: dates valides, lieux non vides).                                                                                                               |
| `/utils/`                  | Modules utilitaires partagés.                                                                                                                                                                               |
| `/utils/config.py`                | **Variables globales** : Chemins, configuration active (EVENT_SOURCE) et tailles de chunks (CHUNK_SIZE=1000, CHUNK_OVERLAP=100)                                                                                                           |
| /utils/`logging_config.py`        | Configuration centralisée des logs (niveaux, formats, fichiers de sortie).                                                                                                                                 |
| `/utils/api_opendatasoft.py`      | **Provider de démonstration** : Récupère les événements depuis OpenDataSoft, applique les filtres (région "Strasbourg", dates récentes), et nettoie les données.                                                 |
| `/utils/base_provider.py`         | **Classe abstraite** définissant l’interface commune (standard iCalendar / RFC 5545) pour tous les connecteurs d'événements.                                                                |
| `/utils/dummy_provider.py`        | **Provider factice** pour les tests unitaires. Simule une API sans dépendre des sources externes : simule des données "en dur" parfaitement stables pour isoler et tester le LLM (Mistral).                                                                                                         |
| `/utils/provider_factory.py`     | **Factory** pour instancier le provider adapté.                                                                                                                   |
| `/utils/vector_store.py`          | **Réserve architecturale** : Destiné à centraliser la logique FAISS, actuellement portée temporairement par indexer.py et MistralChat.py : dans le futur, centralisation ici de la logique pour **FAISS + Mistral embeddings** : Création, chargement, et requêtage de l’index vectoriel.                                                                                                      |
## Exemples d’utilisation
| Catégorie               | Question                                                                 | Réponse Attendue                                                                                     |
|-------------------------|--------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| Précision (Nominal)     | "Qui joue au festival de jazz de Strasbourg ?"                        | "Le John Doe Quartet se produit au Strasbourg Jazz Festival - Mock Edition, au Caveau de Jazz."  |
| Robustesse              | "Quel est le prix de l’atelier peinture numérique ?"                  | "Je n’ai pas d’informations sur le prix, mais il a lieu à la Médiathèque Malraux à Strasbourg."   |
| Négativité              | "Comment faire une quiche lorraine ?"                                | "Désolé, je ne peux répondre qu’aux questions sur les événements culturels."                     |
| Filtrage Temporel       | "Peux-tu me donner des infos sur la conférence d’histoire de l’art ?" | "Cet événement a eu lieu il y a quelques jours et est désormais terminé."                        |
## Workflow typique
1. Utilisateur : Saisit une question dans l’interface Streamlit.
2. Système :

Récupère les événements pertinents depuis l’index FAISS.
Génère une réponse avec le modèle Mistral, en s’appuyant sur les données récupérées.

3. Affichage :

La réponse s’affiche progressivement (streaming).
L’historique est sauvegardé dans st.session_state.messages
## Workflows de tests et d'évaluations (Qualité QA)
Ce POC intègre une suite de tests robustes permettant de modifier le code sereinement (ex: changer le CHUNK_SIZE dans config.py ou modifier le prompt) sans risquer de créer des régressions.

1. Étape 1 : Tests Unitaires et Non-Régression (implémenté que pour ODS pour ce POC):

Avant toute chose, validez que vos modifications structurelles n'ont rien cassé.
   ```bash
   python3 -m pytest tests/
   ```
**Interprétation** : Si tout est OK, l'architecture est saine, sinon des commentaires apparaissent pour que vous sachiez exactement quelle brique (nettoyage, instanciation, etc.) a été endommagée.

2. Étape 2 : Préparation de la "Vérité Terrain"

Pour évaluer l'intelligence du chatbot (le LLM) sans être perturbé par les fluctuations des API externes, nous utilisons un "monde factice" parfaitement stable.

A- Purger l'index existant (pour forcer une reconstruction totale) :
   ```bash
   rm -rf data/faiss_index
   ```
B- Indexer le monde factice (`DummyProvider`) :
   ```bash
   export EVENT_SOURCE="DUMMY" && python indexer.py
   ```

3. Étape 3 : Contrôle Qualité de la Donnée et du Retrieval
Une fois l'indexation terminée, vérifiez que la donnée est bien présente et cherchable avant de faire intervenir l'IA.

A- Vérifier l'intégrité de la donnée (les champs obligatoires sont-ils là ?) :
   ```bash
   python tests/qa_data_integrity.py
   ```
B- Vérifier la recherche vectorielle (Retrieval) :
   ```bash
   python tests/check_similarity.py
   ```
Interprétation des Scores L2 : Plus le score est proche de 0.0, plus la correspondance sémantique est forte. Un bon résultat se situe généralement **entre 0.0 et 0.5**.

4. Étape 4 : L'Évaluation Finale (Le "Juge de Paix")

Maintenant que la base est saine, on évalue la capacité du RAG à répondre correctement aux scénarios de test prédéfinis.
   ```bash
   python tests/evaluate_rag.py
   ```
**Consulter le bulletin de notes :-)** : Ouvrez le fichier tests/eval_logs.csv pour voir vos scores de similarité. Un score de similarité cosinus **≥0.80** valide le test.
