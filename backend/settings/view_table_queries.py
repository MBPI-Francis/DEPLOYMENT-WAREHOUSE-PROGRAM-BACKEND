
CREATE_BEGGINING_VIEW_QUERY = """
    -- View: public.view_beginning_soh
    -- DROP VIEW public.view_beginning_soh;
    
    CREATE OR REPLACE VIEW public.view_beginning_soh
     AS
     WITH rankedrecords AS (
             SELECT soh.warehouse_id AS warehouseid,
                wh.wh_name AS warehousename,
                wh.wh_number AS warehousenumber,
                soh.rm_code_id AS rawmaterialid,
                rm.rm_code AS rmcode,
                soh.rm_soh AS beginningbalance,
                soh.stock_change_date AS stockchangedate,
                soh.date_computed,
                COALESCE(status.name, ''::character varying) AS statusname,
                soh.status_id AS statusid,
                soh.stock_recalculation_count AS recalculation_count
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
        rankedrecords.statusname,
        rankedrecords.statusid,
        rankedrecords.stockchangedate,
        rankedrecords.date_computed,
		rankedrecords.recalculation_count
       FROM rankedrecords
      WHERE rankedrecords.recalculation_count = (	SELECT 
													MAX(rankedrecords.recalculation_count)
	  												FROM rankedrecords)
      ORDER BY rankedrecords.rmcode, rankedrecords.stockchangedate DESC;
    
    ALTER TABLE public.view_beginning_soh
        OWNER TO postgres;
    """



# VERSION 4 Without Adjustment Form and Added the Computation Logic of the Receiving Form Statuses (good and helds)
CREATE_ENDING_VIEW_QUERY = """

    -- View: public.view_ending_stocks_balance

    -- DROP VIEW public.view_ending_stocks_balance;
    
    CREATE OR REPLACE VIEW public.view_ending_stocks_balance
     AS
     WITH initialbalance AS (
             WITH rankedrecords AS (
                     SELECT soh.warehouse_id AS warehouseid,
                        wh.wh_name AS warehousename,
                        wh.wh_number AS warehousenumber,
                        soh.rm_code_id AS rawmaterialid,
                        rm.rm_code AS rmcode,
                        soh.rm_soh AS beginningbalance,
                        soh.stock_change_date AS stockchangedate,
                        soh.date_computed,
                        COALESCE(status.name, ''::character varying) AS statusname,
                        soh.status_id AS statusid,
                        soh.stock_recalculation_count AS recalculation_count
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
                rankedrecords.statusname,
                rankedrecords.statusid,
                rankedrecords.stockchangedate,
                rankedrecords.date_computed,
                rankedrecords.recalculation_count
               FROM rankedrecords
              WHERE rankedrecords.recalculation_count = (( SELECT max(rankedrecords_1.recalculation_count) AS max
                       FROM rankedrecords rankedrecords_1))
            ), 
    
            -- Outgoing Report
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
              WHERE (ogr.is_cleared IS NULL OR ogr.is_cleared = false) 
                  AND (ogr.is_deleted IS NULL OR ogr.is_deleted = false) 
                  AND ogr.date_computed IS NULL
              GROUP BY ogr.warehouse_id, ogr.rm_code_id, ogr.date_computed, status.name, status.id
            ), 
    
            -- Preparation Form
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
              WHERE (pf.is_cleared IS NULL OR pf.is_cleared = false) 
                  AND (pf.is_deleted IS NULL OR pf.is_deleted = false) 
                  AND pf.date_computed IS NULL
              GROUP BY pf.warehouse_id, pf.rm_code_id, pf.date_computed, status.name, status.id
            ), 
    
            -- Transfer Form (FROM)
            transferred_from AS (
             SELECT tf.from_warehouse_id AS warehouseid,
                tf.rm_code_id AS rawmaterialid,
                - sum(tf.qty_kg) AS transferred_from_qty,
                tf.date_computed AS datecomputed,
                status.id AS statusid,
                status.name AS statusname
               FROM tbl_transfer_forms tf
                 JOIN tbl_warehouses wh_from ON tf.from_warehouse_id = wh_from.id
                 LEFT JOIN tbl_status status ON tf.status_id = status.id
              WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) 
                  AND (tf.is_deleted IS NULL OR tf.is_deleted = false) 
                  AND tf.date_computed IS NULL
              GROUP BY tf.from_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
            ), 
    
            -- Transfer Form (TO)
            transferred_to AS (
             SELECT tf.to_warehouse_id AS warehouseid,
                tf.rm_code_id AS rawmaterialid,
                sum(tf.qty_kg) AS transferred_to_qty,
                tf.date_computed AS datecomputed,
                status.id AS statusid,
                status.name AS statusname
               FROM tbl_transfer_forms tf
                 JOIN tbl_warehouses wh_to ON tf.to_warehouse_id = wh_to.id
                 LEFT JOIN tbl_status status ON tf.status_id = status.id
              WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) 
                  AND (tf.is_deleted IS NULL OR tf.is_deleted = false) 
                  AND tf.date_computed IS NULL
              GROUP BY tf.to_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
            ), 
    
            -- Receiving Report
            rr_adjustments AS (
             SELECT rr.warehouse_id AS warehouseid,
                rr.rm_code_id AS rawmaterialid,
                sum(rr.qty_kg) AS total_received,
                rr.date_computed AS datecomputed,
                status.name AS statusname,
                status.id AS statusid
               FROM tbl_receiving_reports rr
                JOIN tbl_warehouses wh ON rr.warehouse_id = wh.id
                JOIN tbl_status status ON rr.status_id = status.id
              WHERE (rr.is_cleared IS NULL OR rr.is_cleared = false) 
                  AND (rr.is_deleted IS NULL OR rr.is_deleted = false) 
                  AND rr.date_computed IS NULL
              GROUP BY rr.warehouse_id, rr.rm_code_id, rr.date_computed, status.id, status.name
              
            ), 
            
            -- Change Status (Evaluation)
            status_adjustments_eval AS (
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
              WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) 
                AND (hf.is_deleted IS NULL OR hf.is_deleted = false) 
                AND hf.date_computed IS NULL 
                AND (new_status.name::text = 'held : under evaluation'::text OR current_status.name::text = 'held : under evaluation'::text)
              GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
            ), 
            
            -- Change Status (Contaminated)
            status_adjustments_conta AS (
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
              WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) 
                AND (hf.is_deleted IS NULL OR hf.is_deleted = false) 
                AND hf.date_computed IS NULL 
                AND (new_status.name::text = 'held : contaminated'::text OR current_status.name::text = 'held : contaminated'::text)
              GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
            ), 
            
            -- Change Status (Rejected)
            status_adjustments_rejec AS (
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
              WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) 
                AND (hf.is_deleted IS NULL OR hf.is_deleted = false) 
                AND hf.date_computed IS NULL 
                AND (new_status.name::text = 'held : reject'::text OR current_status.name::text = 'held : reject'::text)
              GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
            ), 
            
            -- Change Status (Good)
            status_adjustments_good AS (
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
            ), 
            
            -- Held Status Details
            held_status_details AS (
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
            ), 
            
            -- Main Computation Logic
            computed_statement AS (
             SELECT ib.rawmaterialid,
                ib.rmcode,
                ib.warehouseid,
                ib.warehousename,
                ib.warehousenumber,
                ib.beginningbalance +
                    CASE
                        WHEN ib.statusname::text = 'held : reject'::text THEN (- COALESCE(rej.total_held, 0::numeric)) - COALESCE(rej.total_released, 0::numeric) 
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
    
                        + COALESCE(
                            CASE
                                WHEN rr.statusname::text = 'held : reject'::text THEN + COALESCE(rr.total_received, 0::numeric)
                                ELSE NULL::numeric
                            END, 0::numeric)
    
                        
                        WHEN ib.statusname::text = 'held : under evaluation'::text THEN (- COALESCE(eval.total_held, 0::numeric)) - COALESCE(eval.total_released, 0::numeric) 
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
    
                        + COALESCE(
                            CASE
                                WHEN rr.statusname::text = 'held : under evaluation'::text THEN + COALESCE(rr.total_received, 0::numeric)
                                ELSE NULL::numeric
                            END, 0::numeric)
    
                            
                        WHEN ib.statusname::text = 'held : contaminated'::text THEN (- COALESCE(cs.total_held, 0::numeric)) - COALESCE(cs.total_released, 0::numeric) 
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
    
                        + COALESCE(
                            CASE
                                WHEN rr.statusname::text = 'held : contaminated'::text THEN + COALESCE(rr.total_received, 0::numeric)
                                ELSE NULL::numeric
                            END, 0::numeric)
    
                            
                        WHEN ib.statusname::text = 'good'::text THEN (- COALESCE(good.total_held, 0::numeric)) + COALESCE(good.total_released, 0::numeric) 
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
                            
                        + COALESCE(	
                            CASE
                                WHEN rr.statusname::text = 'good'::text THEN COALESCE(rr.total_received, 0::numeric)
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
                 LEFT JOIN rr_adjustments rr ON ib.warehouseid = rr.warehouseid AND ib.rawmaterialid = rr.rawmaterialid AND ib.statusid = rr.statusid
                 LEFT JOIN status_adjustments_conta cs ON ib.warehouseid = cs.warehouseid AND ib.rawmaterialid = cs.rawmaterialid
                 LEFT JOIN status_adjustments_eval eval ON ib.warehouseid = eval.warehouseid AND ib.rawmaterialid = eval.rawmaterialid
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
     SELECT rawmaterialid,
        rmcode,
        warehouseid,
        warehousename,
        warehousenumber,
        sum(new_beginning_balance) AS new_beginning_balance,
        COALESCE(status, ''::character varying) AS status,
        statusid
       FROM computed_statement
      GROUP BY rawmaterialid, rmcode, warehouseid, warehousename, warehousenumber, status, statusid
      ORDER BY rmcode;
      
    ALTER TABLE public.view_ending_stocks_balance
    OWNER TO postgres;
"""

# VERSION 2 With OLD Ending Balance and Spillage Adjustment Form and IAF - TYPE 2 Computation Logic
CREATE_ADJUSTED_ENDING_VIEW_QUERY = """
    -- View: public.view_adjusted_ending_balance

    -- DROP VIEW public.view_adjusted_ending_balance;

    CREATE OR REPLACE VIEW public.view_adjusted_ending_balance
     AS
     
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



     

    ALTER TABLE public.view_adjusted_ending_balance
        OWNER TO postgres;

"""




# VERSION 1 With OLD Ending Balance and Spillage Adjustment Form
# CREATE_ADJUSTED_ENDING_VIEW_QUERY = """
#     -- View: public.view_adjusted_ending_balance
#
#     -- DROP VIEW public.view_adjusted_ending_balance;
#
#     CREATE OR REPLACE VIEW public.view_adjusted_ending_balance
#      AS
#      WITH ending_balance AS (
#              SELECT view_ending_stocks_balance.rawmaterialid,
#                 view_ending_stocks_balance.rmcode,
#                 view_ending_stocks_balance.warehouseid,
#                 view_ending_stocks_balance.warehousename,
#                 view_ending_stocks_balance.warehousenumber,
#                 view_ending_stocks_balance.new_beginning_balance,
#                 view_ending_stocks_balance.status,
#                 view_ending_stocks_balance.statusid
#                FROM view_ending_stocks_balance
#             ), spillage_adjustment_form AS (
#              SELECT spillage.warehouse_id AS warehouseid,
#                 spillage.rm_code_id AS rawmaterialid,
#                 sum(spillage.qty_kg) AS total_spillage_quantity,
#                 spillage.date_computed AS datecomputed,
#                 status.name AS status,
#                 status.id AS statusid
#                FROM tbl_adjustment_spillage spillage
#                  JOIN tbl_warehouses wh ON spillage.warehouse_id = wh.id
#                  JOIN tbl_status status ON spillage.status_id = status.id
#               WHERE (spillage.is_cleared IS NULL OR spillage.is_cleared = false) AND (spillage.is_deleted IS NULL OR spillage.is_deleted = false) AND spillage.date_computed IS NULL
#               GROUP BY spillage.warehouse_id, spillage.rm_code_id, spillage.date_computed, status.name, status.id
#             ), computed_statement AS (
#              SELECT eb.rawmaterialid,
#                 eb.rmcode,
#                 eb.warehouseid,
#                 eb.warehousename,
#                 eb.warehousenumber,
#                 eb.new_beginning_balance +
#                     CASE
#                         WHEN eb.status::text = 'held : reject'::text THEN - COALESCE(
#                         CASE
#                             WHEN spillage.status::text = 'held : reject'::text THEN spillage.total_spillage_quantity
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         WHEN eb.status::text = 'held : contaminated'::text THEN - COALESCE(
#                         CASE
#                             WHEN spillage.status::text = 'held : contaminated'::text THEN spillage.total_spillage_quantity
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         WHEN eb.status::text = 'held : under evaluation'::text THEN - COALESCE(
#                         CASE
#                             WHEN spillage.status::text = 'held : under evaluation'::text THEN spillage.total_spillage_quantity
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         WHEN eb.status::text = 'good'::text THEN - COALESCE(
#                         CASE
#                             WHEN spillage.status::text = 'good'::text THEN spillage.total_spillage_quantity
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         ELSE NULL::numeric
#                     END AS adjusted_ending_balance,
#                 COALESCE(eb.status, ''::character varying) AS status,
#                 eb.statusid
#                FROM ending_balance eb
#                  LEFT JOIN spillage_adjustment_form spillage ON eb.warehouseid = spillage.warehouseid AND eb.rawmaterialid = spillage.rawmaterialid AND eb.statusid = spillage.statusid
#               ORDER BY eb.rmcode, eb.warehousename, eb.warehousenumber, (COALESCE(eb.status, ''::character varying)) NULLS FIRST
#             )
#      SELECT rawmaterialid,
#         rmcode,
#         warehouseid,
#         warehousename,
#         warehousenumber,
#         sum(adjusted_ending_balance) AS new_beginning_balance,
#         COALESCE(status, ''::character varying) AS status,
#         statusid
#        FROM computed_statement
#       GROUP BY rawmaterialid, rmcode, warehouseid, warehousename, warehousenumber, status, statusid
#       ORDER BY rmcode;
#
#     ALTER TABLE public.view_adjusted_ending_balance
#         OWNER TO postgres;
#
# """


# VERSION 3 With Adjustment Form and Change Status Form Bug
# CREATE_ENDING_VIEW_QUERY = """
#
#     -- View: public.view_ending_stocks_balance
#
#     -- DROP VIEW public.view_ending_stocks_balance;
#
#     CREATE OR REPLACE VIEW public.view_ending_stocks_balance
#      AS
#      WITH initialbalance AS (
#              WITH rankedrecords AS (
#                      SELECT soh.warehouse_id AS warehouseid,
#                         wh.wh_name AS warehousename,
#                         wh.wh_number AS warehousenumber,
#                         soh.rm_code_id AS rawmaterialid,
#                         rm.rm_code AS rmcode,
#                         soh.rm_soh AS beginningbalance,
#                         soh.stock_change_date AS stockchangedate,
#                         soh.date_computed,
#                         COALESCE(status.name, ''::character varying) AS statusname,
#                         soh.status_id AS statusid,
#                         soh.stock_recalculation_count AS recalculation_count
#                        FROM tbl_stock_on_hand soh
#                          JOIN tbl_raw_materials rm ON soh.rm_code_id = rm.id
#                          JOIN tbl_warehouses wh ON soh.warehouse_id = wh.id
#                          LEFT JOIN tbl_status status ON soh.status_id = status.id
#                     )
#              SELECT rankedrecords.warehouseid,
#                 rankedrecords.warehousename,
#                 rankedrecords.warehousenumber,
#                 rankedrecords.rawmaterialid,
#                 rankedrecords.rmcode,
#                 rankedrecords.beginningbalance,
#                 rankedrecords.statusname,
#                 rankedrecords.statusid,
#                 rankedrecords.stockchangedate,
#                 rankedrecords.date_computed,
#                 rankedrecords.recalculation_count
#                FROM rankedrecords
#               WHERE rankedrecords.recalculation_count = (( SELECT max(rankedrecords_1.recalculation_count) AS max
#                        FROM rankedrecords rankedrecords_1))
#             ), ogr_adjustments AS (
#              SELECT ogr.warehouse_id AS warehouseid,
#                 ogr.rm_code_id AS rawmaterialid,
#                 sum(ogr.qty_kg) AS total_ogr_quantity,
#                 ogr.date_computed AS datecomputed,
#                 status.name AS statusname,
#                 status.id AS statusid
#                FROM tbl_outgoing_reports ogr
#                  JOIN tbl_warehouses wh ON ogr.warehouse_id = wh.id
#                  JOIN tbl_status status ON ogr.status_id = status.id
#               WHERE (ogr.is_cleared IS NULL OR ogr.is_cleared = false) AND (ogr.is_deleted IS NULL OR ogr.is_deleted = false) AND ogr.date_computed IS NULL
#               GROUP BY ogr.warehouse_id, ogr.rm_code_id, ogr.date_computed, status.name, status.id
#             ), af_adjustments AS (
#              SELECT af.warehouse_id AS warehouseid,
#                 af.rm_code_id AS rawmaterialid,
#                 sum(af.qty_kg) AS total_af_quantity,
#                 af.date_computed AS datecomputed,
#                 status.name AS statusname,
#                 status.id AS statusid
#                FROM tbl_adjustment_form af
#                  JOIN tbl_warehouses wh ON af.warehouse_id = wh.id
#                  JOIN tbl_status status ON af.status_id = status.id
#               WHERE (af.is_cleared IS NULL OR af.is_cleared = false) AND (af.is_deleted IS NULL OR af.is_deleted = false) AND af.date_computed IS NULL
#               GROUP BY af.warehouse_id, af.rm_code_id, af.date_computed, status.name, status.id
#             ), pf_adjustments AS (
#              SELECT pf.warehouse_id AS warehouseid,
#                 pf.rm_code_id AS rawmaterialid,
#                 sum(pf.qty_prepared) AS total_prepared,
#                 sum(pf.qty_return) AS total_returned,
#                 pf.date_computed AS datecomputed,
#                 status.name AS statusname,
#                 status.id AS statusid
#                FROM tbl_preparation_forms pf
#                  JOIN tbl_warehouses wh ON pf.warehouse_id = wh.id
#                  JOIN tbl_status status ON pf.status_id = status.id
#               WHERE (pf.is_cleared IS NULL OR pf.is_cleared = false) AND (pf.is_deleted IS NULL OR pf.is_deleted = false) AND pf.date_computed IS NULL
#               GROUP BY pf.warehouse_id, pf.rm_code_id, pf.date_computed, status.name, status.id
#             ), transferred_from AS (
#              SELECT tf.from_warehouse_id AS warehouseid,
#                 tf.rm_code_id AS rawmaterialid,
#                 - sum(tf.qty_kg) AS transferred_from_qty,
#                 tf.date_computed AS datecomputed,
#                 status.id AS statusid,
#                 status.name AS statusname
#                FROM tbl_transfer_forms tf
#                  JOIN tbl_warehouses wh_from ON tf.from_warehouse_id = wh_from.id
#                  LEFT JOIN tbl_status status ON tf.status_id = status.id
#               WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) AND (tf.is_deleted IS NULL OR tf.is_deleted = false) AND tf.date_computed IS NULL
#               GROUP BY tf.from_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
#             ), transferred_to AS (
#              SELECT tf.to_warehouse_id AS warehouseid,
#                 tf.rm_code_id AS rawmaterialid,
#                 sum(tf.qty_kg) AS transferred_to_qty,
#                 tf.date_computed AS datecomputed,
#                 status.id AS statusid,
#                 status.name AS statusname
#                FROM tbl_transfer_forms tf
#                  JOIN tbl_warehouses wh_to ON tf.to_warehouse_id = wh_to.id
#                  LEFT JOIN tbl_status status ON tf.status_id = status.id
#               WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) AND (tf.is_deleted IS NULL OR tf.is_deleted = false) AND tf.date_computed IS NULL
#               GROUP BY tf.to_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
#             ), rr_adjustments AS (
#              SELECT rr.warehouse_id AS warehouseid,
#                 rr.rm_code_id AS rawmaterialid,
#                 sum(rr.qty_kg) AS total_received,
#                 rr.date_computed AS datecomputed
#                FROM tbl_receiving_reports rr
#                  JOIN tbl_warehouses wh ON rr.warehouse_id = wh.id
#               WHERE (rr.is_cleared IS NULL OR rr.is_cleared = false) AND (rr.is_deleted IS NULL OR rr.is_deleted = false) AND rr.date_computed IS NULL
#               GROUP BY rr.warehouse_id, rr.rm_code_id, rr.date_computed
#             ), status_adjustments_eval AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held : contaminated'::text THEN hf.qty_kg
#                         WHEN new_status.name::text ~~ 'held : reject'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : under evaluation'::text OR current_status.name::text = 'held : under evaluation'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), status_adjustments_conta AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held : under evaluation'::text THEN hf.qty_kg
#                         WHEN new_status.name::text ~~ 'held : reject'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : contaminated'::text OR current_status.name::text = 'held : contaminated'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), status_adjustments_rejec AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held : under evaluation'::text THEN hf.qty_kg
#                         WHEN new_status.name::text ~~ 'held : contaminated'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : reject'::text OR current_status.name::text = 'held : reject'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), status_adjustments_good AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'good'::text OR current_status.name::text = 'good'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), held_status_details AS (
#              SELECT hf.rm_code_id AS rawmaterialid,
#                 wh.wh_name AS warehousename,
#                 wh.id AS warehouseid,
#                 wh.wh_number AS warehousenumber,
#                 rm.rm_code AS rmcode,
#                 sum(hf.qty_kg) AS heldquantity,
#                 new_status.name AS status,
#                 hf.date_computed,
#                 hf.new_status_id AS statusid
#                FROM tbl_held_forms hf
#                  JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE new_status.name::text ~~ 'held%'::text AND (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL
#               GROUP BY hf.rm_code_id, wh.wh_name, wh.wh_number, rm.rm_code, new_status.name, hf.date_computed, wh.id, hf.new_status_id
#             ), computed_statement AS (
#              SELECT ib.rawmaterialid,
#                 ib.rmcode,
#                 ib.warehouseid,
#                 ib.warehousename,
#                 ib.warehousenumber,
#                 ib.beginningbalance +
#                     CASE
#                         WHEN ib.statusname::text = 'held : reject'::text THEN (- COALESCE(rej.total_held, 0::numeric)) - COALESCE(rej.total_released, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tf.statusname::text = 'held : reject'::text THEN tf.transferred_from_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tt.statusname::text = 'held : reject'::text THEN tt.transferred_to_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN pf.statusname::text = 'held : reject'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN ogr.statusname::text = 'held : reject'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN af.statusname::text = 'held : reject'::text THEN COALESCE(af.total_af_quantity, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         WHEN ib.statusname::text = 'held : under evaluation'::text THEN (- COALESCE(eval.total_held, 0::numeric)) - COALESCE(eval.total_released, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tf.statusname::text = 'held : under evaluation'::text THEN tf.transferred_from_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tt.statusname::text = 'held : under evaluation'::text THEN tt.transferred_to_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN pf.statusname::text = 'held : under evaluation'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN ogr.statusname::text = 'held : under evaluation'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN af.statusname::text = 'held : under evaluation'::text THEN COALESCE(af.total_af_quantity, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         WHEN ib.statusname::text = 'held : contaminated'::text THEN (- COALESCE(cs.total_held, 0::numeric)) - COALESCE(cs.total_released, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tf.statusname::text = 'held : contaminated'::text THEN tf.transferred_from_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tt.statusname::text = 'held : contaminated'::text THEN tt.transferred_to_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN pf.statusname::text = 'held : contaminated'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN ogr.statusname::text = 'held : contaminated'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN af.statusname::text = 'held : contaminated'::text THEN COALESCE(af.total_af_quantity, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         WHEN ib.statusname::text = 'good'::text THEN (- COALESCE(good.total_held, 0::numeric)) + COALESCE(good.total_released, 0::numeric) + COALESCE(rr.total_received, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN pf.statusname::text = 'good'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tf.statusname::text = 'good'::text THEN tf.transferred_from_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tt.statusname::text = 'good'::text THEN tt.transferred_to_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN ogr.statusname::text = 'good'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN af.statusname::text = 'good'::text THEN COALESCE(af.total_af_quantity, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         ELSE NULL::numeric
#                     END AS new_beginning_balance,
#                 COALESCE(ib.statusname, ''::character varying) AS status,
#                 ib.statusid
#                FROM initialbalance ib
#                  LEFT JOIN ogr_adjustments ogr ON ib.warehouseid = ogr.warehouseid AND ib.rawmaterialid = ogr.rawmaterialid AND ib.statusid = ogr.statusid
#                  LEFT JOIN af_adjustments af ON ib.warehouseid = af.warehouseid AND ib.rawmaterialid = af.rawmaterialid AND ib.statusid = af.statusid
#                  LEFT JOIN pf_adjustments pf ON ib.warehouseid = pf.warehouseid AND ib.rawmaterialid = pf.rawmaterialid AND ib.statusid = pf.statusid
#                  LEFT JOIN transferred_from tf ON ib.warehouseid = tf.warehouseid AND ib.rawmaterialid = tf.rawmaterialid AND ib.statusid = tf.statusid
#                  LEFT JOIN transferred_to tt ON ib.warehouseid = tt.warehouseid AND ib.rawmaterialid = tt.rawmaterialid AND ib.statusid = tt.statusid
#                  LEFT JOIN rr_adjustments rr ON ib.warehouseid = rr.warehouseid AND ib.rawmaterialid = rr.rawmaterialid
#                  LEFT JOIN status_adjustments_conta cs ON ib.warehouseid = cs.warehouseid AND ib.rawmaterialid = cs.rawmaterialid
#                  LEFT JOIN status_adjustments_eval eval ON ib.warehouseid = eval.warehouseid AND ib.rawmaterialid = eval.rawmaterialid
#                  LEFT JOIN status_adjustments_rejec rej ON ib.warehouseid = rej.warehouseid AND ib.rawmaterialid = rej.rawmaterialid
#                  LEFT JOIN status_adjustments_good good ON ib.warehouseid = good.warehouseid AND ib.rawmaterialid = good.rawmaterialid
#             UNION ALL
#              SELECT hs.rawmaterialid,
#                 hs.rmcode,
#                 hs.warehouseid,
#                 hs.warehousename,
#                 hs.warehousenumber,
#                 hs.heldquantity AS new_beginning_balance,
#                 hs.status,
#                 hs.statusid
#                FROM held_status_details hs
#       ORDER BY 2, 4, 5, 7 NULLS FIRST
#             )
#      SELECT rawmaterialid,
#         rmcode,
#         warehouseid,
#         warehousename,
#         warehousenumber,
#         sum(new_beginning_balance) AS new_beginning_balance,
#         COALESCE(status, ''::character varying) AS status,
#         statusid
#        FROM computed_statement
#       GROUP BY rawmaterialid, rmcode, warehouseid, warehousename, warehousenumber, status, statusid
#       ORDER BY rmcode;
#
#     ALTER TABLE public.view_ending_stocks_balance
#         OWNER TO postgres;
#
#
#
# """

# VERSION 2 Without Adjustment Form
# CREATE_ENDING_VIEW_QUERY = """
#     -- View: public.view_ending_stocks_balance
#
#     -- DROP VIEW public.view_ending_stocks_balance;
#
#     CREATE OR REPLACE VIEW public.view_ending_stocks_balance
#      AS
#          WITH initialbalance AS (
#             WITH rankedrecords AS (
#                 SELECT soh.warehouse_id AS warehouseid,
#                     wh.wh_name AS warehousename,
#                     wh.wh_number AS warehousenumber,
#                     soh.rm_code_id AS rawmaterialid,
#                     rm.rm_code AS rmcode,
#                     soh.rm_soh AS beginningbalance,
#                     soh.stock_change_date AS stockchangedate,
#                     soh.date_computed,
#                     COALESCE(status.name, ''::character varying) AS statusname,
#                     soh.status_id AS statusid,
#                     soh.stock_recalculation_count AS recalculation_count
#                    FROM tbl_stock_on_hand soh
#                      JOIN tbl_raw_materials rm ON soh.rm_code_id = rm.id
#                      JOIN tbl_warehouses wh ON soh.warehouse_id = wh.id
#                      LEFT JOIN tbl_status status ON soh.status_id = status.id
#                 )
#             SELECT rankedrecords.warehouseid,
#                 rankedrecords.warehousename,
#                 rankedrecords.warehousenumber,
#                 rankedrecords.rawmaterialid,
#                 rankedrecords.rmcode,
#                 rankedrecords.beginningbalance,
#                 rankedrecords.statusname,
#                 rankedrecords.statusid,
#                 rankedrecords.stockchangedate,
#                 rankedrecords.date_computed,
#                 rankedrecords.recalculation_count
#             FROM rankedrecords
#             WHERE rankedrecords.recalculation_count = (	SELECT
#                                                         MAX(rankedrecords.recalculation_count)
#                                                         FROM rankedrecords)
#             ),
#
# 			ogr_adjustments AS (
#              SELECT ogr.warehouse_id AS warehouseid,
#                 ogr.rm_code_id AS rawmaterialid,
#                 sum(ogr.qty_kg) AS total_ogr_quantity,
#                 ogr.date_computed AS datecomputed,
# 				status.name AS statusname,
#                 status.id AS statusid
#                FROM tbl_outgoing_reports ogr
#                  JOIN tbl_warehouses wh ON ogr.warehouse_id = wh.id
# 				 JOIN tbl_status status ON ogr.status_id = status.id
#               WHERE (ogr.is_cleared IS NULL OR ogr.is_cleared = false) AND (ogr.is_deleted IS NULL OR ogr.is_deleted = false) AND ogr.date_computed IS NULL
#               GROUP BY ogr.warehouse_id, ogr.rm_code_id, ogr.date_computed, status.name, status.id
#             ),
#
# 			pf_adjustments AS (
#              SELECT pf.warehouse_id AS warehouseid,
#                 pf.rm_code_id AS rawmaterialid,
#                 sum(pf.qty_prepared) AS total_prepared,
#                 sum(pf.qty_return) AS total_returned,
#                 pf.date_computed AS datecomputed,
#                 status.name AS statusname,
#                 status.id AS statusid
#                FROM tbl_preparation_forms pf
#                  JOIN tbl_warehouses wh ON pf.warehouse_id = wh.id
#                  JOIN tbl_status status ON pf.status_id = status.id
#               WHERE (pf.is_cleared IS NULL OR pf.is_cleared = false) AND (pf.is_deleted IS NULL OR pf.is_deleted = false) AND pf.date_computed IS NULL
#               GROUP BY pf.warehouse_id, pf.rm_code_id, pf.date_computed, status.name, status.id
#             ), transferred_from AS (
#              SELECT tf.from_warehouse_id AS warehouseid,
#                 tf.rm_code_id AS rawmaterialid,
#                 - sum(tf.qty_kg) AS transferred_from_qty,
#                 tf.date_computed AS datecomputed,
#                 status.id AS statusid,
#                 status.name AS statusname
#                FROM tbl_transfer_forms tf
#                  JOIN tbl_warehouses wh_from ON tf.from_warehouse_id = wh_from.id
#                  LEFT JOIN tbl_status status ON tf.status_id = status.id
#               WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) AND (tf.is_deleted IS NULL OR tf.is_deleted = false) AND tf.date_computed IS NULL
#               GROUP BY tf.from_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
#             ), transferred_to AS (
#              SELECT tf.to_warehouse_id AS warehouseid,
#                 tf.rm_code_id AS rawmaterialid,
#                 sum(tf.qty_kg) AS transferred_to_qty,
#                 tf.date_computed AS datecomputed,
#                 status.id AS statusid,
#                 status.name AS statusname
#                FROM tbl_transfer_forms tf
#                  JOIN tbl_warehouses wh_to ON tf.to_warehouse_id = wh_to.id
#                  LEFT JOIN tbl_status status ON tf.status_id = status.id
#               WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) AND (tf.is_deleted IS NULL OR tf.is_deleted = false) AND tf.date_computed IS NULL
#               GROUP BY tf.to_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
#             ), rr_adjustments AS (
#              SELECT rr.warehouse_id AS warehouseid,
#                 rr.rm_code_id AS rawmaterialid,
#                 sum(rr.qty_kg) AS total_received,
#                 rr.date_computed AS datecomputed
#                FROM tbl_receiving_reports rr
#                  JOIN tbl_warehouses wh ON rr.warehouse_id = wh.id
#               WHERE (rr.is_cleared IS NULL OR rr.is_cleared = false) AND (rr.is_deleted IS NULL OR rr.is_deleted = false) AND rr.date_computed IS NULL
#               GROUP BY rr.warehouse_id, rr.rm_code_id, rr.date_computed
#             ), status_adjustments_eval AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held : contaminated'::text THEN hf.qty_kg
#                         WHEN new_status.name::text ~~ 'held : reject'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : under evaluation'::text OR current_status.name::text = 'held : under evaluation'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), status_adjustments_conta AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held : under evaluation'::text THEN hf.qty_kg
#                         WHEN new_status.name::text ~~ 'held : reject'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : contaminated'::text OR current_status.name::text = 'held : contaminated'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), status_adjustments_rejec AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held : under evaluation'::text THEN hf.qty_kg
#                         WHEN new_status.name::text ~~ 'held : contaminated'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : reject'::text OR current_status.name::text = 'held : reject'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), status_adjustments_good AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'good'::text OR current_status.name::text = 'good'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), held_status_details AS (
#              SELECT hf.rm_code_id AS rawmaterialid,
#                 wh.wh_name AS warehousename,
#                 wh.id AS warehouseid,
#                 wh.wh_number AS warehousenumber,
#                 rm.rm_code AS rmcode,
#                 sum(hf.qty_kg) AS heldquantity,
#                 new_status.name AS status,
#                 hf.date_computed,
#                 hf.new_status_id AS statusid
#                FROM tbl_held_forms hf
#                  JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE new_status.name::text ~~ 'held%'::text AND (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL
#               GROUP BY hf.rm_code_id, wh.wh_name, wh.wh_number, rm.rm_code, new_status.name, hf.date_computed, wh.id, hf.new_status_id
#             ), computed_statement AS (
#              SELECT ib.rawmaterialid,
#                 ib.rmcode,
#                 ib.warehouseid,
#                 ib.warehousename,
#                 ib.warehousenumber,
#                 ib.beginningbalance +
#                     CASE
#                         WHEN ib.statusname::text = 'held : reject'::text
# 						THEN
# 						(- COALESCE(rej.total_held, 0::numeric))
# 						- COALESCE(rej.total_released, 0::numeric)
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN tf.statusname::text = 'held : reject'::text THEN tf.transferred_from_qty
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN tt.statusname::text = 'held : reject'::text THEN tt.transferred_to_qty
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN pf.statusname::text = 'held : reject'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 							CASE
# 								WHEN ogr.statusname::text = 'held : reject'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
# 								ELSE NULL::numeric
# 							END, 0::numeric)
#
#
#                         WHEN ib.statusname::text = 'held : under evaluation'::text
# 						THEN
# 						(- COALESCE(eval.total_held, 0::numeric)) - COALESCE(eval.total_released, 0::numeric)
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN tf.statusname::text = 'held : under evaluation'::text THEN tf.transferred_from_qty
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN tt.statusname::text = 'held : under evaluation'::text THEN tt.transferred_to_qty
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN pf.statusname::text = 'held : under evaluation'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 							CASE
# 								WHEN ogr.statusname::text = 'held : under evaluation'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
# 								ELSE NULL::numeric
# 							END, 0::numeric)
#
#
#                         WHEN ib.statusname::text = 'held : contaminated'::text
# 						THEN (- COALESCE(cs.total_held, 0::numeric))
# 						- COALESCE(cs.total_released, 0::numeric)
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN tf.statusname::text = 'held : contaminated'::text THEN tf.transferred_from_qty
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 							CASE
# 								WHEN tt.statusname::text = 'held : contaminated'::text THEN tt.transferred_to_qty
# 								ELSE NULL::numeric
# 							END, 0::numeric)
#
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN pf.statusname::text = 'held : contaminated'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 							CASE
# 								WHEN ogr.statusname::text = 'held : contaminated'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
# 								ELSE NULL::numeric
# 							END, 0::numeric)
#
#                         WHEN ib.statusname::text = 'good'::text
# 						THEN (- COALESCE(good.total_held, 0::numeric))
# 						+ COALESCE(good.total_released, 0::numeric)
# 						+ COALESCE(rr.total_received, 0::numeric)
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN pf.statusname::text = 'good'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 							CASE
# 								WHEN tf.statusname::text = 'good'::text THEN tf.transferred_from_qty
# 								ELSE NULL::numeric
# 							END, 0::numeric)
#
# 						+ COALESCE(
# 	                        CASE
# 	                            WHEN tt.statusname::text = 'good'::text THEN tt.transferred_to_qty
# 	                            ELSE NULL::numeric
# 	                        END, 0::numeric)
#
# 						+ COALESCE(
# 							CASE
# 								WHEN ogr.statusname::text = 'good'::text THEN - COALESCE(ogr.total_ogr_quantity, 0::numeric)
# 								ELSE NULL::numeric
# 							END, 0::numeric)
#
#                         ELSE NULL::numeric
#                     END AS new_beginning_balance,
#                 COALESCE(ib.statusname, ''::character varying) AS status,
#                 ib.statusid
#
#
#                FROM initialbalance ib
#                  LEFT JOIN ogr_adjustments ogr ON ib.warehouseid = ogr.warehouseid AND ib.rawmaterialid = ogr.rawmaterialid AND ib.statusid = ogr.statusid
#                  LEFT JOIN pf_adjustments pf ON ib.warehouseid = pf.warehouseid AND ib.rawmaterialid = pf.rawmaterialid AND ib.statusid = pf.statusid
#                  LEFT JOIN transferred_from tf ON ib.warehouseid = tf.warehouseid AND ib.rawmaterialid = tf.rawmaterialid AND ib.statusid = tf.statusid
#                  LEFT JOIN transferred_to tt ON ib.warehouseid = tt.warehouseid AND ib.rawmaterialid = tt.rawmaterialid AND ib.statusid = tt.statusid
#                  LEFT JOIN rr_adjustments rr ON ib.warehouseid = rr.warehouseid AND ib.rawmaterialid = rr.rawmaterialid
#                  LEFT JOIN status_adjustments_conta cs ON ib.warehouseid = cs.warehouseid AND ib.rawmaterialid = cs.rawmaterialid
#                  LEFT JOIN status_adjustments_eval eval ON ib.warehouseid = eval.warehouseid AND ib.rawmaterialid = eval.rawmaterialid
#                  LEFT JOIN status_adjustments_rejec rej ON ib.warehouseid = rej.warehouseid AND ib.rawmaterialid = rej.rawmaterialid
#                  LEFT JOIN status_adjustments_good good ON ib.warehouseid = good.warehouseid AND ib.rawmaterialid = good.rawmaterialid
#             UNION ALL
#              SELECT hs.rawmaterialid,
#                 hs.rmcode,
#                 hs.warehouseid,
#                 hs.warehousename,
#                 hs.warehousenumber,
#                 hs.heldquantity AS new_beginning_balance,
#                 hs.status,
#                 hs.statusid
#                FROM held_status_details hs
#       ORDER BY 2, 4, 5, 7 NULLS FIRST
#             )
#      SELECT computed_statement.rawmaterialid,
#         computed_statement.rmcode,
#         computed_statement.warehouseid,
#         computed_statement.warehousename,
#         computed_statement.warehousenumber,
#         sum(computed_statement.new_beginning_balance) AS new_beginning_balance,
#         COALESCE(computed_statement.status, ''::character varying) AS status,
#         computed_statement.statusid
#        FROM computed_statement
#       GROUP BY computed_statement.rawmaterialid, computed_statement.rmcode, computed_statement.warehouseid, computed_statement.warehousename, computed_statement.warehousenumber, computed_statement.status, computed_statement.statusid
#       ORDER BY computed_statement.rmcode;
#
#     ALTER TABLE public.view_ending_stocks_balance
#         OWNER TO postgres;
#
#     """
#


# CREATE_ENDING_VIEW_QUERY_OLD = """
#     -- View: public.view_ending_stocks_balance
#
#     -- DROP VIEW public.view_ending_stocks_balance;
#
#     CREATE OR REPLACE VIEW public.view_ending_stocks_balance
#      AS
#      WITH initialbalance AS (
#              WITH rankedrecords AS (
#                      SELECT soh.warehouse_id AS warehouseid,
#                         wh.wh_name AS warehousename,
#                         wh.wh_number AS warehousenumber,
#                         soh.rm_code_id AS rawmaterialid,
#                         rm.rm_code AS rmcode,
#                         soh.rm_soh AS beginningbalance,
#                         soh.stock_change_date AS stockchangedate,
#                         status.name AS statusname,
#                         soh.status_id AS statusid,
#                         row_number() OVER (PARTITION BY soh.warehouse_id, soh.rm_code_id, soh.status_id ORDER BY soh.stock_change_date DESC) AS row_num
#                        FROM tbl_stock_on_hand soh
#                          JOIN tbl_raw_materials rm ON soh.rm_code_id = rm.id
#                          JOIN tbl_warehouses wh ON soh.warehouse_id = wh.id
#                          LEFT JOIN tbl_status status ON soh.status_id = status.id
#                     )
#              SELECT rankedrecords.warehouseid,
#                 rankedrecords.warehousename,
#                 rankedrecords.warehousenumber,
#                 rankedrecords.rawmaterialid,
#                 rankedrecords.rmcode,
#                 rankedrecords.beginningbalance,
#                 rankedrecords.stockchangedate,
#                 rankedrecords.statusname,
#                 rankedrecords.statusid
#                FROM rankedrecords
#               WHERE rankedrecords.row_num = 1
#             ), ogr_adjustments AS (
#              SELECT ogr.warehouse_id AS warehouseid,
#                 ogr.rm_code_id AS rawmaterialid,
#                 sum(ogr.qty_kg) AS total_ogr_quantity,
#                 ogr.date_computed AS datecomputed
#                FROM tbl_outgoing_reports ogr
#                  JOIN tbl_warehouses wh ON ogr.warehouse_id = wh.id
#               WHERE (ogr.is_cleared IS NULL OR ogr.is_cleared = false) AND (ogr.is_deleted IS NULL OR ogr.is_deleted = false) AND ogr.date_computed IS NULL
#               GROUP BY ogr.warehouse_id, ogr.rm_code_id, ogr.date_computed
#             ), pf_adjustments AS (
#              SELECT pf.warehouse_id AS warehouseid,
#                 pf.rm_code_id AS rawmaterialid,
#                 sum(pf.qty_prepared) AS total_prepared,
#                 sum(pf.qty_return) AS total_returned,
#                 pf.date_computed AS datecomputed,
#                 status.name AS statusname,
#                 status.id AS statusid
#                FROM tbl_preparation_forms pf
#                  JOIN tbl_warehouses wh ON pf.warehouse_id = wh.id
#                  JOIN tbl_status status ON pf.status_id = status.id
#               WHERE (pf.is_cleared IS NULL OR pf.is_cleared = false) AND (pf.is_deleted IS NULL OR pf.is_deleted = false) AND pf.date_computed IS NULL
#               GROUP BY pf.warehouse_id, pf.rm_code_id, pf.date_computed, status.name, status.id
#             ), transferred_from AS (
#              SELECT tf.from_warehouse_id AS warehouseid,
#                 tf.rm_code_id AS rawmaterialid,
#                 - sum(tf.qty_kg) AS transferred_from_qty,
#                 tf.date_computed AS datecomputed,
#                 status.id AS statusid,
#                 status.name AS statusname
#                FROM tbl_transfer_forms tf
#                  JOIN tbl_warehouses wh_from ON tf.from_warehouse_id = wh_from.id
#                  LEFT JOIN tbl_status status ON tf.status_id = status.id
#               WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) AND (tf.is_deleted IS NULL OR tf.is_deleted = false) AND tf.date_computed IS NULL
#               GROUP BY tf.from_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
#             ), transferred_to AS (
#              SELECT tf.to_warehouse_id AS warehouseid,
#                 tf.rm_code_id AS rawmaterialid,
#                 sum(tf.qty_kg) AS transferred_to_qty,
#                 tf.date_computed AS datecomputed,
#                 status.id AS statusid,
#                 status.name AS statusname
#                FROM tbl_transfer_forms tf
#                  JOIN tbl_warehouses wh_to ON tf.to_warehouse_id = wh_to.id
#                  LEFT JOIN tbl_status status ON tf.status_id = status.id
#               WHERE (tf.is_cleared IS NULL OR tf.is_cleared = false) AND (tf.is_deleted IS NULL OR tf.is_deleted = false) AND tf.date_computed IS NULL
#               GROUP BY tf.to_warehouse_id, tf.rm_code_id, tf.date_computed, status.id, status.name
#             ), rr_adjustments AS (
#              SELECT rr.warehouse_id AS warehouseid,
#                 rr.rm_code_id AS rawmaterialid,
#                 sum(rr.qty_kg) AS total_received,
#                 rr.date_computed AS datecomputed
#                FROM tbl_receiving_reports rr
#                  JOIN tbl_warehouses wh ON rr.warehouse_id = wh.id
#               WHERE (rr.is_cleared IS NULL OR rr.is_cleared = false) AND (rr.is_deleted IS NULL OR rr.is_deleted = false) AND rr.date_computed IS NULL
#               GROUP BY rr.warehouse_id, rr.rm_code_id, rr.date_computed
#             ), status_adjustments_eval AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held : contaminated'::text THEN hf.qty_kg
#                         WHEN new_status.name::text ~~ 'held : reject'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : under evaluation'::text OR current_status.name::text = 'held : under evaluation'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), status_adjustments_conta AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held : under evaluation'::text THEN hf.qty_kg
#                         WHEN new_status.name::text ~~ 'held : reject'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : contaminated'::text OR current_status.name::text = 'held : contaminated'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), status_adjustments_rejec AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held : under evaluation'::text THEN hf.qty_kg
#                         WHEN new_status.name::text ~~ 'held : contaminated'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'held : reject'::text OR current_status.name::text = 'held : reject'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), status_adjustments_good AS (
#              SELECT hf.warehouse_id AS warehouseid,
#                 hf.rm_code_id AS rawmaterialid,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'held%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_held,
#                 sum(
#                     CASE
#                         WHEN new_status.name::text ~~ 'good%'::text THEN hf.qty_kg
#                         ELSE 0::numeric
#                     END) AS total_released,
#                 hf.date_computed AS datecomputed
#                FROM tbl_held_forms hf
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status current_status ON hf.current_status_id = current_status.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL AND (new_status.name::text = 'good'::text OR current_status.name::text = 'good'::text)
#               GROUP BY hf.warehouse_id, hf.rm_code_id, hf.date_computed
#             ), held_status_details AS (
#              SELECT hf.rm_code_id AS rawmaterialid,
#                 wh.wh_name AS warehousename,
#                 wh.id AS warehouseid,
#                 wh.wh_number AS warehousenumber,
#                 rm.rm_code AS rmcode,
#                 sum(hf.qty_kg) AS heldquantity,
#                 new_status.name AS status,
#                 hf.date_computed,
#                 hf.new_status_id AS statusid
#                FROM tbl_held_forms hf
#                  JOIN tbl_raw_materials rm ON hf.rm_code_id = rm.id
#                  JOIN tbl_warehouses wh ON hf.warehouse_id = wh.id
#                  JOIN tbl_status new_status ON hf.new_status_id = new_status.id
#               WHERE new_status.name::text ~~ 'held%'::text AND (hf.is_cleared IS NULL OR hf.is_cleared = false) AND (hf.is_deleted IS NULL OR hf.is_deleted = false) AND hf.date_computed IS NULL
#               GROUP BY hf.rm_code_id, wh.wh_name, wh.wh_number, rm.rm_code, new_status.name, hf.date_computed, wh.id, hf.new_status_id
#             ), computed_statement AS (
#              SELECT ib.rawmaterialid,
#                 ib.rmcode,
#                 ib.warehouseid,
#                 ib.warehousename,
#                 ib.warehousenumber,
#                 ib.beginningbalance +
#                     CASE
#                         WHEN ib.statusname::text = 'held : reject'::text THEN (- COALESCE(rej.total_held, 0::numeric)) - COALESCE(rej.total_released, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tf.statusname::text = 'held : reject'::text THEN tf.transferred_from_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tt.statusname::text = 'held : reject'::text THEN tt.transferred_to_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN pf.statusname::text = 'held : reject'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         WHEN ib.statusname::text = 'held : under evaluation'::text THEN (- COALESCE(eval.total_held, 0::numeric)) - COALESCE(eval.total_released, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tf.statusname::text = 'held : under evaluation'::text THEN tf.transferred_from_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tt.statusname::text = 'held : under evaluation'::text THEN tt.transferred_to_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN pf.statusname::text = 'held : under evaluation'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         WHEN ib.statusname::text = 'held : contaminated'::text THEN (- COALESCE(cs.total_held, 0::numeric)) - COALESCE(cs.total_released, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tf.statusname::text = 'held : contaminated'::text THEN tf.transferred_from_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tt.statusname::text = 'held : contaminated'::text THEN tt.transferred_to_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN pf.statusname::text = 'held : contaminated'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         WHEN ib.statusname::text = 'good'::text THEN (- COALESCE(good.total_held, 0::numeric)) - COALESCE(ogr.total_ogr_quantity, 0::numeric) + COALESCE(good.total_released, 0::numeric) + COALESCE(rr.total_received, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN pf.statusname::text = 'good'::text THEN COALESCE(pf.total_returned, 0::numeric) - COALESCE(pf.total_prepared, 0::numeric)
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tf.statusname::text = 'good'::text THEN tf.transferred_from_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric) + COALESCE(
#                         CASE
#                             WHEN tt.statusname::text = 'good'::text THEN tt.transferred_to_qty
#                             ELSE NULL::numeric
#                         END, 0::numeric)
#                         ELSE NULL::numeric
#                     END AS new_beginning_balance,
#                 COALESCE(ib.statusname, ''::character varying) AS status,
#                 ib.statusid
#                FROM initialbalance ib
#                  LEFT JOIN ogr_adjustments ogr ON ib.warehouseid = ogr.warehouseid AND ib.rawmaterialid = ogr.rawmaterialid
#                  LEFT JOIN pf_adjustments pf ON ib.warehouseid = pf.warehouseid AND ib.rawmaterialid = pf.rawmaterialid AND ib.statusid = pf.statusid
#                  LEFT JOIN transferred_from tf ON ib.warehouseid = tf.warehouseid AND ib.rawmaterialid = tf.rawmaterialid AND ib.statusid = tf.statusid
#                  LEFT JOIN transferred_to tt ON ib.warehouseid = tt.warehouseid AND ib.rawmaterialid = tt.rawmaterialid AND ib.statusid = tt.statusid
#                  LEFT JOIN rr_adjustments rr ON ib.warehouseid = rr.warehouseid AND ib.rawmaterialid = rr.rawmaterialid
#                  LEFT JOIN status_adjustments_conta cs ON ib.warehouseid = cs.warehouseid AND ib.rawmaterialid = cs.rawmaterialid
#                  LEFT JOIN status_adjustments_eval eval ON ib.warehouseid = eval.warehouseid AND eval.rawmaterialid = cs.rawmaterialid
#                  LEFT JOIN status_adjustments_rejec rej ON ib.warehouseid = rej.warehouseid AND ib.rawmaterialid = rej.rawmaterialid
#                  LEFT JOIN status_adjustments_good good ON ib.warehouseid = good.warehouseid AND ib.rawmaterialid = good.rawmaterialid
#             UNION ALL
#              SELECT hs.rawmaterialid,
#                 hs.rmcode,
#                 hs.warehouseid,
#                 hs.warehousename,
#                 hs.warehousenumber,
#                 hs.heldquantity AS new_beginning_balance,
#                 hs.status,
#                 hs.statusid
#                FROM held_status_details hs
#       ORDER BY 2, 4, 5, 7 NULLS FIRST
#             )
#      SELECT computed_statement.rawmaterialid,
#         computed_statement.rmcode,
#         computed_statement.warehouseid,
#         computed_statement.warehousename,
#         computed_statement.warehousenumber,
#         sum(computed_statement.new_beginning_balance) AS new_beginning_balance,
#         COALESCE(computed_statement.status, ''::character varying) AS status,
#         computed_statement.statusid
#        FROM computed_statement
#       GROUP BY computed_statement.rawmaterialid, computed_statement.rmcode, computed_statement.warehouseid, computed_statement.warehousename, computed_statement.warehousenumber, computed_statement.status, computed_statement.statusid
#       ORDER BY computed_statement.rmcode;
#
#     ALTER TABLE public.view_ending_stocks_balance
#         OWNER TO postgres;
#
#     """
