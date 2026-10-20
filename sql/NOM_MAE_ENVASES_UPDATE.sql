UPDATE
    (
        SELECT
            A.descripcion AS descripcionActual,
            B.descripcion AS descripcionNuevo,
            A.HashCalculado AS HashCalculadoActual,
            B.HashCalculado AS HashCalculadoNuevo,
            A.FModificacion AS FModificacionActual,
            A.UModificacion AS UModificacionActual
        FROM
            NOM_MAE_ENVASES A
            JOIN NOM_MAE_ENVASES_TMP B ON A.ID = B.ID
        WHERE
            A.HashCalculado <> B.HashCalculado
    ) tabla_actualizacion
SET
    tabla_actualizacion.descripcionActual = tabla_actualizacion.descripcionNuevo,
    tabla_actualizacion.HashCalculadoActual = tabla_actualizacion.HashCalculadoNuevo,
    tabla_actualizacion.FModificacionActual = SYSTIMESTAMP,
    tabla_actualizacion.UModificacionActual = USER