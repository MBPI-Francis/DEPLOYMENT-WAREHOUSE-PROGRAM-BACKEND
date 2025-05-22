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
        ), spillage_adjustment_form AS (
         SELECT spillage.warehouse_id AS warehouseid,
            spillage.rm_code_id AS rawmaterialid,
            sum(spillage.qty_kg) AS total_spillage_quantity,
            spillage.date_computed AS datecomputed,
            status.name AS status,
            status.id AS statusid
           FROM tbl_adjustment_spillage spillage
             JOIN tbl_warehouses wh ON spillage.warehouse_id = wh.id
             JOIN tbl_status status ON spillage.status_id = status.id
          WHERE (spillage.is_cleared IS NULL OR spillage.is_cleared = false) AND (spillage.is_deleted IS NULL OR spillage.is_deleted = false) AND spillage.date_computed IS NULL
          GROUP BY spillage.warehouse_id, spillage.rm_code_id, spillage.date_computed, status.name, status.id
        ), computed_statement AS (
         SELECT eb.rawmaterialid,
            eb.rmcode,
            eb.warehouseid,
            eb.warehousename,
            eb.warehousenumber,
            eb.new_beginning_balance +
                CASE
                    WHEN eb.status::text = 'held : reject'::text THEN - COALESCE(
                    CASE
                        WHEN spillage.status::text = 'held : reject'::text THEN spillage.total_spillage_quantity
                        ELSE NULL::numeric
                    END, 0::numeric)
                    WHEN eb.status::text = 'held : contaminated'::text THEN - COALESCE(
                    CASE
                        WHEN spillage.status::text = 'held : contaminated'::text THEN spillage.total_spillage_quantity
                        ELSE NULL::numeric
                    END, 0::numeric)
                    WHEN eb.status::text = 'held : under evaluation'::text THEN - COALESCE(
                    CASE
                        WHEN spillage.status::text = 'held : under evaluation'::text THEN spillage.total_spillage_quantity
                        ELSE NULL::numeric
                    END, 0::numeric)
                    WHEN eb.status::text = 'good'::text THEN - COALESCE(
                    CASE
                        WHEN spillage.status::text = 'good'::text THEN spillage.total_spillage_quantity
                        ELSE NULL::numeric
                    END, 0::numeric)
                    ELSE NULL::numeric
                END AS adjusted_ending_balance,
            COALESCE(eb.status, ''::character varying) AS status,
            eb.statusid
           FROM ending_balance eb
             LEFT JOIN spillage_adjustment_form spillage ON eb.warehouseid = spillage.warehouseid AND eb.rawmaterialid = spillage.rawmaterialid AND eb.statusid = spillage.statusid
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

