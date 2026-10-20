UPDATE
    NOM_MAE_EXCIPIENTES
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        from
            NOM_MAE_EXCIPIENTES_TMP
    )