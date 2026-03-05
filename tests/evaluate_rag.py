# fichier tests/evaluate_rag.py utilise le jeu de données annoté pour calculer un score de précision

# fichier tests/evaluate_rag.py utilise le jeu de données annoté pour calculer un score de précision

"""
Module d'Évaluation de la Qualité RAG (Phase 5 - Performance).

Ce script constitue le 'Juge de Paix' du projet Puls-Events. Il compare les 
réponses générées par le chatbot face à une 'Vérité Terrain' (Ground Truth) 
définie manuellement dans 'eval_dataset.json' sur la base du DummyProvider.

Méthodologie d'évaluation :
- Similarité Sémantique : Utilisation de Mistral AI Embeddings pour calculer 
  la proximité cosinus entre la réponse IA et la réponse humaine.
- Seuil de Tolérance (Threshold) : Fixé à 0.80. Un score inférieur déclenche 
  une alerte de régression qualitative.
- Traçabilité : Enregistrement systématique des scores dans 'tests/eval_logs.csv' 
  pour monitorer l'impact des modifications de prompts.

Points de vigilance :
- Respect des règles du prompt (hallucinations, prix, politesse).
- Validation de la capacité de filtrage (événements passés vs futurs).
"""

import os
import sys
import json
import csv
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# --- Configuration des chemins ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from utils.logging_config import setup_logging
from utils.config import MISTRAL_API_KEY, FAISS_INDEX_DIR, CHAT_MODEL, EMBEDDING_MODEL

logger = setup_logging()
load_dotenv()

# Constantes d'évaluation
THRESHOLD = 0.80
DATASET_PATH = os.path.join(current_dir, "eval_dataset.json")
LOGS_PATH = os.path.join(current_dir, "eval_logs.csv")

def load_ground_truth():
    """
    Charge le jeu de données annoté depuis tests/eval_dataset.json.
    
    Returns:
        list: Collection de dictionnaires {category, question, expected_answer, expected_uids}.
    """
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Fichier de test introuvable : {DATASET_PATH}")
        return []
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def format_docs(docs):
    """Formate les documents iCalendar pour le LLM (identique à MistralChat.py)."""
    formatted = []
    for d in docs:
        header = f"--- ÉVÉNEMENT : {d.metadata.get('title', 'Sans titre')} ---"
        details = f"Lieu: {d.metadata.get('location', 'N/A')} | Début: {d.metadata.get('start_date', 'N/A')}"
        content = f"Détails: {d.page_content}"
        formatted.append(f"{header}\n{details}\n{content}")
    return "\n\n".join(formatted)

def build_rag_chain():
    """
    Reconstruit la chaîne RAG en mode 'Headless' (sans Streamlit) pour l'évaluation.
    """
    embeddings = MistralAIEmbeddings(mistral_api_key=MISTRAL_API_KEY, model=EMBEDDING_MODEL)
    vector_store = FAISS.load_local(str(FAISS_INDEX_DIR), embeddings, allow_dangerous_deserialization=True)
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    
    llm = ChatMistralAI(model=CHAT_MODEL, mistral_api_key=MISTRAL_API_KEY, temperature=0.2)
    
    template = """Tu es un assistant expert de Puls-Events pour la recommandation d'événements culturels.
    Tu dois aider l'utilisateur à trouver des idées de sorties en te basant UNIQUEMENT sur le contexte fourni.

    Règles strictes :
    1. Utilise les informations de date (DTSTART) et lieu (LOCATION) pour être précis.
    2. Nous sommes le {current_date}. Priorise les événements à venir.
    3. Si la réponse n'est pas dans le contexte, dis poliment que tu n'as pas d'informations à ce sujet.
    4. Ne jamais inventer de détails techniques, de prix ou de liens URL.

    Contexte (Données iCalendar) :
    {context}

    Question de l'utilisateur : 
    {question}

    Réponse structurée et chaleureuse :"""
    
    prompt_template = ChatPromptTemplate.from_template(template)
    today_str = datetime.now().strftime("%d %B %Y")
    
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough(), "current_date": lambda x: today_str}
        | prompt_template
        | llm
        | StrOutputParser()
    )
    return rag_chain

def calculate_cosine_similarity(text1, text2, embeddings_model):
    """
    Calcule la similarité mathématique cosinus entre deux textes.
    score = dot_product(V1, V2) / (norm(V1) * norm(V2))
    """
    vec1 = embeddings_model.embed_query(text1)
    vec2 = embeddings_model.embed_query(text2)
    
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    
    return dot_product / (norm_vec1 * norm_vec2)

def run_evaluation_cycle():
    """
    Orchestre le passage des tests, calcule les scores et sauvegarde les résultats.
    """
    logger.info("=== Lancement de l'évaluation RAG (Phase 5) ===")
    dataset = load_ground_truth()
    if not dataset: return
    
    rag_chain = build_rag_chain()
    embeddings = MistralAIEmbeddings(mistral_api_key=MISTRAL_API_KEY, model=EMBEDDING_MODEL)
    
    results = []
    
    for idx, test_case in enumerate(dataset, 1):
        logger.info(f"Test {idx}/{len(dataset)}: [{test_case['category']}]")
        
        # 1. Génération de la réponse
        generated_answer = rag_chain.invoke(test_case["question"])
        
        # 2. Calcul de la similarité
        score = calculate_cosine_similarity(generated_answer, test_case["expected_answer"], embeddings)
        status = "SUCCÈS" if score >= THRESHOLD else "ÉCHEC"
        
        logger.info(f"Score: {score:.4f} -> {status}")
        
        # 3. Préparation pour le log
        results.append({
            "timestamp": datetime.now().isoformat(),
            "category": test_case["category"],
            "question": test_case["question"],
            "expected_answer": test_case["expected_answer"],
            "generated_answer": generated_answer,
            "similarity_score": round(score, 4),
            "status": status
        })
    
    # Écriture dans le CSV
    file_exists = os.path.isfile(LOGS_PATH)
    with open(LOGS_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "category", "question", "expected_answer", "generated_answer", "similarity_score", "status"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)
        
    logger.info(f"=== Évaluation terminée. Logs mis à jour dans {LOGS_PATH} ===")

if __name__ == "__main__":
    run_evaluation_cycle()