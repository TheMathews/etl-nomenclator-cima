import os
import json

def extraer_consultas_a_ficheros():
    # 1. Asegurar que la carpeta sql existe
    os.makedirs('sql', exist_ok=True)
    
    # 2. Cargar tu viejo JSON con las queries
    print("Cargando diccionarios_legacy.json...")
    with open('diccionarios_legacy.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    lista_diccionarios = data.get("ListaDiccionarios", [])
    
    ficheros_generados = 0
    
    for dicc in lista_diccionarios:
        # Usamos NombreTabla (Ej: NOM_MAE_ATC) como el script_base
        script_base = dicc.get("NombreTabla")
        tabla_tmp = dicc.get("NombreTabla_TMP")
        
        if not script_base:
            continue
            
        print(f"Generando scripts para {script_base}...")

        # -------------------------------------------------------------
        # 1. CREATE STAGING (Envolviendo el Array en un bloque PL/SQL)
        # -------------------------------------------------------------
        creaciones_sql = dicc.get("SQLCreateTEMP", [])
        if creaciones_sql:
            plsql_block = "BEGIN\n"
            plsql_block += "    -- Drop seguro\n"
            plsql_block += "    BEGIN\n"
            plsql_block += f"        EXECUTE IMMEDIATE 'DROP TABLE {tabla_tmp}';\n"
            plsql_block += "    EXCEPTION WHEN OTHERS THEN\n"
            plsql_block += "        IF SQLCODE != -942 THEN RAISE; END IF;\n"
            plsql_block += "    END;\n\n"
            
            for sentencia in creaciones_sql:
                # Escapamos comillas simples duplicándolas para el EXECUTE IMMEDIATE
                sentencia_escapada = sentencia.replace("'", "''")
                plsql_block += f"    EXECUTE IMMEDIATE '{sentencia_escapada}';\n"
            
            plsql_block += "END;"
            
            with open(f"sql/{script_base}_STAGING_CREATE.sql", "w", encoding="utf-8") as f:
                f.write(plsql_block)
            ficheros_generados += 1

        # -------------------------------------------------------------
        # Función auxiliar para guardar queries simples
        # -------------------------------------------------------------
        def guardar_query(sufijo, clave_json):
            query = dicc.get(clave_json, "")
            if query:
                # Limpiamos el %%CLIENTE%% que he visto en tu SQLCalculoHash de ATC
                query = query.replace("_%%CLIENTE%%", "") 
                with open(f"sql/{script_base}{sufijo}", "w", encoding="utf-8") as f:
                    f.write(query)
                return 1
            return 0

        # Guardamos el resto de ficheros mapeando tus claves del JSON a los sufijos
        ficheros_generados += guardar_query("_STAGING_UPDATE_HASH.sql", "SQLCalculoHash")
        ficheros_generados += guardar_query("_INSERT.sql", "SQLInsert")
        ficheros_generados += guardar_query("_DROP_LOGIC.sql", "SQLUpdate")
        ficheros_generados += guardar_query("_REVERTIR.sql", "SQLUpdateRevertir")
        ficheros_generados += guardar_query("_UPDATE.sql", "SQLActualizaCambiosDetectados")
        ficheros_generados += guardar_query("_STAGING_DROP.sql", "SQLTruncateTMP")

    print(f"\n¡Éxito! Se han generado {ficheros_generados} ficheros .sql en la carpeta 'sql/'.")

if __name__ == "__main__":
    extraer_consultas_a_ficheros()