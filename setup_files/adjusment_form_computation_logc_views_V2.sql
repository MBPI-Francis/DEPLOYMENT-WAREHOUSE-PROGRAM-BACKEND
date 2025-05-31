
WITH ending_balance AS (
	 SELECT view_ending_stocks_balance.rawmaterialid,
		view_ending_stocks_balance.rmcode,
		view_ending_stocks_balance.warehouseid,
		view_ending_stocks_balance.warehousename,
		view_ending_stocks_balance.warehousenumber,
		view_ending_stocks_balance.new_beginning_balance,
		view_ending_stocks_balance.status,
		view_ending_stocks_balance.statusid
	   FROM view_ending_stocks_balance
	), 
	

	spillage_adjustment_form AS (
	 SELECT spillage.warehouse_id AS warehouseid,
		spillage.rm_code_id AS rawmaterialid,
		sum(spillage.qty_kg) AS total_spillage_quantity,
		spillage.date_computed AS datecomputed,
		status.name AS status,
		status.id AS statusid
	   FROM tbl_adjustment_spillage spillage
		 JOIN tbl_warehouses wh ON spillage.warehouse_id = wh.id
		 JOIN tbl_status status ON spillage.status_id = status.id
	  WHERE (spillage.is_cleared IS NULL OR spillage.is_cleared = false) 
		  AND (spillage.is_deleted IS NULL OR spillage.is_deleted = false) 
		  AND spillage.date_computed IS NULL
	  GROUP BY spillage.warehouse_id, spillage.rm_code_id, spillage.date_computed, status.name, status.id
	), 




-- ---------------------------[Receiving Form Queries]---------------------------
	adf_receiving_correct AS (
		SELECT tac.warehouse_id AS warehouseid,
		    tac.rm_code_id AS rawmaterialid,
		    sum(tac.qty_kg) AS total_received,
		    tac.date_computed AS datecomputed,
		    status.name AS status,
		    status.id AS statusid
		FROM tbl_adjustment_correct tac
			JOIN tbl_receiving_reports rr ON tac.incorrect_receiving_id = rr.id
		     JOIN tbl_warehouses wh ON tac.warehouse_id = wh.id
		     JOIN tbl_status status ON tac.status_id = status.id
		WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false)
			AND (tac.is_deleted IS NULL OR tac.is_deleted = false) 
			AND tac.date_computed IS NULL
	  	GROUP BY tac.warehouse_id, tac.rm_code_id, tac.date_computed, status.id, status.name
	),

	adf_receiving_incorrect AS (
		 SELECT rr.warehouse_id AS warehouseid,
		    rr.rm_code_id AS rawmaterialid,
		    sum(rr.qty_kg) AS total_received,
		    rr.date_computed AS datecomputed,
		    status.name AS status,
		    status.id AS statusid
		   FROM tbl_adjustment_correct tac
			 JOIN tbl_receiving_reports rr ON tac.incorrect_receiving_id = rr.id
		     JOIN tbl_warehouses wh ON rr.warehouse_id = wh.id
		     JOIN tbl_status status ON rr.status_id = status.id
		  WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false) 
				AND (tac.is_deleted IS NULL OR tac.is_deleted = false) 
		  		AND tac.date_computed IS NULL
		  GROUP BY rr.warehouse_id, 
			  rr.rm_code_id, 
			  rr.date_computed, 
			  status.id, 
			  status.name
	),


-- ---------------------------[Outgoing Form Queries]---------------------------
	adf_outgoing_correct AS (
	 SELECT tac.warehouse_id AS warehouseid,
		tac.rm_code_id AS rawmaterialid,
		sum(tac.qty_kg) AS total_ogr_qty,
		tac.date_computed AS datecomputed,
		status.name AS status,
		status.id AS statusid
	   FROM tbl_adjustment_correct tac
		 JOIN tbl_outgoing_reports ogr ON tac.incorrect_outgoing_id = ogr.id
		 JOIN tbl_warehouses wh ON tac.warehouse_id = wh.id
		 JOIN tbl_status status ON tac.status_id = status.id
	  WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false) 
	  AND (tac.is_deleted IS NULL OR tac.is_deleted = false) 
	  AND tac.date_computed IS NULL
	  GROUP BY tac.warehouse_id, tac.rm_code_id, tac.date_computed, status.id, status.name


	),


	adf_outgoing_incorrect AS (
     SELECT ogr.warehouse_id AS warehouseid,
        ogr.rm_code_id AS rawmaterialid,
        sum(ogr.qty_kg) AS total_ogr_qty,
        ogr.date_computed AS datecomputed,
        status.name AS status,
        status.id AS statusid
       FROM tbl_adjustment_correct tac
         JOIN tbl_outgoing_reports ogr ON tac.incorrect_outgoing_id = ogr.id
         JOIN tbl_warehouses wh ON ogr.warehouse_id = wh.id
         JOIN tbl_status status ON ogr.status_id = status.id
      WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false) 
	  AND (tac.is_deleted IS NULL OR tac.is_deleted = false) 
	  AND tac.date_computed IS NULL
      GROUP BY ogr.warehouse_id, ogr.rm_code_id, ogr.date_computed, status.id, status.name

	),


-- ---------------------------[Preparation Form Queries]---------------------------
	adf_preparation_correct AS  (
	 SELECT tac.warehouse_id AS warehouseid,
		tac.rm_code_id AS rawmaterialid,
		sum(tac.qty_prepared) AS total_prepared,
		sum(tac.qty_return) AS total_returned,
		tac.date_computed AS datecomputed,
		status.name AS statusname,
		status.id AS statusid
	   FROM tbl_adjustment_correct tac
		 JOIN tbl_preparation_forms pf ON tac.incorrect_preparation_id = pf.id
		 JOIN tbl_warehouses wh ON tac.warehouse_id = wh.id
		 JOIN tbl_status status ON tac.status_id = status.id
	  WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false)
		  AND (tac.is_deleted IS NULL OR tac.is_deleted = false) 
		  AND tac.date_computed IS NULL
	  GROUP BY tac.warehouse_id, tac.rm_code_id, tac.date_computed, status.id, status.name
	),


	adf_preparation_incorrect AS  (
     SELECT pf.warehouse_id AS warehouseid,
        pf.rm_code_id AS rawmaterialid,
        sum(pf.qty_prepared) AS total_prepared,
        sum(pf.qty_return) AS total_returned,
        pf.date_computed AS datecomputed,
        status.name AS statusname,
        status.id AS statusid
       FROM tbl_adjustment_correct tac
         JOIN tbl_preparation_forms pf ON tac.incorrect_preparation_id = pf.id
         JOIN tbl_warehouses wh ON pf.warehouse_id = wh.id
         JOIN tbl_status status ON pf.status_id = status.id
      WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false) 
	  AND (tac.is_deleted IS NULL OR tac.is_deleted = false) 
	  AND tac.date_computed IS NULL
      GROUP BY pf.warehouse_id, pf.rm_code_id, pf.date_computed, status.id, status.name
	),


	

-- ---------------------------[Transfer Form Queries]---------------------------
	adf_transfer_correct AS (
	     SELECT 
		 	tac.from_warehouse_id AS wh_from_id,
			tac.to_warehouse_id AS wh_to_id,
	        tac.rm_code_id AS rawmaterialid,
	        sum(tac.qty_kg) AS transferred_qty,
	        tac.date_computed AS datecomputed,
	        status.id AS statusid,
	        status.name AS status
	    FROM tbl_adjustment_correct tac
	        JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
	        JOIN tbl_warehouses wh_from ON tac.from_warehouse_id = wh_from.id
			JOIN tbl_warehouses wh_to ON tac.to_warehouse_id = wh_to.id
	        JOIN tbl_status status ON tac.status_id = status.id
	
	      WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false)
	        AND (tac.is_deleted IS NULL
	        OR tac.is_deleted = false)
	        AND tac.date_computed IS NULL
	      GROUP BY 	tac.from_warehouse_id,
	                tac.rm_code_id,
	                tac.date_computed,
	                status.id,
	                status.name,
					tac.to_warehouse_id,
					tac.rm_code_id
	),


	adf_transfer_incorrect AS (
	 SELECT 
		tf.from_warehouse_id AS wh_from_id,
		tf.to_warehouse_id AS wh_to_id,
		tf.rm_code_id AS rawmaterialid,
		sum(tf.qty_kg) AS transferred_qty,
		tf.date_computed AS datecomputed,
		status.id AS statusid,
		status.name AS status
	FROM tbl_adjustment_correct tac
		JOIN tbl_transfer_forms tf ON tac.incorrect_transfer_id = tf.id
		JOIN tbl_warehouses wh_from ON tf.from_warehouse_id = wh_from.id
		JOIN tbl_warehouses wh_to ON tf.to_warehouse_id = wh_to.id
		JOIN tbl_status status ON tf.status_id = status.id

	  WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false)
		AND (tac.is_deleted IS NULL
		OR tac.is_deleted = false)
		AND tac.date_computed IS NULL
	  GROUP BY 	tf.from_warehouse_id,
				tf.rm_code_id,
				tf.date_computed,
				status.id,
				status.name,
				tf.to_warehouse_id,
				tf.rm_code_id
		),




-- ---------------------------[Change Status Form Queries]---------------------------

	adf_change_status_correct AS (
     SELECT tac.warehouse_id AS warehouseid,
        tac.rm_code_id AS rawmaterialid,
        current_status.name AS current_status,
        new_status.name AS new_status,

		current_status.id AS current_status_id,
        new_status.id AS new_status_id,
		
        SUM(tac.qty_kg) AS total_qty,
        tac.date_computed

       FROM tbl_adjustment_correct tac
         JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
         JOIN tbl_warehouses wh ON tac.warehouse_id = wh.id
         JOIN tbl_status current_status ON tac.current_status_id = current_status.id
         JOIN tbl_status new_status ON tac.new_status_id = new_status.id
      WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false)
          AND (tac.is_deleted IS NULL OR tac.is_deleted = false)
          AND tac.date_computed IS NULL
      GROUP BY tac.warehouse_id,
        tac.rm_code_id,
        tac.date_computed,
        current_status.name,
        new_status.name,
		current_status.id,
		new_status.id
	),


	adf_change_status_incorrect AS (
	    SELECT hf.warehouse_id AS warehouseid,
        hf.rm_code_id AS rawmaterialid,
        current_status.name AS current_status,
        new_status.name AS new_status,
		current_status.id AS current_status_id,
        new_status.id AS new_status_id,
        SUM(hf.qty_kg) AS total_qty,
        hf.date_computed

       FROM tbl_adjustment_correct tac

         JOIN tbl_held_forms hf ON tac.incorrect_change_status_id = hf.id
         JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
         JOIN tbl_status current_status ON hf.current_status_id = current_status.id
         JOIN tbl_status new_status ON hf.new_status_id = new_status.id

      WHERE (tac.is_cleared IS NULL OR tac.is_cleared = false)
          AND (tac.is_deleted IS NULL OR tac.is_deleted = false)
          AND tac.date_computed IS NULL
      GROUP BY hf.warehouse_id,
        hf.rm_code_id,
        hf.date_computed,
        current_status.name,
        new_status.name,
		current_status.id,
        new_status.id
	),


-- ---------------------------[Computation Queries]---------------------------
	computed_statement AS (
	 SELECT eb.rawmaterialid,
		eb.rmcode,
		eb.warehouseid,
		eb.warehousename,
		eb.warehousenumber,
		eb.new_beginning_balance +
			CASE
				WHEN eb.status::text = 'held : reject'::text 
				THEN 
				- COALESCE(
					CASE
						WHEN spillage.status::text = 'held : reject'::text THEN spillage.total_spillage_quantity
						ELSE NULL::numeric
					END, 0::numeric
				)


				-- ----------[RECEIVING FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				- COALESCE(
							CASE
								WHEN rr_incorrect.status::text = 'held : reject'::text THEN rr_incorrect.total_received
								ELSE NULL::numeric
							END, 0::numeric
				)

				+ COALESCE(
							CASE
								WHEN rr_correct.status::text = 'held : reject'::text THEN rr_correct.total_received
								ELSE NULL::numeric
							END, 0::numeric
				)



				-- ----------[OUTGOING FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN ogr_incorrect.status::text = 'held : reject'::text THEN ogr_incorrect.total_ogr_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN ogr_correct.status::text = 'held : reject'::text THEN ogr_correct.total_ogr_qty
								ELSE NULL::numeric
							END, 0::numeric
				)



				-- ----------[PREPARATION FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
                    CASE
                        WHEN pf_incorrect.statusname::text = 'held : reject'::text THEN COALESCE(pf_incorrect.total_prepared, 0::numeric) - COALESCE(pf_incorrect.total_returned, 0::numeric)
                        ELSE NULL::numeric
                    END, 0::numeric) 

				- COALESCE(
                    CASE
                        WHEN pf_correct.statusname::text = 'held : reject'::text THEN COALESCE(pf_correct.total_prepared, 0::numeric) - COALESCE(pf_correct.total_returned, 0::numeric)
                        ELSE NULL::numeric
                    END, 0::numeric) 



				-- ----------[TRANSFER FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN tf_whfrom_incorrect.status::text = 'held : reject'::text THEN tf_whfrom_incorrect.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN tf_whto_incorrect.status::text = 'held : reject'::text THEN tf_whto_incorrect.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				- COALESCE(
							CASE
								WHEN tf_whfrom_correct.status::text = 'held : reject'::text THEN tf_whfrom_correct.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				+ COALESCE(
							CASE
								WHEN tf_whto_correct.status::text = 'held : reject'::text THEN tf_whto_correct.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				-- ----------[CHANGE STATUS FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN cs_current_incorrect.current_status::text = 'held : reject'::text THEN cs_current_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN cs_new_incorrect.new_status::text = 'held : reject'::text THEN cs_new_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)



				- COALESCE(
							CASE
								WHEN cs_current_incorrect.current_status::text = 'held : reject'::text THEN cs_current_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				+ COALESCE(
							CASE
								WHEN cs_new_incorrect.new_status::text = 'held : reject'::text THEN cs_new_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)



				WHEN eb.status::text = 'held : contaminated'::text 
				THEN 
				- COALESCE(
					CASE
						WHEN spillage.status::text = 'held : contaminated'::text THEN spillage.total_spillage_quantity
						ELSE NULL::numeric
					END, 0::numeric
				)

				-- ----------[RECEIVING FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				- COALESCE(
							CASE
								WHEN rr_incorrect.status::text = 'held : contaminated'::text THEN rr_incorrect.total_received
								ELSE NULL::numeric
							END, 0::numeric
				)

				+ COALESCE(
							CASE
								WHEN rr_correct.status::text = 'held : contaminated'::text THEN rr_correct.total_received
								ELSE NULL::numeric
							END, 0::numeric
				)



				-- ----------[OUTGOING FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN ogr_incorrect.status::text = 'held : contaminated'::text THEN ogr_incorrect.total_ogr_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN ogr_correct.status::text = 'held : contaminated'::text THEN ogr_correct.total_ogr_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				-- ----------[PREPARATION FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
                    CASE
                        WHEN pf_incorrect.statusname::text = 'held : contaminated'::text THEN COALESCE(pf_incorrect.total_prepared, 0::numeric) - COALESCE(pf_incorrect.total_returned, 0::numeric)
                        ELSE NULL::numeric
                    END, 0::numeric) 

				- COALESCE(
                    CASE
                        WHEN pf_correct.statusname::text = 'held : contaminated'::text THEN COALESCE(pf_correct.total_prepared, 0::numeric) - COALESCE(pf_correct.total_returned, 0::numeric)
                        ELSE NULL::numeric
                    END, 0::numeric) 





				-- ----------[TRANSFER FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN tf_whfrom_incorrect.status::text = 'held : contaminated'::text THEN tf_whfrom_incorrect.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN tf_whto_incorrect.status::text = 'held : contaminated'::text THEN tf_whto_incorrect.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				- COALESCE(
							CASE
								WHEN tf_whfrom_correct.status::text = 'held : contaminated'::text THEN tf_whfrom_correct.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				+ COALESCE(
							CASE
								WHEN tf_whto_correct.status::text = 'held : contaminated'::text THEN tf_whto_correct.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				-- ----------[CHANGE STATUS FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN cs_current_incorrect.current_status::text = 'held : contaminated'::text THEN cs_current_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN cs_new_incorrect.new_status::text = 'held : contaminated'::text THEN cs_new_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN cs_current_incorrect.current_status::text = 'held : contaminated'::text THEN cs_current_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				+ COALESCE(
							CASE
								WHEN cs_new_incorrect.new_status::text = 'held : contaminated'::text THEN cs_new_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)



				WHEN eb.status::text = 'held : under evaluation'::text 
				THEN 
				- COALESCE(
					CASE
						WHEN spillage.status::text = 'held : under evaluation'::text THEN spillage.total_spillage_quantity
						ELSE NULL::numeric
					END, 0::numeric
				)

				
				-- ----------[RECEIVING FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				- COALESCE(
							CASE
								WHEN rr_incorrect.status::text = 'held : under evaluation'::text THEN rr_incorrect.total_received
								ELSE NULL::numeric
							END, 0::numeric
				)

				+ COALESCE(
							CASE
								WHEN rr_correct.status::text = 'held : under evaluation'::text THEN rr_correct.total_received
								ELSE NULL::numeric
							END, 0::numeric
				)



				-- ----------[OUTGOING FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN ogr_incorrect.status::text = 'held : under evaluation'::text THEN ogr_incorrect.total_ogr_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN ogr_correct.status::text = 'held : under evaluation'::text THEN ogr_correct.total_ogr_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				-- ----------[PREPARATION FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
                    CASE
                        WHEN pf_incorrect.statusname::text = 'held : under evaluation'::text THEN COALESCE(pf_incorrect.total_prepared, 0::numeric) - COALESCE(pf_incorrect.total_returned, 0::numeric)
                        ELSE NULL::numeric
                    END, 0::numeric) 

				- COALESCE(
                    CASE
                        WHEN pf_correct.statusname::text = 'held : under evaluation'::text THEN COALESCE(pf_correct.total_prepared, 0::numeric) - COALESCE(pf_correct.total_returned, 0::numeric)
                        ELSE NULL::numeric
                    END, 0::numeric) 



				-- ----------[TRANSFER FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN tf_whfrom_incorrect.status::text = 'held : under evaluation'::text THEN tf_whfrom_incorrect.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN tf_whto_incorrect.status::text = 'held : under evaluation'::text THEN tf_whto_incorrect.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				- COALESCE(
							CASE
								WHEN tf_whfrom_correct.status::text = 'held : under evaluation'::text THEN tf_whfrom_correct.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				+ COALESCE(
							CASE
								WHEN tf_whto_correct.status::text = 'held : under evaluation'::text THEN tf_whto_correct.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)



				-- ----------[CHANGE STATUS FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN cs_current_incorrect.current_status::text = 'held : under evaluation'::text THEN cs_current_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN cs_new_incorrect.new_status::text = 'held : under evaluation'::text THEN cs_new_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN cs_current_incorrect.current_status::text = 'held : under evaluation'::text THEN cs_current_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				+ COALESCE(
							CASE
								WHEN cs_new_incorrect.new_status::text = 'held : under evaluation'::text THEN cs_new_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


					
				WHEN eb.status::text = 'good'::text 
				THEN 
				- COALESCE(
					CASE
						WHEN spillage.status::text = 'good'::text THEN spillage.total_spillage_quantity
						ELSE NULL::numeric
					END, 0::numeric
				)

				-- ----------[RECEIVING FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				- COALESCE(
							CASE
								WHEN rr_incorrect.status::text = 'good'::text THEN rr_incorrect.total_received
								ELSE NULL::numeric
							END, 0::numeric
				)

				+ COALESCE(
							CASE
								WHEN rr_correct.status::text = 'good'::text THEN rr_correct.total_received
								ELSE NULL::numeric
							END, 0::numeric
				)



				------[OUTGOING FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN ogr_incorrect.status::text = 'good'::text THEN ogr_incorrect.total_ogr_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN ogr_correct.status::text = 'good'::text THEN ogr_correct.total_ogr_qty
								ELSE NULL::numeric
							END, 0::numeric
				)



				-- ----------[PREPARATION FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
                    CASE
                        WHEN pf_incorrect.statusname::text = 'good'::text THEN COALESCE(pf_incorrect.total_prepared, 0::numeric) - COALESCE(pf_incorrect.total_returned, 0::numeric)
                        ELSE NULL::numeric
                    END, 0::numeric) 

				- COALESCE(
                    CASE
                        WHEN pf_correct.statusname::text = 'good'::text THEN COALESCE(pf_correct.total_prepared, 0::numeric) - COALESCE(pf_correct.total_returned, 0::numeric)
                        ELSE NULL::numeric
                    END, 0::numeric) 



				-- ----------[TRANSFER FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN tf_whfrom_incorrect.status::text = 'good'::text THEN tf_whfrom_incorrect.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN tf_whto_incorrect.status::text = 'good'::text THEN tf_whto_incorrect.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				- COALESCE(
							CASE
								WHEN tf_whfrom_correct.status::text = 'good'::text THEN tf_whfrom_correct.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				+ COALESCE(
							CASE
								WHEN tf_whto_correct.status::text = 'good'::text THEN tf_whto_correct.transferred_qty
								ELSE NULL::numeric
							END, 0::numeric
				)



				-- ----------[CHANGE STATUS FORM CORRECT AND INCORRECT RECORDS COMPUTATION]----------
				+ COALESCE(
							CASE
								WHEN cs_current_incorrect.current_status::text = 'good'::text THEN cs_current_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN cs_new_incorrect.new_status::text = 'good'::text THEN cs_new_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)

				- COALESCE(
							CASE
								WHEN cs_current_incorrect.current_status::text = 'good'::text THEN cs_current_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)


				+ COALESCE(
							CASE
								WHEN cs_new_incorrect.new_status::text = 'good'::text THEN cs_new_incorrect.total_qty
								ELSE NULL::numeric
							END, 0::numeric
				)



				ELSE NULL::numeric
			END AS adjusted_ending_balance,
			
		COALESCE(eb.status, ''::character varying) AS status,
		eb.statusid
	   FROM ending_balance eb

	   
	 	LEFT JOIN spillage_adjustment_form spillage 
		 	ON eb.warehouseid = spillage.warehouseid 
			 	AND eb.rawmaterialid = spillage.rawmaterialid 
			 	AND eb.statusid = spillage.statusid


				 
	-- ----------[LEFT JOIN FOR RECEIVING FORM TABLE]----------
		LEFT JOIN adf_receiving_correct rr_correct 
			ON eb.warehouseid = rr_correct.warehouseid 
			 	AND eb.rawmaterialid = rr_correct.rawmaterialid 
				AND eb.statusid = rr_correct.statusid

		LEFT JOIN adf_receiving_incorrect rr_incorrect 
			ON eb.warehouseid = rr_incorrect.warehouseid 
			 	AND eb.rawmaterialid = rr_incorrect.rawmaterialid 
				AND eb.statusid = rr_incorrect.statusid



	-- ----------[LEFT JOIN FOR OUTGOING FORM TABLE]----------
		LEFT JOIN adf_outgoing_correct ogr_correct 
			ON eb.warehouseid = ogr_correct.warehouseid 
				AND eb.rawmaterialid = ogr_correct.rawmaterialid 
				AND eb.statusid = ogr_correct.statusid

		LEFT JOIN adf_outgoing_incorrect ogr_incorrect 
			ON eb.warehouseid = ogr_incorrect.warehouseid 
				AND eb.rawmaterialid = ogr_incorrect.rawmaterialid 
				AND eb.statusid = ogr_incorrect.statusid



	-- ----------[LEFT JOIN FOR PREPARATION FORM TABLE]----------
		LEFT JOIN adf_preparation_correct pf_correct 
			ON eb.warehouseid = pf_correct.warehouseid 
				AND eb.rawmaterialid = pf_correct.rawmaterialid 
				AND eb.statusid = pf_correct.statusid

		LEFT JOIN adf_preparation_incorrect pf_incorrect 
			ON eb.warehouseid = pf_incorrect.warehouseid 
				AND eb.rawmaterialid = pf_incorrect.rawmaterialid 
				AND eb.statusid = pf_incorrect.statusid

		
	-- ----------[LEFT JOIN FOR TRANSFER FORM TABLE]----------
		LEFT JOIN adf_transfer_incorrect tf_whfrom_incorrect 
			ON eb.warehouseid = tf_whfrom_incorrect.wh_from_id 
				AND eb.rawmaterialid = tf_whfrom_incorrect.rawmaterialid 
				AND eb.statusid = tf_whfrom_incorrect.statusid

		LEFT JOIN adf_transfer_incorrect tf_whto_incorrect 
			ON eb.warehouseid = tf_whto_incorrect.wh_to_id 
				AND eb.rawmaterialid = tf_whto_incorrect.rawmaterialid 
				AND eb.statusid = tf_whto_incorrect.statusid
				
		LEFT JOIN adf_transfer_correct	tf_whfrom_correct 
			ON eb.warehouseid = tf_whfrom_correct.wh_from_id 
				AND eb.rawmaterialid = tf_whfrom_correct.rawmaterialid 
				AND eb.statusid = tf_whfrom_correct.statusid

		LEFT JOIN adf_transfer_correct tf_whto_correct 
			ON eb.warehouseid = tf_whto_correct.wh_to_id 
				AND eb.rawmaterialid = tf_whto_correct.rawmaterialid 
				AND eb.statusid = tf_whto_correct.statusid


	-- ----------[LEFT JOIN FOR CHANGE STATUS FORM TABLE]----------
	-- INCORRECT Current
		LEFT JOIN adf_change_status_incorrect cs_current_incorrect 
			ON eb.warehouseid = cs_current_incorrect.warehouseid 
				AND eb.rawmaterialid = cs_current_incorrect.rawmaterialid 
				AND eb.statusid = cs_current_incorrect.current_status_id
	-- CORRECT New
		LEFT JOIN adf_change_status_incorrect cs_new_incorrect 
			ON eb.warehouseid = cs_new_incorrect.warehouseid 
				AND eb.rawmaterialid = cs_new_incorrect.rawmaterialid 
				AND eb.statusid = cs_new_incorrect.new_status_id

	-- Current
		LEFT JOIN adf_change_status_correct cs_current_correct 
			ON eb.warehouseid = cs_current_correct.warehouseid 
				AND eb.rawmaterialid = cs_current_correct.rawmaterialid 
				AND eb.statusid = cs_current_correct.current_status_id

	-- New		
		LEFT JOIN adf_change_status_correct cs_new_correct 
			ON eb.warehouseid = cs_new_correct.warehouseid 
				AND eb.rawmaterialid = cs_new_correct.rawmaterialid 
				AND eb.statusid = cs_new_correct.new_status_id


	  ORDER BY eb.rmcode, eb.warehousename, eb.warehousenumber, (COALESCE(eb.status, ''::character varying)) NULLS FIRST
	)


 SELECT rawmaterialid,
    rmcode,
    warehouseid,
    warehousename,
    warehousenumber,
    sum(adjusted_ending_balance) AS new_beginning_balance,
    COALESCE(status, ''::character varying) AS status,
    statusid
   FROM computed_statement
  GROUP BY rawmaterialid, rmcode, warehouseid, warehousename, warehousenumber, status, statusid
  ORDER BY rmcode;


