UPDATE
    (
        SELECT
            A.descripcion AS descripcionActual,
            B.descripcion AS descripcionNuevo,
            A.descripcioncorto AS descripcioncortoActual,
            B.descripcioncorto AS descripcioncortoNuevo,
            A.codigodcp AS codigoActual,
            B.codigodcp AS codigoNuevo,
            A.HashCalculado AS HashCalculadoActual,
            B.HashCalculado AS HashCalculadoNuevo,
            A.FModificacion AS FModificacionActual,
            A.UModificacion AS UModificacionActual
        FROM
            NOM_MAE_DCPF A
            JOIN NOM_MAE_DCPF_TMP B ON A.ID = B.ID
        WHERE
            A.HashCalculado <> B.HashCalculado
    ) tabla_actualizacion
SET
    tabla_actualizacion.descripcionActual = tabla_actualizacion.descripcionNuevo,
    tabla_actualizacion.codigoActual = tabla_actualizacion.codigoNuevo,
    tabla_actualizacion.descripcioncortoActual = tabla_actualizacion.descripcioncortoNuevo,
    tabla_actualizacion.HashCalculadoActual = tabla_actualizacion.HashCalculadoNuevo,
    tabla_actualizacion.FModificacionActual = SYSTIMESTAMP,
    tabla_actualizacion.UModificacionActual = USER