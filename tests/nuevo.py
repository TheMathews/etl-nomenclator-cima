import os
import json

def crear_plantillas_sql():
    # Asegurar que la carpeta sql existe
    os.makedirs('sql', exist_ok=True)
    
    # Leemos tu config
    with open('config/config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    sufijos = [
        "_STAGING_CREATE.sql",
        "_STAGING_UPDATE_HASH.sql",
        "_INSERT.sql",
        "_DROP_LOGIC.sql",
        "_REVERTIR.sql",
        "_UPDATE.sql",
        "_STAGING_DROP.sql"
    ]
    
    for tabla in config['tablas']:
        base = tabla['script_base']
        for sufijo in sufijos:
            ruta_archivo = os.path.join('sql', f"{base}{sufijo}")
            if not os.path.exists(ruta_archivo):
                with open(ruta_archivo, 'w', encoding='utf-8') as f:
                    f.write(f"-- TODO: Escribir query para {base}{sufijo}\n")
    
    print("¡Generación completada! Revisa la carpeta 'sql/'.")

if __name__ == "__main__":
    crear_plantillas_sql()