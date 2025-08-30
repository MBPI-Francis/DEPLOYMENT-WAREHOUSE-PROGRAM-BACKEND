
CREATE_VIEW_FORM_ENTRIES_LOG = """

-- View: public.view_form_entries_log

-- DROP VIEW public.view_form_entries_log;

CREATE OR REPLACE VIEW public.view_form_entries_log
 AS
 WITH form_entries_log AS (
         SELECT pf.created_at::date AS date_encoded,
            pf.preparation_date AS date_reported,
            pf.date_computed,
            'preparation_form_report'::text AS document_type,
            pf.ref_number AS document_number,
            rm.rm_code AS mat_code,
            (- pf.qty_prepared) + pf.qty_return AS qty,
            w.wh_name AS whse_no,
            s.name AS status,
            pf.is_deleted,
            pf.is_cleared,
                CASE
                    WHEN pf.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_preparation_forms pf
             JOIN tbl_raw_materials rm ON pf.rm_code_id = rm.id
             JOIN tbl_warehouses w ON pf.warehouse_id = w.id
             LEFT JOIN tbl_status s ON pf.status_id = s.id
        UNION ALL
         SELECT tf.created_at::date AS created_at,
            tf.transfer_date,
            tf.date_computed,
            'transfer_form_report'::text AS text,
            tf.ref_number,
            rm.rm_code,
            - tf.qty_kg,
            w_from.wh_name,
            s.name,
            tf.is_deleted,
            tf.is_cleared,
                CASE
                    WHEN tf.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_transfer_forms tf
             JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
             JOIN tbl_warehouses w_from ON tf.from_warehouse_id = w_from.id
             LEFT JOIN tbl_status s ON tf.status_id = s.id
        UNION ALL
         SELECT tf.created_at::date AS created_at,
            tf.transfer_date,
            tf.date_computed,
            'transfer_form_report'::text AS text,
            tf.ref_number,
            rm.rm_code,
            tf.qty_kg,
            w_to.wh_name,
            s.name,
            tf.is_deleted,
            tf.is_cleared,
                CASE
                    WHEN tf.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_transfer_forms tf
             JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
             JOIN tbl_warehouses w_to ON tf.to_warehouse_id = w_to.id
             LEFT JOIN tbl_status s ON tf.status_id = s.id
        UNION ALL
         SELECT hf.created_at::date AS created_at,
            hf.change_status_date,
            hf.date_computed,
            'change_status_form_report'::text AS text,
            hf.ref_number,
            rm.rm_code,
            - hf.qty_kg,
            w.wh_name,
            s_current.name,
            hf.is_deleted,
            hf.is_cleared,
                CASE
                    WHEN hf.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_held_forms hf
             JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
             JOIN tbl_warehouses w ON hf.warehouse_id = w.id
             LEFT JOIN tbl_status s_current ON hf.current_status_id = s_current.id
        UNION ALL
         SELECT hf.created_at::date AS created_at,
            hf.change_status_date,
            hf.date_computed,
            'change_status_form_report'::text AS text,
            hf.ref_number,
            rm.rm_code,
            hf.qty_kg,
            w.wh_name,
            s_new.name,
            hf.is_deleted,
            hf.is_cleared,
                CASE
                    WHEN hf.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_held_forms hf
             JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
             JOIN tbl_warehouses w ON hf.warehouse_id = w.id
             LEFT JOIN tbl_status s_new ON hf.new_status_id = s_new.id
        UNION ALL
         SELECT rr.created_at::date AS created_at,
            rr.receiving_date,
            rr.date_computed,
            'receiving_form_report'::text AS text,
            rr.ref_number,
            rm.rm_code,
            rr.qty_kg,
            w.wh_name,
            s.name,
            rr.is_deleted,
            rr.is_cleared,
                CASE
                    WHEN rr.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_receiving_reports rr
             JOIN tbl_raw_materials rm ON rr.rm_code_id = rm.id
             JOIN tbl_warehouses w ON rr.warehouse_id = w.id
             LEFT JOIN tbl_status s ON rr.status_id = s.id
        UNION ALL
         SELECT outgoing.created_at::date AS created_at,
            outgoing.outgoing_date,
            outgoing.date_computed,
            'outgoing_form_report'::text AS text,
            outgoing.ref_number,
            rm.rm_code,
            - outgoing.qty_kg,
            w.wh_name,
            s.name,
            outgoing.is_deleted,
            outgoing.is_cleared,
                CASE
                    WHEN outgoing.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_outgoing_reports outgoing
             JOIN tbl_raw_materials rm ON outgoing.rm_code_id = rm.id
             JOIN tbl_warehouses w ON outgoing.warehouse_id = w.id
             LEFT JOIN tbl_status s ON outgoing.status_id = s.id
        UNION ALL
         SELECT spillage.created_at::date AS created_at,
            spillage.adjustment_date,
            spillage.date_computed,
            'adjustment_form_spillage'::text AS text,
            spillage.ref_number,
            rm.rm_code,
            - spillage.qty_kg,
            w.wh_name,
            s.name,
            spillage.is_deleted,
            spillage.is_cleared,
                CASE
                    WHEN spillage.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_spillage spillage
             JOIN tbl_raw_materials rm ON spillage.rm_code_id = rm.id
             JOIN tbl_warehouses w ON spillage.warehouse_id = w.id
             LEFT JOIN tbl_status s ON spillage.status_id = s.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_receiving_incorrect'::text AS text,
            parent.ref_number,
            rm.rm_code,
            - rr.qty_kg,
            w.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_receiving_reports rr ON tac.incorrect_receiving_id = rr.id
             JOIN tbl_warehouses w ON rr.warehouse_id = w.id
             JOIN tbl_status s ON rr.status_id = s.id
             JOIN tbl_raw_materials rm ON rr.rm_code_id = rm.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_receiving_correct'::text AS text,
            parent.ref_number,
            rm.rm_code,
            tac.qty_kg,
            w.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_receiving_reports rr ON tac.incorrect_receiving_id = rr.id
             JOIN tbl_warehouses w ON tac.warehouse_id = w.id
             JOIN tbl_status s ON tac.status_id = s.id
             JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_outgoing_incorrect'::text AS text,
            parent.ref_number,
            rm.rm_code,
            ogr.qty_kg,
            w.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_outgoing_reports ogr ON tac.incorrect_outgoing_id = ogr.id
             JOIN tbl_warehouses w ON ogr.warehouse_id = w.id
             JOIN tbl_status s ON ogr.status_id = s.id
             JOIN tbl_raw_materials rm ON ogr.rm_code_id = rm.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_outgoing_correct'::text AS text,
            parent.ref_number,
            rm.rm_code,
            - tac.qty_kg,
            w.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_outgoing_reports ogr ON tac.incorrect_outgoing_id = ogr.id
             JOIN tbl_warehouses w ON tac.warehouse_id = w.id
             JOIN tbl_status s ON tac.status_id = s.id
             JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_preparation_incorrect'::text AS text,
            parent.ref_number,
            rm.rm_code,
            pf.qty_prepared - pf.qty_return,
            w.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_preparation_forms pf ON tac.incorrect_preparation_id = pf.id
             JOIN tbl_warehouses w ON pf.warehouse_id = w.id
             JOIN tbl_status s ON pf.status_id = s.id
             JOIN tbl_raw_materials rm ON pf.rm_code_id = rm.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_preparation_correct'::text AS text,
            parent.ref_number,
            rm.rm_code,
            (- tac.qty_prepared) + tac.qty_return,
            w.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_preparation_forms pf ON tac.incorrect_preparation_id = pf.id
             JOIN tbl_warehouses w ON tac.warehouse_id = w.id
             JOIN tbl_status s ON tac.status_id = s.id
             JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_transfer_incorrect'::text AS text,
            parent.ref_number,
            rm.rm_code,
            tf.qty_kg,
            w_from.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
             JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
             JOIN tbl_warehouses w_from ON tf.from_warehouse_id = w_from.id
             LEFT JOIN tbl_status s ON tf.status_id = s.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_transfer_incorrect'::text AS text,
            parent.ref_number,
            rm.rm_code,
            - tf.qty_kg,
            w_to.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
             JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
             JOIN tbl_warehouses w_to ON tf.to_warehouse_id = w_to.id
             LEFT JOIN tbl_status s ON tf.status_id = s.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_transfer_correct'::text AS text,
            parent.ref_number,
            rm.rm_code,
            - tac.qty_kg,
            w_from.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
             JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
             JOIN tbl_warehouses w_from ON tac.from_warehouse_id = w_from.id
             LEFT JOIN tbl_status s ON tac.status_id = s.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_transfer_correct'::text AS text,
            parent.ref_number,
            rm.rm_code,
            tac.qty_kg,
            w_to.wh_name,
            s.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
             JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
             JOIN tbl_warehouses w_to ON tac.to_warehouse_id = w_to.id
             LEFT JOIN tbl_status s ON tac.status_id = s.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_change_status_incorrect'::text AS text,
            parent.ref_number,
            rm.rm_code,
            hf.qty_kg,
            w.wh_name,
            s_current.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
             JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
             JOIN tbl_warehouses w ON hf.warehouse_id = w.id
             LEFT JOIN tbl_status s_current ON hf.current_status_id = s_current.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_change_status_incorrect'::text AS text,
            parent.ref_number,
            rm.rm_code,
            - hf.qty_kg,
            w.wh_name,
            s_new.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
             JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
             JOIN tbl_warehouses w ON hf.warehouse_id = w.id
             LEFT JOIN tbl_status s_new ON hf.new_status_id = s_new.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_change_status_correct'::text AS text,
            parent.ref_number,
            rm.rm_code,
            - tac.qty_kg,
            w.wh_name,
            s_current.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
             JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
             JOIN tbl_warehouses w ON tac.warehouse_id = w.id
             LEFT JOIN tbl_status s_current ON tac.current_status_id = s_current.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        UNION ALL
         SELECT tac.created_at::date AS created_at,
            parent.adjustment_date,
            tac.date_computed,
            'adjustment_form_change_status_correct'::text AS text,
            parent.ref_number,
            rm.rm_code,
            tac.qty_kg,
            w.wh_name,
            s_new.name,
            tac.is_deleted,
            tac.is_cleared,
                CASE
                    WHEN tac.date_computed IS NOT NULL THEN 'Yes'::text
                    ELSE 'No'::text
                END AS is_computed
           FROM tbl_adjustment_correct tac
             JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
             JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
             JOIN tbl_warehouses w ON tac.warehouse_id = w.id
             LEFT JOIN tbl_status s_new ON tac.new_status_id = s_new.id
             JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
        )
 SELECT date_encoded,
    date_reported,
    document_type,
    document_number,
    mat_code,
    qty,
    whse_no,
    status,
    is_deleted,
    is_cleared,
    is_computed
   FROM form_entries_log
   WHERE date_computed IS NOT NULL AND is_deleted = false
  ORDER BY date_computed DESC, date_encoded DESC, document_type, mat_code, qty;

ALTER TABLE public.view_form_entries_log
    OWNER TO postgres;







"""