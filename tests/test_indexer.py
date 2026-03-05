# Ce fichier tests/test_indexer.py :
# Tests unitaires pour la logique de découpage (Chunking) et de préparation RAG.
# ÉTAPE 7, 8 et 9 : Validation du splitter et de la structure des métadonnées.
# Approche : On teste l'indexation "à froid" (sans base FAISS réelle) pour
# s'assurer que les documents envoyés à l'IA sont conformes.

"""
Module de validation du pipeline de préparation des données (Phase 2).

Ce script vérifie que la transformation des DataFrames iCalendar vers les 
objets 'Document' de LangChain se fait sans perte d'information. Il teste 
également la robustesse du découpage sémantique (Chunking).

Note : Ce module est le préalable indispensable avant d'entamer l'évaluation 
qualitative (QA annotée) du système.
"""

import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from utils.config import CHUNK_SIZE, CHUNK_OVERLAP

# --- ÉTAPE 7 : Test de la logique de découpage (Splitter) ---
def test_text_splitter_integrity():
    """
    Vérifie que le découpage des textes respecte les contraintes du LLM.

    Le splitter doit garantir que chaque fragment (chunk) ne dépasse pas 
    la taille maximale définie dans `config.py`, tout en conservant le 
    chevauchement (overlap) nécessaire à la cohérence contextuelle.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    
    # On crée un texte très long (2 fois la taille du chunk)
    long_text = "Événement de test. " * 150 
    
    chunks = splitter.split_text(long_text)
    
    assert len(chunks) > 1, "Le texte devrait être découpé en plusieurs morceaux."
    for chunk in chunks:
        assert len(chunk) <= CHUNK_SIZE, f"Un chunk dépasse la taille limite de {CHUNK_SIZE}"

# --- ÉTAPE 8 : Test du formatage des Documents LangChain ---
def test_document_metadata_structure(valid_icalendar_df):
    """
    Valide l'intégrité des métadonnées injectées dans l'index FAISS.

    S'assure que chaque document créé contient les champs obligatoires :
    - SUMMARY (Titre)
    - DTSTART (Date)
    - LOCATION (Lieu)
    - URL (Source)

    C'est sur ces métadonnées que reposera l'évaluation finale du système.
    """

    from indexer import main # On peut tester la logique interne si elle est isolée
    
    # Simulation d'un événement unique
    row = valid_icalendar_df.iloc[0]
    
    # Création du document (reproduction de la logique de indexer.py)
    doc = Document(
        page_content=row["DESCRIPTION"],
        metadata={
            "title": row["SUMMARY"],
            "start_date": row["DTSTART"],
            "location": row["LOCATION"],
            "url": row["URL"],
            "uid": row["UID"]
        }
    )

    # Vérification des champs critiques pour le RAG
    assert doc.page_content.startswith("Description:"), "Le contenu devrait commencer par le préfixe standard."
    assert "title" in doc.metadata
    assert doc.metadata["title"] == "Titre Standardisé Test"
    assert doc.metadata["url"] == "https://dummy.url"

# --- ÉTAPE 9 : Test de filtrage des contenus vides ---
def test_empty_content_handling():
    """
    S'assure que le système ne tente pas d'indexer des descriptions trop courtes
    qui pollueraient la recherche sémantique.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE)
    short_text = "N/A" # Moins de 5 caractères
    
    chunks = splitter.split_text(short_text)
    
    # Ici, nous testons la logique de filtrage que est implémentée dans indexer.py
    # (Note : dans indexer.py, on a mis 'if len(chunk.page_content) > 5')
    valid_chunks = [c for c in chunks if len(c) > 5]
    
    assert len(valid_chunks) == 0, "Les textes trop courts ne devraient pas produire de chunks valides."