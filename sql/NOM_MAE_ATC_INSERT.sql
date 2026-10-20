INSERT INTO
    NOM_MAE_ATC (id, codigo, descripcion, HashCalculado)
SELECT
    id,
    codigo,
    descripcion,
    HashCalculado
FROM
    NOM_MAE_ATC_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_ATC
    )