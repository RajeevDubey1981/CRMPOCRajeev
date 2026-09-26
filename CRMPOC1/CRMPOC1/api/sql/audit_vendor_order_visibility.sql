-- Audit vendor order visibility.
-- Vendor users can see orders only when users.email matches vendors.email.

SELECT
    v.id AS vendor_id,
    v.vendor_code,
    v.name_of_firm,
    v.email AS vendor_email,
    u.id AS user_id,
    u.email AS user_email,
    u.role AS user_role,
    u.is_active AS user_is_active,
    COUNT(o.id) AS order_count,
    CASE
        WHEN COUNT(o.id) = 0 THEN 'NO_ORDERS'
        WHEN v.email IS NULL OR TRIM(v.email) = '' THEN 'VENDOR_EMAIL_MISSING'
        WHEN u.id IS NULL THEN 'VENDOR_USER_MISSING'
        WHEN LOWER(u.role) <> 'vendor' THEN 'USER_ROLE_NOT_VENDOR'
        WHEN u.is_active = 0 THEN 'USER_INACTIVE'
        ELSE 'OK'
    END AS visibility_status
FROM vendors v
LEFT JOIN users u
    ON LOWER(TRIM(u.email)) = LOWER(TRIM(v.email))
    AND u.deleted_at IS NULL
LEFT JOIN orders o
    ON o.vendor_id = v.id
    AND o.deleted_at IS NULL
WHERE v.deleted_at IS NULL
GROUP BY
    v.id,
    v.vendor_code,
    v.name_of_firm,
    v.email,
    u.id,
    u.email,
    u.role,
    u.is_active
ORDER BY
    visibility_status DESC,
    order_count DESC,
    v.name_of_firm;

-- Known repair: Savitar Services.
-- Run only after confirming vivek.s@pia-consultancy.com is the Savitar login.
/*
UPDATE vendors
SET email = 'vivek.s@pia-consultancy.com'
WHERE name_of_firm = 'SAVITAR SERVICES PVT LTD'
  AND deleted_at IS NULL;

UPDATE users
SET role = 'vendor', is_active = 1
WHERE email = 'vivek.s@pia-consultancy.com'
  AND deleted_at IS NULL;
*/
