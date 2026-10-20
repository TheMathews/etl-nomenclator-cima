UPDATE
    NOM_MAE_PRESCRIPCION
SET
    FBorrado = SYSTIMESTAMP,
    UBorrado = USER
WHERE
    cod_nacion NOT IN (
        SELECT
            DISTINCT cod_nacion
        FROM
            NOM_MAE_PRESCRIPCION_TMP
    )