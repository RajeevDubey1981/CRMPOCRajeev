/*
  INDcool CRM MySQL cleanup script.

  Deletes all rows from the indcool database, but keeps only:
    users.email = 'admin@indcool.com'
    roles, permissions, alembic_version (left untouched)

  This does not drop tables.
*/

USE indcool;

SET SQL_SAFE_UPDATES = 0;
SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM `calls`;
DELETE FROM `claim_photos`;
DELETE FROM `claims`;
DELETE FROM `complaint_status_logs`;
DELETE FROM `complaints`;
DELETE FROM `couriers`;
DELETE FROM `installation_documents`;
DELETE FROM `installation_engineer_serials`;
DELETE FROM `installation_requests`;
DELETE FROM `installation_status_logs`;
DELETE FROM `item_masters`;
DELETE FROM `market_categories`;
DELETE FROM `market_items`;
DELETE FROM `market_order_items`;
DELETE FROM `market_orders`;
DELETE FROM `market_users`;
DELETE FROM `order_items`;
DELETE FROM `orders`;
DELETE FROM `partner_agreements`;
DELETE FROM `partner_registrations`;
DELETE FROM `payment_transactions`;
DELETE FROM `projects`;
DELETE FROM `serial_history_events`;
DELETE FROM `service_approvals`;
DELETE FROM `service_assignments`;
DELETE FROM `service_completions`;
DELETE FROM `service_document_rules`;
DELETE FROM `service_documents`;
DELETE FROM `service_notifications`;
DELETE FROM `service_observations`;
DELETE FROM `service_payment_requests`;
DELETE FROM `service_request_items`;
DELETE FROM `service_request_units`;
DELETE FROM `service_requests`;
DELETE FROM `service_status_logs`;
DELETE FROM `service_unit_assignments`;
DELETE FROM `user_pending_actions`;
DELETE FROM `vendors`;
DELETE FROM `workflow_tasks`;

DELETE FROM `users`
WHERE LOWER(TRIM(`email`)) <> 'admin@indcool.com'
   OR `email` IS NULL;

SET FOREIGN_KEY_CHECKS = 1;

COMMIT;

SELECT `id`, `name`, `email`, `role`
FROM `users`
ORDER BY `id`;

SELECT 'alembic_version' AS table_name, COUNT(*) AS row_count FROM `alembic_version`
UNION ALL SELECT 'calls', COUNT(*) FROM `calls`
UNION ALL SELECT 'claim_photos', COUNT(*) FROM `claim_photos`
UNION ALL SELECT 'claims', COUNT(*) FROM `claims`
UNION ALL SELECT 'complaint_status_logs', COUNT(*) FROM `complaint_status_logs`
UNION ALL SELECT 'complaints', COUNT(*) FROM `complaints`
UNION ALL SELECT 'couriers', COUNT(*) FROM `couriers`
UNION ALL SELECT 'installation_documents', COUNT(*) FROM `installation_documents`
UNION ALL SELECT 'installation_engineer_serials', COUNT(*) FROM `installation_engineer_serials`
UNION ALL SELECT 'installation_requests', COUNT(*) FROM `installation_requests`
UNION ALL SELECT 'installation_status_logs', COUNT(*) FROM `installation_status_logs`
UNION ALL SELECT 'item_masters', COUNT(*) FROM `item_masters`
UNION ALL SELECT 'market_categories', COUNT(*) FROM `market_categories`
UNION ALL SELECT 'market_items', COUNT(*) FROM `market_items`
UNION ALL SELECT 'market_order_items', COUNT(*) FROM `market_order_items`
UNION ALL SELECT 'market_orders', COUNT(*) FROM `market_orders`
UNION ALL SELECT 'market_users', COUNT(*) FROM `market_users`
UNION ALL SELECT 'order_items', COUNT(*) FROM `order_items`
UNION ALL SELECT 'orders', COUNT(*) FROM `orders`
UNION ALL SELECT 'partner_agreements', COUNT(*) FROM `partner_agreements`
UNION ALL SELECT 'partner_registrations', COUNT(*) FROM `partner_registrations`
UNION ALL SELECT 'payment_transactions', COUNT(*) FROM `payment_transactions`
UNION ALL SELECT 'permissions', COUNT(*) FROM `permissions`
UNION ALL SELECT 'projects', COUNT(*) FROM `projects`
UNION ALL SELECT 'roles', COUNT(*) FROM `roles`
UNION ALL SELECT 'serial_history_events', COUNT(*) FROM `serial_history_events`
UNION ALL SELECT 'service_approvals', COUNT(*) FROM `service_approvals`
UNION ALL SELECT 'service_assignments', COUNT(*) FROM `service_assignments`
UNION ALL SELECT 'service_completions', COUNT(*) FROM `service_completions`
UNION ALL SELECT 'service_document_rules', COUNT(*) FROM `service_document_rules`
UNION ALL SELECT 'service_documents', COUNT(*) FROM `service_documents`
UNION ALL SELECT 'service_notifications', COUNT(*) FROM `service_notifications`
UNION ALL SELECT 'service_observations', COUNT(*) FROM `service_observations`
UNION ALL SELECT 'service_payment_requests', COUNT(*) FROM `service_payment_requests`
UNION ALL SELECT 'service_request_items', COUNT(*) FROM `service_request_items`
UNION ALL SELECT 'service_request_units', COUNT(*) FROM `service_request_units`
UNION ALL SELECT 'service_requests', COUNT(*) FROM `service_requests`
UNION ALL SELECT 'service_status_logs', COUNT(*) FROM `service_status_logs`
UNION ALL SELECT 'service_unit_assignments', COUNT(*) FROM `service_unit_assignments`
UNION ALL SELECT 'user_pending_actions', COUNT(*) FROM `user_pending_actions`
UNION ALL SELECT 'users', COUNT(*) FROM `users`
UNION ALL SELECT 'vendors', COUNT(*) FROM `vendors`
UNION ALL SELECT 'workflow_tasks', COUNT(*) FROM `workflow_tasks`;
