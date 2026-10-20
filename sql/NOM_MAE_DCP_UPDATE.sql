UPDATE
    (
        SELECT
            A.codigodcsa AS CodigoDCSAActual,
            B.codigodcsa AS CodigoDCSANuevo,
            A.descripcion AS descripcionActual,
            B.descripcion AS descripcionNuevo,
            A.codigo AS codigoActual,
            B.codigo AS codigoNuevo,
            A.HashCalculado AS HashCalculadoActual,
            B.HashCalculado AS HashCalculadoNuevo,
            A.FModificacion AS FModificacionActual,
            A.UModificacion AS UModificacionActual
        FROM
            NOM_MAE_DCP A
            JOIN NOM_MAE_DCP_TMP B ON A.ID = B.ID
        WHERE
            A.HashCalculado <> B.HashCalculado
    ) tabla_actualizacion
SET
    tabla_actualizacion.CodigoDCSAActual = tabla_actualizacion.CodigoDCSANuevo,
    tabla_actualizacion.descripcionActual = tabla_actualizacion.descripcionNuevo,
    tabla_actualizacion.codigoActual = tabla_actualizacion.codigoNuevo,
    tabla_actualizacion.HashCalculadoActual = tabla_actualizacion.HashCalculadoNuevo,
    tabla_actualizacion.FModificacionActual = SYSTIMESTAMP,
    tabla_actualizacion.UModificacionActual = USER