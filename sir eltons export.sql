
WITH form_entries_log AS (

	-- Preparation Form
	SELECT 
	    pf.created_at::date AS date_encoded,
	    pf.preparation_date AS date_reported,
		pf.date_computed,
	    'preparation_form_report' AS document_type,
	    pf.ref_number AS document_number,
	    rm.rm_code AS mat_code,
	 	(-pf.qty_prepared + pf.qty_return) AS qty,  -- net quantity
		w.wh_name AS whse_no,
	    s.name AS status,
		pf.is_deleted,
		pf.is_cleared,
		CASE 
			WHEN pf.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	FROM tbl_preparation_forms pf
	JOIN tbl_raw_materials rm ON pf.rm_code_id = rm.id
	JOIN tbl_warehouses w ON pf.warehouse_id = w.id
	LEFT JOIN tbl_status s ON pf.status_id = s.id
	WHERE pf.date_computed IS NOT NULL
	-- WHERE pf.is_deleted IS DISTINCT FROM true
	
	
	UNION ALL
	
	-- Transfer Form (OUT from source warehouse)
	SELECT 
	    tf.created_at::date,
	    tf.transfer_date,
		tf.date_computed,
	    'transfer_form_report',
	    tf.ref_number,
	    rm.rm_code,
	    -tf.qty_kg,
		    w_from.wh_name,
	    s.name,
		tf.is_deleted,
		tf.is_cleared,
		CASE 
			WHEN tf.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_transfer_forms tf
	JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
	JOIN tbl_warehouses w_from ON tf.from_warehouse_id = w_from.id
	LEFT JOIN tbl_status s ON tf.status_id = s.id
	WHERE tf.date_computed IS NOT NULL
	-- WHERE tf.is_deleted IS DISTINCT FROM true
	
	UNION ALL
	
	-- Transfer Form (IN to destination warehouse)
	SELECT 
	    tf.created_at::date,
	    tf.transfer_date,
		tf.date_computed,
	    'transfer_form_report',
	    tf.ref_number,
	    rm.rm_code,
	    tf.qty_kg,
		    w_to.wh_name,
	    s.name,
		tf.is_deleted,
		tf.is_cleared,
		CASE 
			WHEN tf.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_transfer_forms tf
	JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
	JOIN tbl_warehouses w_to ON tf.to_warehouse_id = w_to.id
	LEFT JOIN tbl_status s ON tf.status_id = s.id
	WHERE tf.date_computed IS NOT NULL
	-- WHERE tf.is_deleted IS DISTINCT FROM true
	
	UNION ALL
	
	-- Change Status Form (current_status → -qty)
	SELECT 
	    hf.created_at::date,
	    hf.change_status_date,
		hf.date_computed,
	    'change_status_form_report',
	    hf.ref_number,
	    rm.rm_code,
	    -hf.qty_kg,
		    w.wh_name,
	    s_current.name,
		hf.is_deleted,
		hf.is_cleared,
		CASE 
			WHEN hf.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_held_forms hf
	JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
	JOIN tbl_warehouses w ON hf.warehouse_id = w.id
	LEFT JOIN tbl_status s_current ON hf.current_status_id = s_current.id
	WHERE hf.date_computed IS NOT NULL
	-- WHERE hf.is_deleted IS DISTINCT FROM true
	
	UNION ALL
	
	-- Change Status Form (new_status → +qty)
	SELECT 
	    hf.created_at::date,
	    hf.change_status_date,
		hf.date_computed,
	    'change_status_form_report',
	    hf.ref_number,
	    rm.rm_code,
	    hf.qty_kg,
		    w.wh_name,
	    s_new.name,
		hf.is_deleted,
		hf.is_cleared,
		CASE 
			WHEN hf.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_held_forms hf
	JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
	JOIN tbl_warehouses w ON hf.warehouse_id = w.id
	LEFT JOIN tbl_status s_new ON hf.new_status_id = s_new.id
	WHERE hf.date_computed IS NOT NULL
	-- WHERE hf.is_deleted IS DISTINCT FROM true
	
	UNION ALL
	
	-- Receiving Form
	SELECT 
	    rr.created_at::date,
	    rr.receiving_date,
		rr.date_computed,
	    'receiving_form_report',
	    rr.ref_number,
	    rm.rm_code,
	    rr.qty_kg,
		    w.wh_name,
	    s.name,
		rr.is_deleted,
		rr.is_cleared,
		CASE 
			WHEN rr.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_receiving_reports rr
	JOIN tbl_raw_materials rm ON rr.rm_code_id = rm.id
	JOIN tbl_warehouses w ON rr.warehouse_id = w.id
	LEFT JOIN tbl_status s ON rr.status_id = s.id
	WHERE rr.date_computed IS NOT NULL
	-- WHERE rr.is_deleted IS DISTINCT FROM true
	
	UNION ALL
	
	-- Outgoing Form
	SELECT 
	    outgoing.created_at::date,
	    outgoing.outgoing_date,
		outgoing.date_computed,
	    'outgoing_form_report',
	    outgoing.ref_number,
	    rm.rm_code,
	    -outgoing.qty_kg,
		    w.wh_name,
	    s.name,
		outgoing.is_deleted,
		outgoing.is_cleared,
		CASE 
			WHEN outgoing.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_outgoing_reports outgoing
	JOIN tbl_raw_materials rm ON outgoing.rm_code_id = rm.id
	JOIN tbl_warehouses w ON outgoing.warehouse_id = w.id
	LEFT JOIN tbl_status s ON outgoing.status_id = s.id
	WHERE outgoing.date_computed IS NOT NULL
	-- WHERE outgoing.is_deleted IS DISTINCT FROM true
	
	
	-- #-------------------------------------- IAF SQL Querries --------------------------------------#
	
	-- Spillage - IAF
	UNION ALL
	SELECT    
	 	spillage.created_at::date,
	    spillage.adjustment_date,
		spillage.date_computed,
	    'adjustment_form_spillage',
	    spillage.ref_number,
	    rm.rm_code,
	    -spillage.qty_kg,
		    w.wh_name,
	    s.name,
		spillage.is_deleted,
		spillage.is_cleared,
		CASE 
			WHEN spillage.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
		
	FROM tbl_adjustment_spillage spillage
	JOIN tbl_raw_materials rm ON spillage.rm_code_id = rm.id
	JOIN tbl_warehouses w ON spillage.warehouse_id = w.id
	LEFT JOIN tbl_status s ON spillage.status_id = s.id
	WHERE spillage.date_computed IS NOT NULL
	
	
	
	-- ---------------------------[Receiving Form Queries]---------------------------
	
	UNION ALL
	
		-- IAF - RR - INCORRECT
	
	SELECT 
	 	tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_receiving_incorrect',
	    parent.ref_number,
	    rm.rm_code,
	    -rr.qty_kg,
		    w.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
		
	FROM tbl_adjustment_correct tac
		JOIN tbl_receiving_reports rr ON tac.incorrect_receiving_id = rr.id
		 JOIN tbl_warehouses w ON rr.warehouse_id = w.id
		 JOIN tbl_status s ON rr.status_id = s.id
		 JOIN tbl_raw_materials rm ON rr.rm_code_id = rm.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
	
	UNION ALL
	
		-- IAF - RR - CORRECT
	SELECT 
	 	tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_receiving_correct',
	    parent.ref_number,
	    rm.rm_code,
	    tac.qty_kg,
		    w.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
		
	FROM tbl_adjustment_correct tac
		JOIN tbl_receiving_reports rr ON tac.incorrect_receiving_id = rr.id
		 JOIN tbl_warehouses w ON tac.warehouse_id = w.id
		 JOIN tbl_status s ON tac.status_id = s.id
		 JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
	
	
	
	-- ---------------------------[Outgoing Form Queries]---------------------------
	
	
		-- IAF - OGR - INCORRECT
	UNION ALL
	SELECT
	 	tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_outgoing_incorrect',
	    parent.ref_number,
	    rm.rm_code,
	    ogr.qty_kg,
		    w.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	FROM tbl_adjustment_correct tac
		 JOIN tbl_outgoing_reports ogr ON tac.incorrect_outgoing_id = ogr.id
		 JOIN tbl_warehouses w ON ogr.warehouse_id = w.id
		 JOIN tbl_status s ON ogr.status_id = s.id
		 JOIN tbl_raw_materials rm ON ogr.rm_code_id = rm.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
		 
		-- IAF - OGR - CORRECT
	UNION ALL
	SELECT
	 	tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_outgoing_correct',
	    parent.ref_number,
	    rm.rm_code,
	    -tac.qty_kg,
		    w.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	FROM tbl_adjustment_correct tac
		 JOIN tbl_outgoing_reports ogr ON tac.incorrect_outgoing_id = ogr.id
		 JOIN tbl_warehouses w ON tac.warehouse_id = w.id
		 JOIN tbl_status s ON tac.status_id = s.id
		 JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
	
	
	
	
	
	-- ---------------------------[Preparation Form Queries]---------------------------
	UNION ALL
	
	-- IAF - PF - INCORRECT
	SELECT 
		tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_preparation_incorrect',
	    parent.ref_number,
	    rm.rm_code,
	 	(pf.qty_prepared - pf.qty_return),  -- net quantity
		w.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_adjustment_correct tac
		JOIN tbl_preparation_forms pf ON tac.incorrect_preparation_id = pf.id
		 JOIN tbl_warehouses w ON pf.warehouse_id = w.id
		 JOIN tbl_status s ON pf.status_id = s.id
		 JOIN tbl_raw_materials rm ON pf.rm_code_id = rm.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
	
	UNION ALL
	-- IAF - PF - CORRECT
	SELECT 
		tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_preparation_correct',
	    parent.ref_number,
	    rm.rm_code,
	 	(-tac.qty_prepared + tac.qty_return),  -- net quantity
		w.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_adjustment_correct tac
		JOIN tbl_preparation_forms pf ON tac.incorrect_preparation_id = pf.id
		 JOIN tbl_warehouses w ON tac.warehouse_id = w.id
		 JOIN tbl_status s ON tac.status_id = s.id
		 JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
	
	
	-- ---------------------------[Transfer Form Queries]---------------------------
	
	
	UNION ALL
	-- ---------------[INCORRECT]---------------
	-- IAF - TF - Transfer Form (OUT from source warehouse)
	SELECT 
	    tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_transfer_incorrect',
	    parent.ref_number,
	    rm.rm_code,
	    tf.qty_kg,
		w_from.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_adjustment_correct tac
		JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
		JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
		JOIN tbl_warehouses w_from ON tf.from_warehouse_id = w_from.id
		LEFT JOIN tbl_status s ON tf.status_id = s.id
		JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	-- WHERE tf.is_deleted IS DISTINCT FROM true
	
	UNION ALL
	
	-- ---------------[INCORRECT]---------------
	-- Transfer Form (IN to destination warehouse)
	SELECT 
	    tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_transfer_incorrect',
	    parent.ref_number,
	    rm.rm_code,
	    -tf.qty_kg,
		w_to.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_adjustment_correct tac
		JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
		JOIN tbl_raw_materials rm ON tf.rm_code_id = rm.id
		JOIN tbl_warehouses w_to ON tf.to_warehouse_id = w_to.id
		LEFT JOIN tbl_status s ON tf.status_id = s.id
		JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	-- WHERE tf.is_deleted IS DISTINCT FROM true
	
	
	
	UNION ALL
	-- ---------------[CORRECT]---------------
	-- IAF - TF - Transfer Form (OUT from source warehouse)
	SELECT 
	    tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_transfer_correct',
	    parent.ref_number,
	    rm.rm_code,
	    -tac.qty_kg,
		w_from.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_adjustment_correct tac
	JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
	JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
	JOIN tbl_warehouses w_from ON tac.from_warehouse_id = w_from.id
	LEFT JOIN tbl_status s ON tac.status_id = s.id
	JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	-- WHERE tf.is_deleted IS DISTINCT FROM true
	
	UNION ALL
	
	-- ---------------[CORRECT]---------------
	-- Transfer Form (IN to destination warehouse)
	SELECT 
	    tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_transfer_correct',
	    parent.ref_number,
	    rm.rm_code,
	    tac.qty_kg,
		w_to.wh_name,
	    s.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	FROM tbl_adjustment_correct tac
	JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
	JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
	JOIN tbl_warehouses w_to ON tac.to_warehouse_id = w_to.id
	LEFT JOIN tbl_status s ON tac.status_id = s.id
	JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
	UNION ALL
	-- ---------------------------[Change Status Form Queries]---------------------------
	
	
	-- ---------------[INCORRECT]---------------
	-- Change Status Form (current_status → -qty)
	SELECT 
	    tac.created_at::date,
	    parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_change_status_incorrect',
	    parent.ref_number,
	    rm.rm_code,
	    hf.qty_kg,
		w.wh_name,
	    s_current.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	   FROM tbl_adjustment_correct tac
		 JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
			JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
			JOIN tbl_warehouses w ON hf.warehouse_id = w.id
			LEFT JOIN tbl_status s_current ON hf.current_status_id = s_current.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
	UNION ALL
	
	-- ---------------[INCORRECT]---------------
	-- Change Status Form (new_status → +qty)
	SELECT 
	    tac.created_at::date,
		parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_change_status_incorrect',
	    parent.ref_number,
	    rm.rm_code,
	    -hf.qty_kg,
		    w.wh_name,
	    s_new.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	   FROM tbl_adjustment_correct tac
		 JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
			JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
			JOIN tbl_warehouses w ON hf.warehouse_id = w.id
			LEFT JOIN tbl_status s_new ON hf.new_status_id = s_new.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
	
	
	
	UNION ALL
	-- ---------------[CORRECT]---------------
	-- Change Status Form (current_status → -qty)
	SELECT 
	    tac.created_at::date,
		parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_change_status_correct',
	    parent.ref_number,
	    rm.rm_code,
	    -tac.qty_kg,
		    w.wh_name,
	    s_current.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	
	   FROM tbl_adjustment_correct tac
		 JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
			JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
			JOIN tbl_warehouses w ON tac.warehouse_id = w.id
			LEFT JOIN tbl_status s_current ON tac.current_status_id = s_current.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
	
	UNION ALL
	
	-- ---------------[CORRECT]---------------
	-- Change Status Form (new_status → +qty)
	SELECT 
	    tac.created_at::date,
		parent.adjustment_date,
		tac.date_computed,
	    'adjustment_form_change_status_correct',
	    parent.ref_number,
	    rm.rm_code,
	    tac.qty_kg,
		    w.wh_name,
	    s_new.name,
		tac.is_deleted,
		tac.is_cleared,
		CASE 
			WHEN tac.date_computed IS NOT NULL THEN 'Yes'
			ELSE 'No'
		END AS is_computed
	   FROM tbl_adjustment_correct tac
		 JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
			JOIN tbl_raw_materials rm ON tac.rm_code_id = rm.id
			JOIN tbl_warehouses w ON tac.warehouse_id = w.id
			LEFT JOIN tbl_status s_new ON tac.new_status_id = s_new.id
		 JOIN tbl_adjustment_parent parent ON tac.adjustment_parent_id = parent.id
	WHERE tac.date_computed IS NOT NULL
	
		 
	ORDER BY date_computed desc, date_encoded desc, document_type ,mat_code, qty
)

SELECT 
	date_encoded,
	date_reported,
	document_type,
	document_number,
	mat_code,
	qty,
	whse_no,
	status,
	is_deleted
FROM form_entries_log
WHERE is_deleted = true