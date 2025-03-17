        # SQL query for creating the view
        sql_query = f"""
            CREATE OR REPLACE VIEW {view_name} AS
            WITH
            -- Step 1: Initial Beginning Balance
            initialbalance AS (
                WITH rankedrecords AS (
                    SELECT
                        SOH.warehouse_id AS warehouseid,
                        WH.wh_name AS WarehouseName,
                        WH.wh_number AS WarehouseNumber,
                        SOH.rm_code_id AS rawmaterialid,
                        RM.rm_code AS RMCode,
                        SOH.rm_soh AS beginningbalance,
                        SOH.stock_change_date AS stockchangedate,
                        STATUS.name AS StatusName,
                        SOH.status_id AS StatusID,
                        SOH.date_computed,
                        row_number() OVER (PARTITION BY SOH.warehouse_id, SOH.rm_code_id, SOH.status_id ORDER BY SOH.stock_change_date DESC) AS row_num
                    FROM tbl_stock_on_hand AS SOH
                    INNER JOIN tbl_raw_materials AS RM
                        ON SOH.rm_code_id = RM.id
                    INNER JOIN tbl_warehouses AS WH
                        ON SOH.warehouse_id = WH.id

                    LEFT JOIN tbl_status AS STATUS
                        ON SOH.status_id = STATUS.id
                )
                SELECT
                    rankedrecords.warehouseid,
                    rankedrecords.warehousename,
                    rankedrecords.warehousenumber,
                    rankedrecords.rawmaterialid,
                    rankedrecords.rmcode,
                    rankedrecords.beginningbalance,
                    rankedrecords.stockchangedate,
                    rankedrecords.statusname,
                    rankedrecords.statusid,
                    rankedrecords.date_computed
                FROM rankedrecords
                WHERE rankedrecords.row_num = 1
            ),

            -- Step 2: Outgoing Report Adjustments
            OGR_Adjustments AS (
                SELECT
                    ogr.warehouse_id AS WarehouseID,
                    ogr.rm_code_id AS RawMaterialID,
                    SUM(ogr.qty_kg) AS Total_OGR_Quantity,
                    ogr.date_computed AS DateComputed
                FROM
                    tbl_outgoing_reports AS ogr
                INNER JOIN tbl_warehouses AS wh
                    ON ogr.warehouse_id = wh.id
                WHERE
                    ogr.date_computed = '{today}' AND (ogr.is_deleted ISNULL OR ogr.is_deleted = False)
                GROUP BY
                    ogr.warehouse_id, ogr.rm_code_id, ogr.date_computed
            ),

            -- Step 3: Preparation Form Adjustments
            PF_Adjustments AS (
                SELECT
                    pf.warehouse_id AS WarehouseID,
                    pf.rm_code_id AS RawMaterialID,
                    SUM(pf.qty_prepared) AS Total_Prepared,
                    SUM(pf.qty_return) AS Total_Returned,
                    pf.date_computed AS DateComputed
                FROM
                    tbl_preparation_forms as pf
                INNER JOIN tbl_warehouses AS wh
                    ON pf.warehouse_id = wh.id

                WHERE
                    pf.date_computed = '{today}' AND (pf.is_deleted ISNULL OR pf.is_deleted = False)
                GROUP BY
                    pf.warehouse_id, pf.rm_code_id, pf.date_computed
            ),

            -- Step 4: Transfer Form Adjustments
            TF_Adjustments AS (
                SELECT
                    tf.from_warehouse_id AS WarehouseID,
                    tf.rm_code_id AS RawMaterialID,
                    -SUM(tf.qty_kg) AS Total_Transferred_Quantity,
                    tf.date_computed AS DateComputed
                FROM
                    tbl_transfer_forms AS tf
                INNER JOIN tbl_warehouses AS wh_from
                    ON tf.from_warehouse_id = wh_from.id
                WHERE
                    tf.date_computed = '{today}'
                    AND tf.status_id ISNULL
                    AND (tf.is_deleted ISNULL OR tf.is_deleted = False)
                GROUP BY
                    tf.from_warehouse_id, tf.rm_code_id, tf.date_computed
                UNION ALL
                SELECT
                    tf.to_warehouse_id AS WarehouseID,
                    tf.rm_code_id AS RawMaterialID,
                    SUM(tf.qty_kg) AS Total_Transferred_Quantity,
                    tf.date_computed AS DateComputed
                FROM
                    tbl_transfer_forms AS tf

                INNER JOIN tbl_warehouses AS wh_to
                    ON tf.to_warehouse_id = wh_to.id

                WHERE
                    tf.date_computed = '{today}'
                    AND tf.status_id ISNULL
                    AND (tf.is_deleted ISNULL OR tf.is_deleted = False)
                GROUP BY
                    tf.to_warehouse_id, tf.rm_code_id, tf.date_computed
            ),

            -- Step 5: Receiving Report Adjustments
            RR_Adjustments AS (
                SELECT
                    rr.warehouse_id AS WarehouseID,
                    rr.rm_code_id AS RawMaterialID,
                    SUM(rr.qty_kg) AS Total_Received,
                    rr.date_computed AS DateComputed
                FROM
                    tbl_receiving_reports  AS rr

                INNER JOIN tbl_warehouses AS wh
                    ON rr.warehouse_id = wh.id

                WHERE
                    rr.date_computed = '{today}'
                    AND (rr.is_deleted ISNULL OR rr.is_deleted = False)
                GROUP BY
                    rr.warehouse_id, rr.rm_code_id, rr.date_computed
            ),


            -- Step 6: Change of Status Form Adjustments
            Status_Adjustments AS (
                SELECT
                        hf.warehouse_id AS WarehouseID,
                        hf.rm_code_id AS RawMaterialID,
                    SUM(
                        CASE
                            WHEN new_status.name LIKE 'held%'
                                THEN qty_kg
                            ELSE 0
                        END
                        )
                        AS Total_Held,
                    SUM(CASE WHEN new_status.name LIKE 'good%' THEN qty_kg ELSE 0 END) AS Total_Released,
                    hf.date_computed AS DateComputed
                FROM
                    tbl_held_forms as hf

                INNER JOIN tbl_warehouses AS wh
                    ON hf.warehouse_id = wh.id

                INNER JOIN tbl_status AS current_status
                    ON hf.current_status_id = current_status.id

                INNER JOIN tbl_status AS new_status
                    ON hf.new_status_id = new_status.id

                LEFT JOIN InitialBalance AS ib
                    ON hf.new_status_id = ib.statusid

                WHERE
                    hf.date_computed = '{today}'
                    AND (hf.is_deleted ISNULL OR hf.is_deleted = False)
                GROUP BY
                    hf.warehouse_id, hf.rm_code_id, hf.date_computed
            ),

            -- Step 7: Held Status Details Adjustments
            Held_Status_Details AS (
                SELECT
                    hf.rm_code_id AS RawMaterialID,
                    wh.wh_name AS WarehouseName,
                    wh.id AS WarehouseID,
                    wh.wh_number AS WarehouseNumber,
                    rm.rm_code AS RMCode,
                    SUM(qty_kg) AS HeldQuantity,
                    new_status.name AS Status,
                    hf.date_computed,
                    hf.new_status_id AS StatusID
                FROM
                    tbl_held_forms AS hf
                INNER JOIN tbl_raw_materials AS rm
                    ON hf.rm_code_id = rm.id
                INNER JOIN tbl_warehouses AS wh
                    ON hf.warehouse_id = wh.id
                INNER JOIN tbl_status AS new_status
                    ON hf.new_status_id = new_status.id

                WHERE
                    new_status.name LIKE 'held%'
                    AND hf.date_computed = '{today}'
                    AND (hf.is_deleted ISNULL OR hf.is_deleted = False)
                GROUP BY
                    hf.rm_code_id, wh.wh_name, wh.wh_number, rm.rm_code, new_status.name, hf.date_computed, wh.id, hf.new_status_id
            )


            -- Final Query
            SELECT
                ib.rawmaterialid,
                ib.rmcode,
                ib.warehouseid,
                ib.warehousename,
                ib.warehousenumber,
                ib.BeginningBalance
                + COALESCE(rr.Total_Received, 0)
                + COALESCE(pf.Total_Returned, 0)
                - COALESCE(ogr.Total_OGR_Quantity, 0)
                - COALESCE(pf.Total_Prepared, 0)
                + COALESCE(tf.Total_Transferred_Quantity, 0)
                - COALESCE(cs.Total_Held, 0)
                + COALESCE(cs.Total_Released, 0) AS New_Beginning_Balance,
                '' AS Status,
                NULL AS StatusID
            FROM
                initialbalance ib
            LEFT JOIN
                OGR_Adjustments ogr
                ON ib.WarehouseID = ogr.WarehouseID AND ib.RawMaterialID = ogr.RawMaterialID
            LEFT JOIN
                PF_Adjustments pf
                ON ib.WarehouseID = pf.WarehouseID AND ib.RawMaterialID = pf.RawMaterialID
            LEFT JOIN
                TF_Adjustments tf
                ON ib.WarehouseID = tf.WarehouseID AND ib.RawMaterialID = tf.RawMaterialID
            LEFT JOIN
                RR_Adjustments rr
                ON ib.WarehouseID = rr.WarehouseID AND ib.RawMaterialID = rr.RawMaterialID
            LEFT JOIN
                Status_Adjustments cs
                ON ib.WarehouseID = cs.WarehouseID AND ib.RawMaterialID = cs.RawMaterialID

            WHERE ib.statusid ISNULL

            UNION ALL

            SELECT
                hs.rawmaterialid,
                hs.RMCode,
                hs.warehouseid,
                hs.WarehouseName,
                hs.WarehouseNumber,
                hs.HeldQuantity AS New_Beginning_Balance,
                hs.Status,
                hs.StatusID
            FROM
                Held_Status_Details hs

            ORDER BY
                RMCode, WarehouseName, WarehouseNumber, Status NULLS FIRST;
        """