INSERT INTO
    NOM_MAE_VIAS_ADMINISTRACION (id, codigo, HashCalculado)
SELECT
    id,
    codigo,
    HashCalculado
FROM
    NOM_MAE_VIAS_ADMINISTRACION_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_VIAS_ADMINISTRACION
    )