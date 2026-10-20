UPDATE
    NOM_MAE_PRINCIPIOS_ACTIVOS
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        from
            NOM_MAE_PRINCIPIOS_ACTIVOS_TMP
    )