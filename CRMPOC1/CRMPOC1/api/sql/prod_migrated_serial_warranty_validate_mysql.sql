-- PROD validation for migrated serial warranty backfill.

SELECT
    COUNT(*) AS backup_rows
FROM order_items_warranty_fix_backup_20260916;

SELECT
    COUNT(*) AS migrated_order_items_still_missing_all_warranty_years
FROM order_items oi
JOIN order_items_warranty_fix_backup_20260916 b
  ON b.id = oi.id
WHERE oi.pcb_warranty_years IS NULL
  AND oi.component_warranty_years IS NULL
  AND oi.machine_warranty_years IS NULL;

SELECT
    oi.id,
    o.order_no,
    oi.serial_no,
    oi.serial_no_2,
    COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date) AS warranty_base,
    oi.pcb_warranty_years,
    oi.component_warranty_years,
    oi.machine_warranty_years,
    DATE_ADD(COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date), INTERVAL oi.pcb_warranty_years YEAR) AS pcb_warranty_date,
    DATE_ADD(COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date), INTERVAL oi.component_warranty_years YEAR) AS component_warranty_date,
    DATE_ADD(COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date), INTERVAL oi.machine_warranty_years YEAR) AS machine_warranty_date
FROM order_items oi
JOIN orders o
  ON o.id = oi.order_id
WHERE LOWER(oi.serial_no) = LOWER('IDCACEZI24091301498')
   OR LOWER(oi.serial_no_2) = LOWER('IDCACEZI24091301498');
