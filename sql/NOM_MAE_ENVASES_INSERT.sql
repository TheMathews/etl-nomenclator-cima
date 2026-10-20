INSERT INTO
    NOM_MAE_ENVASES (id, descripcion, HashCalculado)
SELECT
    id,
    descripcion,
    HashCalculado
FROM
    NOM_MAE_ENVASES_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_ENVASES
    )