UPDATE
    NOM_MAE_DCPF
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
            NOM_MAE_DCPF_TMP
        WHERE
            id IN (
                SELECT
                    DISTINCT id
                FROM
                    NOM_MAE_DCPF
                WHERE
                    FBorrado IS NOT NULL
            )
    )