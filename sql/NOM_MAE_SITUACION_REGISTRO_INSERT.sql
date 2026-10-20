INSERT INTO
    NOM_MAE_SITUACION_REGISTRO (id, codigo, HashCalculado)
SELECT
    id,
    codigo,
    HashCalculado
FROM
    NOM_MAE_SITUACION_REGISTRO_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_SITUACION_REGISTRO
    )