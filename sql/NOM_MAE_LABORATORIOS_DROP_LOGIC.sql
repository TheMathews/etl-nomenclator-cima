UPDATE
    NOM_MAE_LABORATORIOS
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        from
            NOM_MAE_LABORATORIOS_TMP
    )