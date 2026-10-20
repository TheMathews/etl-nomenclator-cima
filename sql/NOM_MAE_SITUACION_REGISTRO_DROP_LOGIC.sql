UPDATE
    NOM_MAE_SITUACION_REGISTRO
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        from
            NOM_MAE_SITUACION_REGISTRO_TMP
    )