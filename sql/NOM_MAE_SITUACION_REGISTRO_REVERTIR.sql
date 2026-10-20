UPDATE
    NOM_MAE_SITUACION_REGISTRO
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
            NOM_MAE_SITUACION_REGISTRO_TMP
        WHERE
            id IN (
                SELECT
                    DISTINCT id
                FROM
                    NOM_MAE_SITUACION_REGISTRO
                WHERE
                    FBorrado IS NOT NULL
            )
    )