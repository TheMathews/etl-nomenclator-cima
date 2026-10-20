INSERT INTO
    NOM_MAE_DCP (
        id,
        codigo,
        descripcion,
        codigodcsa,
        HashCalculado
    )
SELECT
    id,
    codigo,
    descripcion,
    codigodcsa,
    HashCalculado
FROM
    NOM_MAE_DCP_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_DCP
    )