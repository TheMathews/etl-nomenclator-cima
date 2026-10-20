INSERT INTO
    NOM_MAE_FORMA_FARMACEUTICA (
        id,
        descripcion,
        idformafarmaceuticasimplificada,
        HashCalculado
    )
SELECT
    id,
    descripcion,
    idformafarmaceuticasimplificada,
    HashCalculado
FROM
    NOM_MAE_FORMA_FARMACEUTICA_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_FORMA_FARMACEUTICA
    )