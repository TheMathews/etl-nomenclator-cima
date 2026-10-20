INSERT INTO
    NOM_MAE_PRINCIPIOS_ACTIVOS (
        id,
        codigo,
        descripcion,
        listapsicotropo,
        listaestupefaciente,
        HashCalculado
    )
SELECT
    id,
    codigo,
    descripcion,
    listapsicotropo,
    listaestupefaciente,
    HashCalculado
FROM
    NOM_MAE_PRINCIPIOS_ACTIVOS_TMP
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_PRINCIPIOS_ACTIVOS
    )