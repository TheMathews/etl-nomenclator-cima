INSERT INTO
    NOM_MAE_FORMA_FARMACEUTICA_SIMPLIFICADAS (id, descripcion, HashCalculado)
SELECT
    id,
    descripcion,
    HashCalculado
FROM
    NOM_MAE_FORMA_FARMACEUTICA_SIMPLIFICADAS_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_FORMA_FARMACEUTICA_SIMPLIFICADAS
    )