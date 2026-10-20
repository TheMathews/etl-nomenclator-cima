UPDATE
    NOM_MAE_PRESCRIPCION
SET
    FBorrado = NULL,
    UBorrado = NULL,
    FModificacion = SYSTIMESTAMP,
    UModificacion = USER
WHERE
    cod_nacion IN (
        SELECT
            DISTINCT cod_nacion
        FROM
            NOM_MAE_PRESCRIPCION_TMP
        WHERE
            cod_nacion IN (
                SELECT
                    DISTINCT cod_nacion
                FROM
                    NOM_MAE_PRESCRIPCION
                WHERE
                    FBorrado IS NOT NULL
            )
    );