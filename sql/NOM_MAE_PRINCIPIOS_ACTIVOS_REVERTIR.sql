UPDATE
    NOM_MAE_PRINCIPIOS_ACTIVOS
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
            NOM_MAE_PRINCIPIOS_ACTIVOS_TMP
        WHERE
            id IN (
                SELECT
                    DISTINCT id
                FROM
                    NOM_MAE_PRINCIPIOS_ACTIVOS
                WHERE
                    FBorrado IS NOT NULL
            )
    )