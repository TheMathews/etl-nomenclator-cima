INSERT INTO
    NOM_MAE_UNIDAD_CONTENIDO (id, codigo, HashCalculado)
SELECT
    id,
    codigo,
    HashCalculado
FROM
    NOM_MAE_UNIDAD_CONTENIDO_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_UNIDAD_CONTENIDO
    )