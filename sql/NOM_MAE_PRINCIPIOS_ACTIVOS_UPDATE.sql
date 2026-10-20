UPDATE
    (
        SELECT
            A.descripcion AS descripcionActual,
            B.descripcion AS descripcionNuevo,
            A.codigo AS codigoActual,
            B.codigo AS codigoNuevo,
            A.listapsicotropo AS listapsicotropoActual,
            B.listapsicotropo AS listapsicotropoNuevo,
            A.listaestupefaciente AS listaestupefacienteActual,
            B.listaestupefaciente AS listaestupefacienteNuevo,
            A.HashCalculado AS HashCalculadoActual,
            B.HashCalculado AS HashCalculadoNuevo,
            A.FModificacion AS FModificacionActual,
            A.UModificacion AS UModificacionActual
        FROM
            NOM_MAE_PRINCIPIOS_ACTIVOS A
            JOIN NOM_MAE_PRINCIPIOS_ACTIVOS_TMP B ON A.ID = B.ID
        WHERE
            A.HashCalculado <> B.HashCalculado
    ) tabla_actualizacion
SET
    tabla_actualizacion.descripcionActual = tabla_actualizacion.descripcionNuevo,
    tabla_actualizacion.codigoActual = tabla_actualizacion.codigoNuevo,
    tabla_actualizacion.listapsicotropoActual = tabla_actualizacion.listapsicotropoNuevo,
    tabla_actualizacion.listaestupefacienteActual = tabla_actualizacion.listaestupefacienteNuevo,
    tabla_actualizacion.HashCalculadoActual = tabla_actualizacion.HashCalculadoNuevo,
    tabla_actualizacion.FModificacionActual = SYSTIMESTAMP,
    tabla_actualizacion.UModificacionActual = USER