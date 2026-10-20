UPDATE
    (
        SELECT
            A.descripcion AS desc_actual,
            A.codigo AS cod_actual,
            A.HashCalculado AS hash_actual,
            A.UModificacion AS usuario_modificacion_actual,
            A.FModificacion AS fecha_modificacion_actual,
            B.descripcion AS desc_nueva,
            B.codigo AS cod_nuevo,
            B.HashCalculado AS hash_nuevo,
            A.ID
        FROM
            NOM_MAE_ATC A
            JOIN NOM_MAE_ATC_TMP B ON A.ID = B.ID
        WHERE
            A.HashCalculado <> B.HashCalculado
    ) tabla_actualizacion
SET
    tabla_actualizacion.desc_actual = tabla_actualizacion.desc_nueva,
    tabla_actualizacion.cod_actual = tabla_actualizacion.cod_nuevo,
    tabla_actualizacion.hash_actual = tabla_actualizacion.hash_nuevo,
    tabla_actualizacion.usuario_modificacion_actual = USER,
    tabla_actualizacion.fecha_modificacion_actual = SYSTIMESTAMP