INSERT INTO
    NOM_MAE_EXCIPIENTES (id, descripcion, HashCalculado)
SELECT
    id,
    descripcion,
    HashCalculado
FROM
    NOM_MAE_EXCIPIENTES_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_EXCIPIENTES
    )