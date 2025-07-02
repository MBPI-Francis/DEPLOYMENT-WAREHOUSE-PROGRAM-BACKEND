-- Preparation Form
SELECT 
    pf.created_at::date AS date_encoded,
    pf.preparation_date AS date_reported,
	pf.date_computed,
    'Preparation Form' AS document_type,
    pf.ref_number AS document_number,
    rm.rm_code AS mat_code,
 	(-pf.qty_prepared + pf.qty_return) AS qty,  -- net quantity
	w.wh_name AS whse_no,
    s.name AS status,
	pf.is_deleted
FROM tbl_preparation_forms pf
JOIN tbl_raw_materials rm ON pf.rm_code_id = rm.id
JOIN tbl_warehouses w ON pf.warehouse_id = w.id
LEFT JOIN tbl_status s ON pf.status_id = s.id
-- WHERE pf.is_deleted IS DISTINCT FROM true


UNION ALL

-- Transfer Form (OUT from source warehouse)
SELECT 
    tf.created_at::date,
    tf.transfer_date,
	tf.date_computed,
    'Transfer Form',
    tf.ref_number,
    rm.rm_code,
    -tf.qty_kg,
	    w_from.wh_name,
    s.name,
	tf.is_deleted

FROM tbl_transfer_forms tf
JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
JOIN tbl_warehouses w_from ON tf.from_warehouse_id = w_from.id
LEFT JOIN tbl_status s ON tf.status_id = s.id
-- WHERE tf.is_deleted IS DISTINCT FROM true

UNION ALL

-- Transfer Form (IN to destination warehouse)
SELECT 
    tf.created_at::date,
    tf.transfer_date,
	tf.date_computed,
    'Transfer Form',
    tf.ref_number,
    rm.rm_code,
    tf.qty_kg,
	    w_to.wh_name,
    s.name,
	tf.is_deleted

FROM tbl_transfer_forms tf
JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
JOIN tbl_warehouses w_to ON tf.to_warehouse_id = w_to.id
LEFT JOIN tbl_status s ON tf.status_id = s.id
-- WHERE tf.is_deleted IS DISTINCT FROM true

UNION ALL

-- Change Status Form (current_status → -qty)
SELECT 
    hf.created_at::date,
    hf.change_status_date,
	hf.date_computed,
    'Change Status Form',
    hf.ref_number,
    rm.rm_code,
    -hf.qty_kg,
	    w.wh_name,
    s_current.name,
	hf.is_deleted

FROM tbl_held_forms hf
JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
JOIN tbl_warehouses w ON hf.warehouse_id = w.id
LEFT JOIN tbl_status s_current ON hf.current_status_id = s_current.id
-- WHERE hf.is_deleted IS DISTINCT FROM true

UNION ALL

-- Change Status Form (new_status → +qty)
SELECT 
    hf.created_at::date,
    hf.change_status_date,
	hf.date_computed,
    'Change Status Form',
    hf.ref_number,
    rm.rm_code,
    hf.qty_kg,
	    w.wh_name,
    s_new.name,
	hf.is_deleted

FROM tbl_held_forms hf
JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
JOIN tbl_warehouses w ON hf.warehouse_id = w.id
LEFT JOIN tbl_status s_new ON hf.new_status_id = s_new.id
-- WHERE hf.is_deleted IS DISTINCT FROM true

UNION ALL

-- Receiving Form
SELECT 
    rr.created_at::date,
    rr.receiving_date,
	rr.date_computed,
    'Receiving Form',
    rr.ref_number,
    rm.rm_code,
    rr.qty_kg,
	    w.wh_name,
    s.name,
	rr.is_deleted

FROM tbl_receiving_reports rr
JOIN tbl_raw_materials rm ON rr.rm_code_id = rm.id
JOIN tbl_warehouses w ON rr.warehouse_id = w.id
LEFT JOIN tbl_status s ON rr.status_id = s.id
-- WHERE rr.is_deleted IS DISTINCT FROM true

UNION ALL

-- Outgoing Form
SELECT 
    outgoing.created_at::date,
    outgoing.outgoing_date,
	outgoing.date_computed,
    'Outgoing Form',
    outgoing.ref_number,
    rm.rm_code,
    -outgoing.qty_kg,
	    w.wh_name,
    s.name,
	outgoing.is_deleted

FROM tbl_outgoing_reports outgoing
JOIN tbl_raw_materials rm ON outgoing.rm_code_id = rm.id
JOIN tbl_warehouses w ON outgoing.warehouse_id = w.id
LEFT JOIN tbl_status s ON outgoing.status_id = s.id
-- WHERE outgoing.is_deleted IS DISTINCT FROM true

ORDER BY date_computed desc, date_encoded desc, document_type ,mat_code, qty;
