UPDATE
    NOM_MAE_FORMA_FARMACEUTICA
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
            NOM_MAE_FORMA_FARMACEUTICA_TMP
        WHERE
            id IN (
                SELECT
                    DISTINCT id
                FROM
                    NOM_MAE_FORMA_FARMACEUTICA
                WHERE
                    FBorrado IS NOT NULL
            )
    )