UPDATE
    NOM_MAE_VIAS_ADMINISTRACION
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        from
            NOM_MAE_VIAS_ADMINISTRACION_TMP
    )