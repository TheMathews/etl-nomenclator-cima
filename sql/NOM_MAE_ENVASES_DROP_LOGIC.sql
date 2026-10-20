UPDATE
    NOM_MAE_ENVASES
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        from
            NOM_MAE_ENVASES_TMP
    )