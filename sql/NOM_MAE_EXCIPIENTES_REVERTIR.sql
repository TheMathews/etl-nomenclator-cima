UPDATE
    NOM_MAE_EXCIPIENTES
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
            NOM_MAE_EXCIPIENTES_TMP
        WHERE
            id IN (
                SELECT
                    DISTINCT id
                FROM
                    NOM_MAE_EXCIPIENTES
                WHERE
                    FBorrado IS NOT NULL
            )
    )