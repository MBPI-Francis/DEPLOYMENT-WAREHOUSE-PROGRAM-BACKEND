    WITH initialbalance AS (
             WITH rankedrecords AS (
                     SELECT soh.warehouse_id AS warehouseid,
                        wh.wh_name AS warehousename,
                        wh.wh_number AS warehousenumber,
                        soh.rm_code_id AS rawmaterialid,
                        rm.rm_code AS rmcode,
                        soh.rm_soh AS beginningbalance,
                        soh.stock_change_date AS stockchangedate,
                        status.name AS statusname,
                        soh.status_id AS statusid,
                        row_number() OVER (PARTITION BY soh.warehouse_id, soh.rm_code_id, soh.status_id ORDER BY soh.stock_change_date DESC) AS row_num
                       FROM tbl_stock_on_hand soh
                         JOIN tbl_raw_materials rm ON soh.rm_code_id = rm.id
                         JOIN tbl_warehouses wh ON soh.warehouse_id = wh.id
                         LEFT JOIN tbl_status status ON soh.status_id = status.id
                    )
             SELECT rankedrecords.warehouseid,
                rankedrecords.warehousename,
                rankedrecords.warehousenumber,
                rankedrecords.rawmaterialid,
                rankedrecords.rmcode,
                rankedrecords.beginningbalance,
                rankedrecords.stockchangedate,
                rankedrecords.statusname,
                rankedrecords.statusid
               FROM rankedrecords
              WHERE rankedrecords.row_num = 1
            ), 
			
			ogr_adjustments AS (
             SELECT ogr.warehouse_id AS warehouseid,
                ogr.rm_code_id AS rawmaterialid,
                sum(ogr.qty_kg) AS total_ogr_quantity,
                ogr.date_computed AS datecomputed,
				status.name AS statusname,
                status.id AS statusid
               FROM tbl_outgoing_reports ogr
                 JOIN tbl_warehouses wh ON ogr.warehouse_id = wh.id
				 JOIN tbl_status status ON ogr.status_id = status.id
              WHERE (ogr.is_cleared IS NULL OR ogr.is_cleared = false) AND (ogr.is_deleted IS NULL OR ogr.is_deleted = false) AND ogr.date_computed IS NULL
              GROUP BY ogr.warehouse_id, ogr.rm_code_id, ogr.date_computed, status.name, status.id
            ), 
			
			pf_adjustments AS (
             SELECT pf.warehouse_id AS warehouseid,
                pf.rm_code_id AS rawmaterialid,
                sum(pf.qty_prepared) AS total_prepared,
                sum(pf.qty_return) AS total_returned,
                pf.date_computed AS datecomputed,
                status.name AS statusname,
                status.id AS statusid
               FROM tbl_preparation_forms pf
                 JOIN tbl_warehouses wh ON pf.warehouse_id = wh.id
                 JOIN tbl_status status ON pf.status_id = status.id
              WHERE (pf.is_cleared IS NULL OR pf.is_cleared = false) AND (pf.is_deleted IS NULL OR pf.is_deleted = false) AND pf.date_computed IS NULL
              GROUP BY pf.warehouse_id, pf.rm_code_id, pf.date_computed, status.name, status.id
            ), transferred_from AS (
             SELECT tf.from_warehouse_id AS warehouseid,
                tf.rm_code_id AS rawmaterialid,
                - sum(tf.qty_kg) AS transferred_from_qty,
                tf.date_computed AS datecomputed,
                status.id AS statusid,
                status.name AS statusname
               FROM tbl_transfer_forms tf
                 JOIN tbl_warehouses wh_from ON tf.from_warehouse_id = wh_from.id
                 LEFT JOIN tbl_status status ON tf.status_id = status.id
              WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) AND (tf.is_deleted IS NULL OR tf.is_deleted = false) AND tf.date_computed IS NULL
              GROUP BY tf.from_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
            ), transferred_to AS (
             SELECT tf.to_warehouse_id AS warehouseid,
                tf.rm_code_id AS rawmaterialid,
                sum(tf.qty_kg) AS transferred_to_qty,
                tf.date_computed AS datecomputed,
                status.id AS statusid,
                status.name AS statusname
               FROM tbl_transfer_forms tf
                 JOIN tbl_warehouses wh_to ON tf.to_warehouse_id = wh_to.id
                 LEFT JOIN tbl_status status ON tf.status_id = status.id
              WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) AND (tf.is_deleted IS NULL OR tf.is_deleted = false) AND tf.date_computed IS NULL
              GROUP BY tf.to_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
            ), rr_adjustments AS (
             SELECT rr.warehouse_id AS warehouseid,
                rr.rm_code_id AS rawmaterialid,
                sum(rr.qty_kg) AS total_received,
                rr.date_computed AS datecomputed
               FROM tbl_receiving_reports rr
                 JOIN tbl_warehouses wh ON rr.warehouse_id = wh.id
              WHERE (rr.is_cleared IS NULL OR rr.is_cleared = false) AND (rr.is_deleted IS NULL OR rr.is_deleted = false) AND rr.date_computed IS NULL
              GROUP BY rr.warehouse_id, rr.rm_code_id, rr.date_computed
            ), status_adjustments_eval AS (
             SELECT hf.warehouse_id AS warehouseid,
                hf.rm_code_id AS rawmaterialid,
                sum(
                    CASE
                        WHEN new_status.name::text ~~ 'held : contaminated'::text THEN hf.qty_kg
                        WHEN new_status.name::text ~~ 'held : reject'::text THEN hf.qty_kg
                        ELSE 0::numeric
                    END) AS total_held,
                sum(
                    CASE
                        WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
                        ELSE 0::numeric
                    END) AS total_released,
                hf.date_computed AS datecomputed
               FROM tbl_held_forms hf
                 JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
                 JOIN tbl_status current_status ON hf.current_status_id = current_status.id
                 JOIN tbl_status new_status ON hf.new_status_id = new_status.id
              WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : under evaluation'::text OR current_status.name::text = 'held : under evaluation'::text)
              GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
            ), status_adjustments_conta AS (
             SELECT hf.warehouse_id AS warehouseid,
                hf.rm_code_id AS rawmaterialid,
                sum(
                    CASE
                        WHEN new_status.name::text ~~ 'held : under evaluation'::text THEN hf.qty_kg
                        WHEN new_status.name::text ~~ 'held : reject'::text THEN hf.qty_kg
                        ELSE 0::numeric
                    END) AS total_held,
                sum(
                    CASE
                        WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
                        ELSE 0::numeric
                    END) AS total_released,
                hf.date_computed AS datecomputed
               FROM tbl_held_forms hf
                 JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
                 JOIN tbl_status current_status ON hf.current_status_id = current_status.id
                 JOIN tbl_status new_status ON hf.new_status_id = new_status.id
              WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : contaminated'::text OR current_status.name::text = 'held : contaminated'::text)
              GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
            ), status_adjustments_rejec AS (
             SELECT hf.warehouse_id AS warehouseid,
                hf.rm_code_id AS rawmaterialid,
                sum(
                    CASE
                        WHEN new_status.name::text ~~ 'held : under evaluation'::text THEN hf.qty_kg
                        WHEN new_status.name::text ~~ 'held : contaminated'::text THEN hf.qty_kg
                        ELSE 0::numeric
                    END) AS total_held,
                sum(
                    CASE
                        WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
                        ELSE 0::numeric
                    END) AS total_released,
                hf.date_computed AS datecomputed
               FROM tbl_held_forms hf
                 JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
                 JOIN tbl_status current_status ON hf.current_status_id = current_status.id
                 JOIN tbl_status new_status ON hf.new_status_id = new_status.id
              WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : reject'::text OR current_status.name::text = 'held : reject'::text)
              GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
            ), status_adjustments_good AS (
             SELECT hf.warehouse_id AS warehouseid,
                hf.rm_code_id AS rawmaterialid,
                sum(
                    CASE
                        WHEN new_status.name::text ~~ 'held%'::text THEN hf.qty_kg
                        ELSE 0::numeric
                    END) AS total_held,
                sum(
                    CASE
                        WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
                        ELSE 0::numeric
                    END) AS total_released,
                hf.date_computed AS datecomputed
               FROM tbl_held_forms hf
                 JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
                 JOIN tbl_status current_status ON hf.current_status_id = current_status.id
                 JOIN tbl_status new_status ON hf.new_status_id = new_status.id
              WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'good'::text OR current_status.name::text = 'good'::text)
              GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
            ), held_status_details AS (
             SELECT hf.rm_code_id AS rawmaterialid,
                wh.wh_name AS warehousename,
                wh.id AS warehouseid,
                wh.wh_number AS warehousenumber,
                rm.rm_code AS rmcode,
                sum(hf.qty_kg) AS heldquantity,
                new_status.name AS status,
                hf.date_computed,
                hf.new_status_id AS statusid
               FROM tbl_held_forms hf
                 JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
                 JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
                 JOIN tbl_status new_status ON hf.new_status_id = new_status.id
              WHERE new_status.name::text ~~ 'held%'::text AND (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL
              GROUP BY hf.rm_code_id, wh.wh_name, wh.wh_number, rm.rm_code, new_status.name, hf.date_computed, wh.id, hf.new_status_id
            ), computed_statement AS (
             SELECT ib.rawmaterialid,
                ib.rmcode,
                ib.warehouseid,
                ib.warehousename,
                ib.warehousenumber,
                ib.beginningbalance +
                    CASE
                        WHEN ib.statusname::text = 'held : reject'::text 
						THEN 
						(- COALESCE(rej.total_held, 0::numeric)) 
						- COALESCE(rej.total_released, 0::numeric) 
						+ COALESCE(
	                        CASE
	                            WHEN tf.statusname::text = 'held : reject'::text THEN tf.transferred_from_qty
	                            ELSE NULL::numeric
	                        END, 0::numeric) 
							
						+ COALESCE(
	                        CASE
	                            WHEN tt.statusname::text = 'held : reject'::text THEN tt.transferred_to_qty
	                            ELSE NULL::numeric
	                        END, 0::numeric) 
						
						+ COALESCE(
	                        CASE
	                            WHEN pf.statusname::text = 'held : reject'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
	                            ELSE NULL::numeric
	                        END, 0::numeric)

						+ COALESCE(
							CASE
								WHEN ogr.statusname::text = 'held : reject'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
								ELSE NULL::numeric
							END, 0::numeric)
						
							
                        WHEN ib.statusname::text = 'held : under evaluation'::text 
						THEN 
						(- COALESCE(eval.total_held, 0::numeric)) 
						- COALESCE(eval.total_released, 0::numeric) 
						+ COALESCE(
	                        CASE
	                            WHEN tf.statusname::text = 'held : under evaluation'::text THEN tf.transferred_from_qty
	                            ELSE NULL::numeric
	                        END, 0::numeric) 
							
						+ COALESCE(
	                        CASE
	                            WHEN tt.statusname::text = 'held : under evaluation'::text THEN tt.transferred_to_qty
	                            ELSE NULL::numeric
	                        END, 0::numeric) 
							
						+ COALESCE(
	                        CASE
	                            WHEN pf.statusname::text = 'held : under evaluation'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
	                            ELSE NULL::numeric
	                        END, 0::numeric)

						+ COALESCE(
							CASE
								WHEN ogr.statusname::text = 'held : under evaluation'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
								ELSE NULL::numeric
							END, 0::numeric)
							
							
                        WHEN ib.statusname::text = 'held : contaminated'::text 
						THEN (- COALESCE(cs.total_held, 0::numeric)) 
						- COALESCE(cs.total_released, 0::numeric) 
						+ COALESCE(
	                        CASE
	                            WHEN tf.statusname::text = 'held : contaminated'::text THEN tf.transferred_from_qty
	                            ELSE NULL::numeric
	                        END, 0::numeric) 
							
						+ COALESCE(
							CASE
								WHEN tt.statusname::text = 'held : contaminated'::text THEN tt.transferred_to_qty
								ELSE NULL::numeric
							END, 0::numeric) 
							
						+ COALESCE(
	                        CASE
	                            WHEN pf.statusname::text = 'held : contaminated'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
	                            ELSE NULL::numeric
	                        END, 0::numeric)

						+ COALESCE(
							CASE
								WHEN ogr.statusname::text = 'held : contaminated'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
								ELSE NULL::numeric
							END, 0::numeric)

                        WHEN ib.statusname::text = 'good'::text 
						THEN (- COALESCE(good.total_held, 0::numeric)) 
						+ COALESCE(good.total_released, 0::numeric) 
						+ COALESCE(rr.total_received, 0::numeric) 
						+ COALESCE(
	                        CASE
	                            WHEN pf.statusname::text = 'good'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
	                            ELSE NULL::numeric
	                        END, 0::numeric) 
							
						+ COALESCE(
							CASE
								WHEN tf.statusname::text = 'good'::text THEN tf.transferred_from_qty
								ELSE NULL::numeric
							END, 0::numeric) 
							
						+ COALESCE(
	                        CASE
	                            WHEN tt.statusname::text = 'good'::text THEN tt.transferred_to_qty
	                            ELSE NULL::numeric
	                        END, 0::numeric)

						+ COALESCE(
							CASE
								WHEN ogr.statusname::text = 'good'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
								ELSE NULL::numeric
							END, 0::numeric)
							
                        ELSE NULL::numeric
                    END AS new_beginning_balance,
                COALESCE(ib.statusname, ''::character varying) AS status,
                ib.statusid

				
               FROM initialbalance ib
                 LEFT JOIN ogr_adjustments ogr ON ib.warehouseid = ogr.warehouseid AND ib.rawmaterialid = ogr.rawmaterialid AND ib.statusid = ogr.statusid
                 LEFT JOIN pf_adjustments pf ON ib.warehouseid = pf.warehouseid AND ib.rawmaterialid = pf.rawmaterialid AND ib.statusid = pf.statusid
                 LEFT JOIN transferred_from tf ON ib.warehouseid = tf.warehouseid AND ib.rawmaterialid = tf.rawmaterialid AND ib.statusid = tf.statusid
                 LEFT JOIN transferred_to tt ON ib.warehouseid = tt.warehouseid AND ib.rawmaterialid = tt.rawmaterialid AND ib.statusid = tt.statusid
                 LEFT JOIN rr_adjustments rr ON ib.warehouseid = rr.warehouseid AND ib.rawmaterialid = rr.rawmaterialid
                 LEFT JOIN status_adjustments_conta cs ON ib.warehouseid = cs.warehouseid AND ib.rawmaterialid = cs.rawmaterialid
                 LEFT JOIN status_adjustments_eval eval ON ib.warehouseid = eval.warehouseid AND eval.rawmaterialid = cs.rawmaterialid
                 LEFT JOIN status_adjustments_rejec rej ON ib.warehouseid = rej.warehouseid AND ib.rawmaterialid = rej.rawmaterialid
                 LEFT JOIN status_adjustments_good good ON ib.warehouseid = good.warehouseid AND ib.rawmaterialid = good.rawmaterialid
            UNION ALL
             SELECT hs.rawmaterialid,
                hs.rmcode,
                hs.warehouseid,
                hs.warehousename,
                hs.warehousenumber,
                hs.heldquantity AS new_beginning_balance,
                hs.status,
                hs.statusid
               FROM held_status_details hs
      ORDER BY 2, 4, 5, 7 NULLS FIRST
            )
     SELECT computed_statement.rawmaterialid,
        computed_statement.rmcode,
        computed_statement.warehouseid,
        computed_statement.warehousename,
        computed_statement.warehousenumber,
        sum(computed_statement.new_beginning_balance) AS new_beginning_balance,
        COALESCE(computed_statement.status, ''::character varying) AS status,
        computed_statement.statusid
       FROM computed_statement
      GROUP BY computed_statement.rawmaterialid, computed_statement.rmcode, computed_statement.warehouseid, computed_statement.warehousename, computed_statement.warehousenumber, computed_statement.status, computed_statement.statusid
      ORDER BY computed_statement.rmcode;