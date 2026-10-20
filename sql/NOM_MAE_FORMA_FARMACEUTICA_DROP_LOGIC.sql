UPDATE
    NOM_MAE_FORMA_FARMACEUTICA
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    id NOT IN (
        SELECT
            DISTINCT id
        from
            NOM_MAE_FORMA_FARMACEUTICA_TMP
    )