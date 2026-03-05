# Ce fichier tests/exploration_proprietes_api_ods.py
# Script d'inspection : affiche 50 records et les exporte en CSV pour analyse détaillée.

import requests
import pandas as pd
import os
from pathlib import Path

def inspect_ods_schema_and_export():
    url = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records"
    
    # Correction : On définit le dossier et on s'assure qu'il existe
    output_dir = Path("tests")
    output_dir.mkdir(exist_ok=True) # Crée le dossier 'tests' s'il n'existe pas
    output_file = output_dir / "audit_champs_ods.csv"
    
    params = {
        'limit': 50,
        'where': "location_city='Strasbourg'" # On force la ville pour voir comment le CP est stocké
        #'q': '67000'
    }

    try:
        print(f"Interrogation de l'API OpenDataSoft en cours ({params['limit']} résultats)...")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = data.get('results', [])
        
        if not results:
            print("Aucun résultat trouvé pour Strasbourg.")
            return

        # --- PARTIE 1 : AFFICHAGE TERMINAL ---
        print(f"\n=== ANALYSE DE LA STRUCTURE (Record #1) ===")
        first_record = results[0]
        for key, value in first_record.items():
            val_str = str(value)
            if len(val_str) > 60: val_str = val_str[:57] + "..."
            prefix = ">>> " if "location" in key or "city" in key else "- "
            print(f"{prefix}{key: <25} : {val_str}")

        # --- PARTIE 2 : EXPORT CSV VIA PANDAS ---
        print(f"\n=== EXPORT CSV EN COURS ===")
        df = pd.DataFrame(results)

        # --- DIAGNOSTIC CODE POSTAL ---
        print("\n=== DIAGNOSTIC CODES POSTAUX TROUVÉS ===")
        found_zip = False
        for record in results:
            for key, value in record.items():
                if "67" in str(value):
                    print(f"Trouvé dans le champ [{key}] : {value}")
                    found_zip = True
        if not found_zip:
            print("Incroyable : Le chiffre '67' n'apparaît dans aucun champ des 50 premiers résultats.")
        
        # Sauvegarde sécurisée
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Succès ! Le fichier d'audit a été créé ici : {output_file.absolute()}")
        print(f"Nombre de colonnes détectées : {len(df.columns)}")

    except Exception as e:
        print(f"Erreur lors du processus : {e}")

if __name__ == "__main__":
    inspect_ods_schema_and_export()