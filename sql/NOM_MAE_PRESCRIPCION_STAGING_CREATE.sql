BEGIN
    -- Drop seguro
    BEGIN
        EXECUTE IMMEDIATE 'DROP TABLE NOM_MAE_PRESCRIPCION_TMP';
    EXCEPTION WHEN OTHERS THEN
        IF SQLCODE != -942 THEN RAISE; END IF;
    END;

    EXECUTE IMMEDIATE 'CREATE TABLE NOM_MAE_PRESCRIPCION_TMP ( cod_nacion NUMBER PRIMARY KEY, cod_dcsa NUMBER, cod_dcp NUMBER, cod_dcpf NUMBER, cod_envase NUMBER, cod_sitreg NUMBER, contenido VARCHAR2(100), unid_contenido NUMBER, laboratorio_titular NUMBER, laboratorio_comercializador NUMBER, cod_sitreg_presen NUMBER, fec_sitreg_presen DATE, fec_comer DATE, fecha_caducidad_ultimo_lote_obligado_serializacion DATE, fecha_situacion_registro DATE, fecha_autorizacion DATE, url_fictec VARCHAR2(250), url_prosp VARCHAR2(250), des_prese VARCHAR2(350), des_nomco VARCHAR2(200), des_dosific VARCHAR2(255), nro_definitivo VARCHAR2(50), nro_conte VARCHAR2(2000), lista_psicotropo VARCHAR2(50), lista_estupefaciente VARCHAR2(50), cod_nacionales_inactivos VARCHAR2(500), sw_receta NUMBER(1), sw_especial_control_medico NUMBER(1), sw_afecta_conduccion NUMBER(1), sw_diagnostico_hospitalario NUMBER(1), sw_tiene_excipientes_decl_obligatoria NUMBER(1), sw_uso_hospitalario NUMBER(1), sw_huerfano NUMBER(1), serializacion NUMBER(1), sw_psicotropo NUMBER(1), sw_envase_clinico NUMBER(1), sw_base_a_plantas NUMBER(1), sw_estupefaciente NUMBER(1), sw_triangulo_negro NUMBER(1), sw_generico NUMBER(1), sw_comercializado NUMBER(1), sw_sustituible NUMBER(1), sw_tld NUMBER(1), importacion_paralela NUMBER(1), radiofarmaco NUMBER(1), biosimilar NUMBER(1), formasfarmaceuticas CLOB, imagenes CLOB, atc CLOB, notaseguridad CLOB, gtin CLOB, problemassuministro CLOB, HashCalculado RAW(64), FCreacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FModificacion TIMESTAMP, FBorrado TIMESTAMP, UCreacion VARCHAR2(150) DEFAULT USER, UModificacion VARCHAR2(150), UBorrado VARCHAR2(150) )';

END;