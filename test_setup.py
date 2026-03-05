# Fichier test_setup.py dans poc pour vérifier que Python parle bien à Mistral via votre clé
# mistralai est le client officiel de Mistral : SDK (Software Development Kit)
# Il permet de "parler" à l'API (envoyer un JSON, recevoir une réponse). 
#C'est ce que j'utilisedans dans ce script

import os
from dotenv import load_dotenv
from mistralai import Mistral # Nouvelle syntaxe simplifiée

# 1. Charge la clé depuis .env
load_dotenv()
api_key = os.environ.get("MISTRAL_API_KEY")

if not api_key:
    print("Erreur : Clé API non trouvée dans .env")
else:
    print("Clé API détectée.")
    try:
        # 2. Nouvelle façon d'instancier le client
        client = Mistral(api_key=api_key)
        
        # 3. Appel simplifié
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "user", "content": "Dis 'Bonjour Puls-Events' en français."}
            ]
        )
        print(f"Réponse de Mistral : {response.choices[0].message.content}")
        print("Environnement prêt !")
    except Exception as e:
        print(f"Erreur de connexion API : {e}")