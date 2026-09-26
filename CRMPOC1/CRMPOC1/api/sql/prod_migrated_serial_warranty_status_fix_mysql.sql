-- PROD FIX: refresh persisted service warranty statuses for migrated order items.
-- Scoped to direct order_item_id references only.

START TRANSACTION;

DROP TEMPORARY TABLE IF EXISTS tmp_order_item_warranty_status;

CREATE TEMPORARY TABLE tmp_order_item_warranty_status AS
SELECT
    oi.id AS order_item_id,
    CASE
        WHEN DATE_ADD(
            COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date),
            INTERVAL oi.machine_warranty_years YEAR
        ) >= CURDATE()
        THEN 'IN WARRANTY'
        ELSE 'OUT OF WARRANTY'
    END AS warranty_status
FROM order_items oi
JOIN order_items_warranty_fix_backup_20260916 b
  ON b.id = oi.id
JOIN orders o
  ON o.id = oi.order_id
WHERE oi.machine_warranty_years IS NOT NULL
  AND COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date) IS NOT NULL;

CREATE INDEX idx_tmp_order_item_warranty_status_item_id
    ON tmp_order_item_warranty_status(order_item_id);

DROP TABLE IF EXISTS service_request_units_warranty_fix_backup_20260916;

CREATE TABLE service_request_units_warranty_fix_backup_20260916 AS
SELECT sru.*
FROM service_request_units sru
JOIN tmp_order_item_warranty_status ws
  ON ws.order_item_id = sru.order_item_id
WHERE sru.warranty_status IS NULL
   OR CONVERT(sru.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci
      <> CONVERT(ws.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci;

DROP TABLE IF EXISTS service_requests_warranty_fix_backup_20260916;

CREATE TABLE service_requests_warranty_fix_backup_20260916 AS
SELECT sr.*
FROM service_requests sr
JOIN tmp_order_item_warranty_status ws
  ON ws.order_item_id = sr.order_item_id
WHERE sr.deleted_at IS NULL
  AND (
      sr.warranty_status IS NULL
      OR CONVERT(sr.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci
         <> CONVERT(ws.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci
  );

DROP TABLE IF EXISTS service_observations_warranty_fix_backup_20260916;

CREATE TABLE service_observations_warranty_fix_backup_20260916 AS
SELECT so.*
FROM service_observations so
JOIN service_request_units sru
  ON sru.id = so.service_request_unit_id
JOIN tmp_order_item_warranty_status ws
  ON ws.order_item_id = sru.order_item_id
WHERE so.warranty_status IS NULL
   OR CONVERT(so.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci
      <> CONVERT(ws.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci;

SELECT COUNT(*) AS backed_up_service_request_units
FROM service_request_units_warranty_fix_backup_20260916;

SELECT COUNT(*) AS backed_up_service_requests
FROM service_requests_warranty_fix_backup_20260916;

SELECT COUNT(*) AS backed_up_service_observations
FROM service_observations_warranty_fix_backup_20260916;

UPDATE service_request_units sru
JOIN tmp_order_item_warranty_status ws
  ON ws.order_item_id = sru.order_item_id
SET sru.warranty_status = ws.warranty_status
WHERE sru.warranty_status IS NULL
   OR CONVERT(sru.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci
      <> CONVERT(ws.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci;

SELECT ROW_COUNT() AS updated_service_request_units;

UPDATE service_requests sr
JOIN tmp_order_item_warranty_status ws
  ON ws.order_item_id = sr.order_item_id
SET sr.warranty_status = ws.warranty_status
WHERE sr.deleted_at IS NULL
  AND (
      sr.warranty_status IS NULL
      OR CONVERT(sr.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci
         <> CONVERT(ws.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci
  );

SELECT ROW_COUNT() AS updated_service_requests;

UPDATE service_observations so
JOIN service_request_units sru
  ON sru.id = so.service_request_unit_id
JOIN tmp_order_item_warranty_status ws
  ON ws.order_item_id = sru.order_item_id
SET so.warranty_status = ws.warranty_status
WHERE so.warranty_status IS NULL
   OR CONVERT(so.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci
      <> CONVERT(ws.warranty_status USING utf8mb4) COLLATE utf8mb4_unicode_ci;

SELECT ROW_COUNT() AS updated_service_observations;

COMMIT;
