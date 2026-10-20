UPDATE
    NOM_MAE_UNIDAD_CONTENIDO
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        from
            NOM_MAE_UNIDAD_CONTENIDO_TMP
    )