# le fichier /tests/exploration_proprietes_api_openagenda.py 
# exporte dans un fichier .json les éléments de l'api d'openagenda.com concernant le grand est

import requests
import json
import os
from tabulate import tabulate

def flatten_data(data, parent_key=''):
    """Aplatit un dictionnaire ou une liste en incluant toutes les sous-clés."""
    items = []
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, (dict, list)):
                items.extend(flatten_data(value, new_key))
            else:
                items.append((new_key, type(value).__name__, str(value)[:50]))
    elif isinstance(data, list):
        for i, value in enumerate(data):
            new_key = f"{parent_key}[{i}]"
            if isinstance(value, (dict, list)):
                items.extend(flatten_data(value, new_key))
            else:
                items.append((new_key, type(value).__name__, str(value)[:50]))
    return items

# URL de l'API OpenAgenda avec ta clé et les paramètres
url = "https://api.openagenda.com/v2/agendas/7430297"
params = {
    "key": "69102d97a84c460ea43c400b2529a009",
    "detailed": 1
}

# Envoi de la requête GET
response = requests.get(url, params=params)

# Vérification du statut de la réponse
if response.status_code == 200:
    data = response.json()

    # Export des données dans un fichier JSON
    script_name = os.path.basename(__file__).replace('.py', '.json')
    output_path = os.path.join('./tests', script_name)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # Affiche toutes les propriétés (y compris les sous-clés)
    flattened_data = flatten_data(data)

    # Affichage du tableau
    print(tabulate(flattened_data, headers=["Clé", "Type", "Description"], tablefmt="grid"))
else:
    print(f"Erreur : {response.status_code} - {response.text}")
