INSERT INTO
    NOM_MAE_DCSA (id, descripcion, HashCalculado)
SELECT
    id,
    descripcion,
    HashCalculado
FROM
    NOM_MAE_DCSA_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_DCSA
    )