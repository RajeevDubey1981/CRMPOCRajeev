-- PROD FIX: backfill migrated serial warranties and refresh warranty status.
-- Run the dry-run first:
--   api/sql/prod_migrated_serial_warranty_dry_run_mysql.sql
--
-- This script is transactional for updates. Review output before keeping the run.

START TRANSACTION;

DROP TEMPORARY TABLE IF EXISTS tmp_migrated_serial_warranties;

CREATE TEMPORARY TABLE tmp_migrated_serial_warranties AS
SELECT
    LOWER(TRIM(she.serial_no)) AS serial_key,
    she.order_item_id AS history_order_item_id,
    MAX(she.id) AS latest_history_event_id,
    MAX(STR_TO_DATE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(she.metadata_json, '$.pcb_warrantyupto')), 'null'), '%Y-%m-%d')) AS pcb_warrantyupto,
    MAX(STR_TO_DATE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(she.metadata_json, '$.comp_warrantyupto')), 'null'), '%Y-%m-%d')) AS comp_warrantyupto,
    MAX(STR_TO_DATE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(she.metadata_json, '$.machin_warrantyupto')), 'null'), '%Y-%m-%d')) AS machin_warrantyupto
FROM serial_history_events she
WHERE she.event_type = 'migration'
  AND she.event_subtype = 'legacy_serial_recovery'
  AND she.serial_no IS NOT NULL
  AND JSON_VALID(she.metadata_json)
GROUP BY LOWER(TRIM(she.serial_no)), she.order_item_id;

DROP TEMPORARY TABLE IF EXISTS tmp_migrated_serial_warranty_computed_raw;
DROP TEMPORARY TABLE IF EXISTS tmp_migrated_serial_warranty_computed;

DROP TEMPORARY TABLE IF EXISTS tmp_order_item_serial_keys;

CREATE TEMPORARY TABLE tmp_order_item_serial_keys AS
SELECT
    LOWER(TRIM(serial_no)) AS serial_key,
    id AS order_item_id
FROM order_items
WHERE serial_no IS NOT NULL AND TRIM(serial_no) <> ''
UNION ALL
SELECT
    LOWER(TRIM(serial_no_2)) AS serial_key,
    id AS order_item_id
FROM order_items
WHERE serial_no_2 IS NOT NULL AND TRIM(serial_no_2) <> '';

CREATE INDEX idx_tmp_order_item_serial_keys_serial_key
    ON tmp_order_item_serial_keys(serial_key);

DROP TEMPORARY TABLE IF EXISTS tmp_unique_order_item_serial_keys;

CREATE TEMPORARY TABLE tmp_unique_order_item_serial_keys AS
SELECT
    serial_key,
    MIN(order_item_id) AS order_item_id,
    COUNT(DISTINCT order_item_id) AS order_item_count
FROM tmp_order_item_serial_keys
GROUP BY serial_key
HAVING COUNT(DISTINCT order_item_id) = 1;

CREATE INDEX idx_tmp_unique_order_item_serial_keys_serial_key
    ON tmp_unique_order_item_serial_keys(serial_key);

CREATE TEMPORARY TABLE tmp_migrated_serial_warranty_computed_raw AS
SELECT
    ms.latest_history_event_id,
    ms.serial_key,
    ms.history_order_item_id,
    oi.id AS order_item_id,
    oi.order_id,
    o.order_no,
    COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date) AS warranty_base,
    ms.pcb_warrantyupto,
    ms.comp_warrantyupto,
    ms.machin_warrantyupto,
    CASE
        WHEN COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date) IS NULL
          OR ms.pcb_warrantyupto IS NULL
        THEN NULL
        ELSE TIMESTAMPDIFF(YEAR, COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date), ms.pcb_warrantyupto)
    END AS computed_pcb_warranty_years,
    CASE
        WHEN COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date) IS NULL
          OR ms.comp_warrantyupto IS NULL
        THEN NULL
        ELSE TIMESTAMPDIFF(YEAR, COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date), ms.comp_warrantyupto)
    END AS computed_component_warranty_years,
    CASE
        WHEN COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date) IS NULL
          OR ms.machin_warrantyupto IS NULL
        THEN NULL
        ELSE TIMESTAMPDIFF(YEAR, COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date), ms.machin_warrantyupto)
    END AS computed_machine_warranty_years
FROM tmp_migrated_serial_warranties ms
LEFT JOIN tmp_unique_order_item_serial_keys oisk
  ON oisk.serial_key = ms.serial_key
  AND ms.history_order_item_id IS NULL
JOIN order_items oi
  ON oi.id = ms.history_order_item_id
  OR oi.id = oisk.order_item_id
JOIN orders o
  ON o.id = oi.order_id;

CREATE TEMPORARY TABLE tmp_migrated_serial_warranty_computed AS
SELECT
    MAX(latest_history_event_id) AS latest_history_event_id,
    MIN(serial_key) AS serial_key,
    MAX(history_order_item_id) AS history_order_item_id,
    order_item_id,
    order_id,
    order_no,
    warranty_base,
    MAX(pcb_warrantyupto) AS pcb_warrantyupto,
    MAX(comp_warrantyupto) AS comp_warrantyupto,
    MAX(machin_warrantyupto) AS machin_warrantyupto,
    MAX(computed_pcb_warranty_years) AS computed_pcb_warranty_years,
    MAX(computed_component_warranty_years) AS computed_component_warranty_years,
    MAX(computed_machine_warranty_years) AS computed_machine_warranty_years
FROM tmp_migrated_serial_warranty_computed_raw
GROUP BY
    order_item_id,
    order_id,
    order_no,
    warranty_base;

DROP TABLE IF EXISTS order_items_warranty_fix_backup_20260916;

CREATE TABLE order_items_warranty_fix_backup_20260916 AS
SELECT oi.*
FROM order_items oi
JOIN tmp_migrated_serial_warranty_computed c
  ON c.order_item_id = oi.id
WHERE oi.pcb_warranty_years IS NULL
   OR oi.component_warranty_years IS NULL
   OR oi.machine_warranty_years IS NULL;

SELECT COUNT(*) AS backed_up_order_items_in_temp_table
FROM order_items_warranty_fix_backup_20260916;

UPDATE order_items oi
JOIN tmp_migrated_serial_warranty_computed c
  ON c.order_item_id = oi.id
SET
    oi.pcb_warranty_years = COALESCE(oi.pcb_warranty_years, c.computed_pcb_warranty_years),
    oi.component_warranty_years = COALESCE(oi.component_warranty_years, c.computed_component_warranty_years),
    oi.machine_warranty_years = COALESCE(oi.machine_warranty_years, c.computed_machine_warranty_years)
WHERE (oi.pcb_warranty_years IS NULL AND c.computed_pcb_warranty_years IS NOT NULL)
   OR (oi.component_warranty_years IS NULL AND c.computed_component_warranty_years IS NOT NULL)
   OR (oi.machine_warranty_years IS NULL AND c.computed_machine_warranty_years IS NOT NULL);

SELECT ROW_COUNT() AS updated_order_items;

DROP TEMPORARY TABLE IF EXISTS tmp_order_item_warranty_status;

CREATE TEMPORARY TABLE tmp_order_item_warranty_status AS
SELECT
    oi.id AS order_item_id,
    LOWER(TRIM(oi.serial_no)) AS serial_key,
    LOWER(TRIM(oi.serial_no_2)) AS serial_key_2,
    oi.serial_no,
    oi.serial_no_2,
    CASE
        WHEN DATE_ADD(
            COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date),
            INTERVAL oi.machine_warranty_years YEAR
        ) >= CURDATE()
        THEN 'IN WARRANTY'
        ELSE 'OUT OF WARRANTY'
    END AS warranty_status
FROM order_items oi
JOIN orders o
  ON o.id = oi.order_id
WHERE oi.machine_warranty_years IS NOT NULL
  AND COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date) IS NOT NULL;

UPDATE service_request_units sru
JOIN tmp_order_item_warranty_status ws
  ON ws.order_item_id = sru.order_item_id
SET sru.warranty_status = ws.warranty_status
WHERE sru.warranty_status IS NULL
   OR sru.warranty_status <> ws.warranty_status;

SELECT ROW_COUNT() AS updated_service_request_units;

UPDATE service_requests sr
LEFT JOIN tmp_order_item_serial_keys oisk
  ON oisk.serial_key = LOWER(TRIM(sr.serial_no))
JOIN tmp_order_item_warranty_status ws
  ON ws.order_item_id = sr.order_item_id
  OR ws.order_item_id = oisk.order_item_id
SET sr.warranty_status = ws.warranty_status
WHERE sr.deleted_at IS NULL
  AND (sr.warranty_status IS NULL OR sr.warranty_status <> ws.warranty_status);

SELECT ROW_COUNT() AS updated_service_requests;

UPDATE service_observations so
LEFT JOIN service_request_units sru
  ON sru.id = so.service_request_unit_id
LEFT JOIN tmp_order_item_serial_keys oisk
  ON oisk.serial_key = LOWER(TRIM(so.serial_no))
JOIN tmp_order_item_warranty_status ws
  ON ws.order_item_id = sru.order_item_id
  OR ws.order_item_id = oisk.order_item_id
SET so.warranty_status = ws.warranty_status
WHERE so.warranty_status IS NULL
   OR so.warranty_status <> ws.warranty_status;

SELECT ROW_COUNT() AS updated_service_observations;

SELECT
    c.serial_key,
    c.order_item_id,
    c.order_no,
    oi.pcb_warranty_years,
    oi.component_warranty_years,
    oi.machine_warranty_years,
    DATE_ADD(c.warranty_base, INTERVAL oi.pcb_warranty_years YEAR) AS pcb_warranty_date,
    DATE_ADD(c.warranty_base, INTERVAL oi.component_warranty_years YEAR) AS component_warranty_date,
    DATE_ADD(c.warranty_base, INTERVAL oi.machine_warranty_years YEAR) AS machine_warranty_date
FROM tmp_migrated_serial_warranty_computed c
JOIN order_items oi
  ON oi.id = c.order_item_id
ORDER BY c.latest_history_event_id DESC
LIMIT 50;

COMMIT;
