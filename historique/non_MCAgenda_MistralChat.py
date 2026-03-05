# Ce fichier MistralChat.py dans le dossier poc à la racine du projet est le script principal de l'application Streamlit
# Ce script va utiliser Streamlit pour l'interface visuelle (étape 9) et LangChain pour la logique interne (étapes 1 à 8). 
# Il est conçu pour lire l'index qui a été créé avec indexer.py (Standard iCalendar RFC 5545).
# C'est ici qu'est définie le prompt système de ce RAG en complément de celui du llm utilisé.
# Attention : ceci a des implications éthiques, morales, cognitives et psychologiques.

import streamlit as st
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Importations locales sécurisées
from utils.logging_config import setup_logging
# Utilisation de la configuration centralisée
from utils.config import (
    MISTRAL_API_KEY, 
    FAISS_INDEX_DIR, 
    CHAT_MODEL, 
    EMBEDDING_MODEL
)

# Configuration du logging
logger = setup_logging()

# Configuration de la page Streamlit
st.set_page_config(page_title="Assistant Événements Culturels", page_icon="🎭")
st.title("🤖 Assistant Puls-Events : Culture & Agenda")
st.markdown("---")

# --- DÉBUT DE LA LOGIQUE RAG (Retrieval-Augmented Generation) ---

def get_vector_store():
    """
    Charge la base de données vectorielle FAISS existante en utilisant les chemins configurés.
    """
    if not MISTRAL_API_KEY:
        st.error("Clé API Mistral manquante dans la configuration.")
        return None

    # Etape 2 : Chargement de l'Index Vectoriel
    # Il est CRUCIAL d'utiliser les mêmes embeddings que lors de l'indexation.
    embeddings = MistralAIEmbeddings(
        mistral_api_key=MISTRAL_API_KEY, 
        model=EMBEDDING_MODEL
    )
    
    if not FAISS_INDEX_DIR.exists():
        st.error(f"L'index FAISS est introuvable dans {FAISS_INDEX_DIR}. Veuillez lancer indexer.py.")
        return None

    try:
        # allow_dangerous_deserialization est nécessaire pour charger les fichiers .pkl de l'index
        vector_store = FAISS.load_local(
            str(FAISS_INDEX_DIR), 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        return vector_store
    except Exception as e:
        st.error(f"Erreur lors du chargement de l'index : {e}")
        return None

def format_docs(docs):
    """
    Etape 6 : Création de la Chaîne de Formatage des Documents.
    Amélioration : On extrait les métadonnées iCalendar pour aider le LLM à se repérer.
    """
    formatted = []
    for d in docs:
        # On utilise le vocabulaire standardisé iCalendar stocké dans les métadonnées
        header = f"--- ÉVÉNEMENT : {d.metadata.get('title', 'Sans titre')} ---"
        details = f"Lieu: {d.metadata.get('location', 'N/A')} | Début: {d.metadata.get('start_date', 'N/A')}"
        content = f"Détails: {d.page_content}"
        formatted.append(f"{header}\n{details}\n{content}")
    
    return "\n\n".join(formatted)

def main():
    # Initialisation de l'historique de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Affichage de l'historique
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Etape 9 : Interface de Chat
    if prompt := st.chat_input("Quel type d'événement cherchez-vous ?"):
        # 1. Afficher le message utilisateur
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Préparer le contexte RAG
        vector_store = get_vector_store()
        
        if vector_store:
            # Etape 1 : Initialisation du Modèle de Chat (LLM) via config
            llm = ChatMistralAI(
                model=CHAT_MODEL,
                temperature=0.2, # Température basse pour limiter les hallucinations
                mistral_api_key=MISTRAL_API_KEY
            )

            # Etape 3 : Conversion de FAISS en "Retriever"
            retriever = vector_store.as_retriever(search_kwargs={"k": 5})

            # Etape 4 : Définition du Template de "Prompt"
            # Ce prompt cadre les limites cognitives et éthiques de l'IA.
            template = """Tu es un assistant expert de Puls-Events pour la recommandation d'événements culturels.
            Tu dois aider l'utilisateur à trouver des idées de sorties en te basant UNIQUEMENT sur le contexte fourni.

            Règles strictes :
            1. Utilise les informations de date (DTSTART) et lieu (LOCATION) pour être précis.
            2. Si un événement est passé par rapport à aujourd'hui (février 2026), précise-le.
            3. Si la réponse n'est pas dans le contexte, dis poliment que tu n'as pas d'informations à ce sujet.
            4. Ne jamais inventer de détails techniques, de prix ou de liens URL.

            Contexte (Données iCalendar) :
            {context}

            Question de l'utilisateur : 
            {question}

            Réponse structurée et chaleureuse :"""
            
            prompt_template = ChatPromptTemplate.from_template(template)

            # Etape 7 : Assemblage de la Chaîne RAG
            rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | prompt_template
                | llm
                | StrOutputParser()
            )

            # Génération de la réponse
            with st.chat_message("assistant"):
                try:
                    # Etape 10 : Exécution avec streaming pour une meilleure expérience utilisateur
                    response_stream = rag_chain.stream(prompt)
                    response = st.write_stream(response_stream)
                    
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Désolé, une erreur technique est survenue : {e}")

if __name__ == "__main__":
    main()