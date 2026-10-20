UPDATE
    (
        SELECT
            A.descripcion AS descripcionActual,
            B.descripcion AS descripcionNuevo,
            A.idformafarmaceuticasimplificada AS idformafarmaceuticasimplificadaActual,
            B.idformafarmaceuticasimplificada AS idformafarmaceuticasimplificadaNuevo,
            A.HashCalculado AS HashCalculadoActual,
            B.HashCalculado AS HashCalculadoNuevo,
            A.FModificacion AS FModificacionActual,
            A.UModificacion AS UModificacionActual
        FROM
            NOM_MAE_FORMA_FARMACEUTICA A
            JOIN NOM_MAE_FORMA_FARMACEUTICA_TMP B ON A.ID = B.ID
        WHERE
            A.HashCalculado <> B.HashCalculado
    ) tabla_actualizacion
SET
    tabla_actualizacion.descripcionActual = tabla_actualizacion.descripcionNuevo,
    tabla_actualizacion.idformafarmaceuticasimplificadaActual = tabla_actualizacion.idformafarmaceuticasimplificadaNuevo,
    tabla_actualizacion.HashCalculadoActual = tabla_actualizacion.HashCalculadoNuevo,
    tabla_actualizacion.FModificacionActual = SYSTIMESTAMP,
    tabla_actualizacion.UModificacionActual = USER