-- PROD DRY RUN: migrated serial warranty repair preview.
-- This does not update data.

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
    oi.serial_no AS order_item_serial_no,
    oi.serial_no_2 AS order_item_serial_no_2,
    oi.pcb_warranty_years AS current_pcb_warranty_years,
    oi.component_warranty_years AS current_component_warranty_years,
    oi.machine_warranty_years AS current_machine_warranty_years,
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
    order_item_serial_no,
    order_item_serial_no_2,
    current_pcb_warranty_years,
    current_component_warranty_years,
    current_machine_warranty_years,
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
    order_item_serial_no,
    order_item_serial_no_2,
    current_pcb_warranty_years,
    current_component_warranty_years,
    current_machine_warranty_years,
    warranty_base;

SELECT
    COUNT(*) AS matched_order_items,
    SUM(
        current_pcb_warranty_years IS NULL
        OR current_component_warranty_years IS NULL
        OR current_machine_warranty_years IS NULL
    ) AS order_items_with_any_missing_warranty_years,
    SUM(computed_pcb_warranty_years IS NOT NULL) AS computable_pcb_rows,
    SUM(computed_component_warranty_years IS NOT NULL) AS computable_component_rows,
    SUM(computed_machine_warranty_years IS NOT NULL) AS computable_machine_rows
FROM tmp_migrated_serial_warranty_computed;

SELECT
    latest_history_event_id,
    serial_key,
    order_item_id,
    order_no,
    order_item_serial_no,
    order_item_serial_no_2,
    warranty_base,
    pcb_warrantyupto,
    comp_warrantyupto,
    machin_warrantyupto,
    current_pcb_warranty_years,
    computed_pcb_warranty_years,
    current_component_warranty_years,
    computed_component_warranty_years,
    current_machine_warranty_years,
    computed_machine_warranty_years
FROM tmp_migrated_serial_warranty_computed
WHERE current_pcb_warranty_years IS NULL
   OR current_component_warranty_years IS NULL
   OR current_machine_warranty_years IS NULL
ORDER BY latest_history_event_id DESC
LIMIT 100;

SELECT 'service_requests' AS table_name, COUNT(*) AS rows_that_would_get_warranty_status
FROM service_requests sr
LEFT JOIN tmp_order_item_serial_keys oisk
  ON oisk.serial_key = LOWER(TRIM(sr.serial_no))
JOIN order_items oi
  ON oi.id = sr.order_item_id
  OR oi.id = oisk.order_item_id
WHERE sr.deleted_at IS NULL
  AND oi.machine_warranty_years IS NOT NULL;

SELECT 'service_request_units' AS table_name, COUNT(*) AS rows_that_would_get_warranty_status
FROM service_request_units sru
JOIN order_items oi
  ON oi.id = sru.order_item_id
WHERE oi.machine_warranty_years IS NOT NULL;

SELECT 'service_observations' AS table_name, COUNT(*) AS rows_that_would_get_warranty_status
FROM service_observations so
LEFT JOIN service_request_units sru
  ON sru.id = so.service_request_unit_id
LEFT JOIN tmp_order_item_serial_keys oisk
  ON oisk.serial_key = LOWER(TRIM(so.serial_no))
JOIN order_items oi
  ON oi.id = sru.order_item_id
  OR oi.id = oisk.order_item_id
WHERE oi.machine_warranty_years IS NOT NULL;
