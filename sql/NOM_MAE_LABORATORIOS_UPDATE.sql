UPDATE
    (
        SELECT
            A.descripcion AS descripcionActual,
            B.descripcion AS descripcionNuevo,
            A.direccion AS direccionActual,
            B.direccion AS direccionNuevo,
            A.codigopostal AS codigopostalActual,
            B.codigopostal AS codigopostalNuevo,
            A.localidad AS localidadActual,
            B.localidad AS localidadNuevo,
            A.cif AS cifActual,
            B.cif AS cifNuevo,
            A.HashCalculado AS HashCalculadoActual,
            B.HashCalculado AS HashCalculadoNuevo,
            A.FModificacion AS FModificacionActual,
            A.UModificacion AS UModificacionActual
        FROM
            NOM_MAE_LABORATORIOS A
            JOIN NOM_MAE_LABORATORIOS_TMP B ON A.ID = B.ID
        WHERE
            A.HashCalculado <> B.HashCalculado
    ) tabla_actualizacion
SET
    tabla_actualizacion.descripcionActual = tabla_actualizacion.descripcionNuevo,
    tabla_actualizacion.direccionActual = tabla_actualizacion.direccionNuevo,
    tabla_actualizacion.codigopostalActual = tabla_actualizacion.codigopostalNuevo,
    tabla_actualizacion.localidadActual = tabla_actualizacion.localidadNuevo,
    tabla_actualizacion.cifActual = tabla_actualizacion.cifNuevo,
    tabla_actualizacion.HashCalculadoActual = tabla_actualizacion.HashCalculadoNuevo,
    tabla_actualizacion.FModificacionActual = SYSTIMESTAMP,
    tabla_actualizacion.UModificacionActual = USER