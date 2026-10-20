UPDATE
    NOM_MAE_FORMA_FARMACEUTICA_SIMPLIFICADAS
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
            NOM_MAE_FORMA_FARMACEUTICA_SIMPLIFICADAS_TMP
        WHERE
            id IN (
                SELECT
                    DISTINCT id
                FROM
                    NOM_MAE_FORMA_FARMACEUTICA_SIMPLIFICADAS
                WHERE
                    FBorrado IS NOT NULL
            )
    )