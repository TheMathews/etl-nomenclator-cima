UPDATE
    NOM_MAE_UNIDAD_CONTENIDO
SET
    FBorrado = NULL,
    UBorrado = NULL,
    FModificacion = SYSTIMESTAMP,
    UModificacion = USER
WHERE
    id IN (
        SELECT
            DISTINCT id
        FROM
            NOM_MAE_UNIDAD_CONTENIDO_TMP
        WHERE
            id IN (
                SELECT
                    DISTINCT id
                FROM
                    NOM_MAE_UNIDAD_CONTENIDO
                WHERE
                    FBorrado IS NOT NULL
            )
    )