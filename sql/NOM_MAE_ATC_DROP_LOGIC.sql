UPDATE
    NOM_MAE_ATC
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        from
            NOM_MAE_ATC_TMP
    )