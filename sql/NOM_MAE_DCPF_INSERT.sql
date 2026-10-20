INSERT INTO
    NOM_MAE_DCPF (
        id,
        descripcion,
        descripcioncorto,
        codigodcp,
        HashCalculado
    )
SELECT
    id,
    descripcion,
    descripcioncorto,
    codigodcp,
    HashCalculado
FROM
    NOM_MAE_DCPF_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_DCPF
    )