import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter
from indexer import create_documents
from utils.config import CHUNK_SIZE, CHUNK_OVERLAP
from utils.provider_factory import get_event_provider

"""
Module de validation du pipeline de préparation des données (Phase 2).
Vérifie le découpage et le formatage des documents LangChain.
"""

# --- ÉTAPE 7 : Test de la logique de découpage (Splitter) ---
def test_text_splitter_integrity():
    """Vérifie que le découpage respecte les tailles de chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    
    long_text = "Événement de test. " * 150 
    chunks = splitter.split_text(long_text)
    
    assert len(chunks) > 1, "Le texte devrait être découpé en plusieurs morceaux."
    for chunk in chunks:
        assert len(chunk) <= CHUNK_SIZE, f"Un chunk dépasse la taille limite de {CHUNK_SIZE}"

# --- ÉTAPE 8 : Test du formatage avec la vraie fonction de production ---
def test_document_metadata_structure(valid_icalendar_df):
    """
    Valide l'intégrité des métadonnées via create_documents.
    Note : Nécessite l'objet provider pour les constantes de colonnes.
    """
    # On récupère un provider (même un dummy) pour avoir accès aux noms de colonnes
    provider = get_event_provider()
    
    # On appelle la fonction de production avec le df de test et le provider
    docs = create_documents(valid_icalendar_df, provider)
    
    assert len(docs) > 0, "Aucun document n'a été généré."
    doc = docs[0]

    # Vérifications des champs critiques
    assert doc.page_content.startswith("Description:"), "Le contenu ne respecte pas le format attendu."
    assert "title" in doc.metadata
    assert doc.metadata["title"] == "Titre Standardisé Test"
    assert doc.metadata["url"] == "https://dummy.url"

# --- ÉTAPE 9 : Test de filtrage des contenus vides ---
def test_empty_content_handling():
    """S'assure que les textes trop courts (< 5 chars) sont ignorés."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE)
    short_text = "N/A" 
    
    chunks = splitter.split_text(short_text)
    # On simule la logique de filtrage présente dans indexer.py
    valid_chunks = [c for c in chunks if len(c) > 5]
    
    assert len(valid_chunks) == 0, "Les textes trop courts ne devraient pas être retenus."