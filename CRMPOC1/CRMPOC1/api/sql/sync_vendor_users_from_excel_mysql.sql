-- Sync vendor emails, vendor categories, and vendor login users.
-- Source: C:\Users\rajee\Downloads\vendorwithn oemail.xlsx
-- DB: MySQL/MariaDB
--
-- Important:
-- - Vendor order visibility requires vendors.email = users.email.
-- - The Excel user_email value is used as the final login email.
-- - Missing users are created with default password: vendor123

START TRANSACTION;

SET @add_vendor_type_sql := IF(
    (
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'vendors'
          AND COLUMN_NAME = 'vendor_type'
    ) = 0,
    'ALTER TABLE vendors ADD COLUMN vendor_type VARCHAR(100) NULL',
    'SELECT 1'
);
PREPARE add_vendor_type_stmt FROM @add_vendor_type_sql;
EXECUTE add_vendor_type_stmt;
DEALLOCATE PREPARE add_vendor_type_stmt;

CREATE TEMPORARY TABLE vendor_user_sync (
    vendor_id INT NOT NULL,
    vendor_code VARCHAR(100) NULL,
    name_of_firm VARCHAR(255) NOT NULL,
    login_email VARCHAR(255) NOT NULL,
    vendor_type VARCHAR(100) NULL,
    PRIMARY KEY (vendor_id)
);

INSERT INTO vendor_user_sync (vendor_id, vendor_code, name_of_firm, login_email, vendor_type) VALUES
(1001088, 'IDCVEN000017', 'Vasu Enterprises', 'vasuenterprises.9669@gmail.com', 'Gem Partner'),
(1001077, 'IDCVEN000008', 'INDCOOL ELECTRICALS PVT LTD', 'info@indcool.in', 'Gem Partner'),
(1001091, 'IDCVEN000022', 'SHANVI ENTERPRISES', 'shanvienterprisesgem@gmail.com', 'Gem Partner'),
(1001083, 'IDCVEN000013', 'SMART COOL TECH', 'smartcooltech77@gmail.com', 'Gem Partner'),
(1001093, 'IDCVEN000024', 'ARIHANT ENGINEERING WORKS', 'arihantenggjain@gmail.com', 'Retailer'),
(1001110, 'IDCVEN000037', 'NEW BHATIA DISC CENTRE', 'rajeevgem22@gmail.com', 'Gem Partner'),
(1001076, 'IDCVEN000007~LEGACY-13', 'SAI ENTERPRISES', 'asrraghav06@gmail.com', 'Gem Partner'),
(1001067, 'IDCVEN000001', 'SAVITAR SERVICES PVT LTD', 'vivek.s@pia-consultancy.com', 'Gem Partner'),
(1001089, 'IDCVEN000018', 'SHIV SHAKTI TRADING COMPANY', 'care.sstc2022@gmail.com', 'Gem Partner'),
(1001073, 'IDCVEN000006', 'COMTECH GROUP', 'dhanprigroup@gmail.com', 'Gem Partner'),
(1001072, 'IDC000051', 'COMTECH ENTERPRISES', 'comtechenterprises@gmail.com', 'Gem Partner'),
(1001068, 'IDCVEN000002', 'PRIMATEL FIBCOM LIMITED', 'rma@ptfl.in', 'Gem Partner'),
(1001111, 'IDCVEN000038', 'MINEWORTH ENGINEERING PRODUCTS PRIVATE LIMITED', 'mineworth8@gmail.com', 'Gem Partner'),
(1001090, 'IDCVEN000021', 'SARP and Company', 'sarpandcompany@gmail.com', 'Gem Partner'),
(1001105, 'IDCVEN000032', 'GALAXY DIGITAL', 'galaxy.bpl4@gmail.com', 'Gem Partner'),
(1001070, 'IDCVEN000004', 'R S ELECTRO-MECH CORPORATION', 'rselectromech2@gmail.com', 'Gem Partner'),
(1001081, 'IDCVEN000011', 'JAI BALAJI & SONS', 'harshmani4904@gmail.com', 'Gem Partner'),
(1001087, 'IDCVEN000015~LEGACY-24', 'RUCHI ELECTRONICS', 'ruchielectronics@gmail.com', 'Gem Partner'),
(1001130, 'IDCVEN000056', 'National Contractors', 'nationalcontractors.panindia@gmail.com', 'Gem Partner'),
(1001074, 'IDCVEN000027', 'UNIQUE INDIA', 'uniqueindialko@gmail.com', 'Gem Partner'),
(1001109, 'IDCDLRCSD00001', 'BALAJI ELECTROVISION', 'p.kumar1980p@gmail.com', 'CSD'),
(1001071, 'IDCVEN000005', 'M/S KAMINI DISTRIBUTORS', 'kaminidistributors16@gmail.com', 'Gem Partner'),
(1001106, 'IDCVEN000033', 'NITIN ENGINEERS', 'nitinengineers31@gmail.com', 'Gem Partner'),
(1001104, 'IDCVEN000030', 'SUBPLOT LLP', 'subplotllp@gmail.com', 'Gem Partner'),
(1001103, 'IDCVEN000029', 'Akshay Traders', 'akshaytraders94@gmail.com', 'Gem Partner'),
(1001079, 'IDCVEN000010', 'BHAGYA LAXMI INTERNATIONAL', 'international.bhagyalaxmi@gmail.com', 'Gem Partner'),
(1001092, 'IDCVEN000023', 'HIND TRADING CO', 'hindtc01@gmail.com', 'Gem Partner'),
(1001078, 'IDCVEN000009', 'KAMANA ASSOCIATE', 'kamanaassociate@gmail.com', 'Gem Partner'),
(1001112, 'IDCVEN000038~LEGACY-49', 'RITIKA ENTERPRISES', 'ritikakosli@gmail.com', 'CSD'),
(1001069, 'IDCVEN000003', 'APPEXIAL PRIVATE LIMITED', 'info@appexial.in', 'Gem Partner'),
(1001108, 'IDCVEN000035', 'LG LAMINATES', 'lglaminates@gmail.com', 'CSD'),
(1001131, 'IDCVEN000057', 'NISNIK INTERNATIONAL', 'nisnikinternational@gmail.com', 'Gem Partner'),
(1001139, 'IDCVEN000065', 'ARYA ENGINEERING CORPORATION', 'aryaengcorp@gmail.com', 'Gem Partner'),
(1001084, 'IDCVEN000014', 'BHAGWATI TRADING CO', 'bhagwatikarnal@gmail.com', 'Gem Partner'),
(1001075, 'IDCVEN000007', 'GARG ENTERPRISES', 'gargenterprises15153@gmail.com', 'Gem Partner'),
(1001133, 'IDCVEN000059', 'LOTUS BUSINESS ALLIANCE', 'lotusbusinessalliance@gmail.com', 'Gem Partner'),
(1001113, 'IDCVEN000040', 'M/s Sachin Agarwal', 'dineshagarwal73@gmail.com', 'Gem Partner'),
(1001085, 'IDCVEN000015', 'PKG ENTERPRISES', 'pkgenterpriese@gmail.com', 'Retailer'),
(1001118, 'IDCVEN000044', 'ALPHA TRADING & PROMOTIONS', 'alphatrading91@yahoo.com', 'CSD'),
(1001097, 'IDCVEN000025~LEGACY-34', 'Aryan Cooling Solution', 'adnanman571@gmail.com', 'Service Partner'),
(1001099, 'IDCVEN000028', 'AVNI HOME SERVICES LLP', 'avnihomeservices01@gmail.com', 'Service Partner / Gem Partner'),
(1001141, 'IDCVEN000067', 'BALAJI ELECTROVISION', 'p.kumar1980pq@gmail.com', 'CSD'),
(1001123, 'IDCVEN000049', 'BHARAT TRADING COMPANY', 'ashishkansal1610@gmail.com', 'Gem Partner'),
(1001127, 'IDCVEN000053', 'BINARY VENDORS', 'ceo@panacean.cool', 'Retailer'),
(1001137, 'IDCVEN000063', 'Brahmdev Distributors', 'brahmadevdis001@gmail.com', 'CSD'),
(1001119, 'IDCVEN000045', 'CAK ELECTRONICS', 'charukansal1976@gmail.com', 'CSD'),
(1001096, 'IDCVEN000025', 'DEEPAK AIRCON', 'ideepakkumargond@gmail.com', 'CSD'),
(1001132, 'IDCVEN000058', 'DRISHTI ENTERPRISES', 'drishtienterprises182@gmail.com', 'Service Partner'),
(1001066, 'VEN051', 'GLOBAL AIRCON', 'globalaircon2001@gmail.com', 'Service Partner'),
(1001142, 'IDCVEN000068', 'HOME MAKERS', 'homemakers.hyd@gmail.com', 'CSD'),
(1001136, 'IDCVEN000062', 'Ishaq Enterprises', 'ishaqenterprises2003@gmail.com', 'CSD'),
(1001080, 'IDCVEN000010~LEGACY-17', 'JAI BALAJI & SON', 'harshmani4904@gmail.com', 'CSD'),
(1001115, 'IDCVEN000041~LEGACY-52', 'JAI BALAJI TRADING COMPANY (INDCOOL)', 'khetaramgodara567@gmail.com', 'CSD'),
(1001065, 'VEN050', 'Legacy vendor 2', 'gifcoolservice@gmail.com', 'CSD'),
(1001107, 'IDCVEN000034', 'LG LAMINATES', 'lglaminates@gmail.com', 'CSD'),
(1001126, 'IDCVEN000052', 'Loyal Enterprises', 'loyalenterprise9@gmail.com', 'CSD'),
(1001116, 'IDCVEN000042', 'MAA BHAGWATI ENTERPRISES', 'maabhagwatienterprises97@gmail.com', 'Retailer'),
(1001140, 'IDCVEN000066', 'MAA BHAGWATI ENTERPRISES', 'maabhagwatienterprises97@gmail.com', 'Retailer'),
(1001134, 'IDCVEN000060', 'MANDAL ENTERPRISES', 'michael.hr@sinaiic.com', 'Service Partner'),
(1001145, 'IDCISP108', 'NEW AIR COOLING POINT', 'newaircoolingpoint653@gmail.com', 'Retailer / Service Partner'),
(1001121, 'IDCVEN000047', 'NEW LIGHT STORE', 'satish.chandra1958@gmail.com', 'Retailer'),
(1001117, 'IDCVEN000043', 'NEXT DIGITAL HOME', 'rahul.nextdigitalhome@gmail.com', 'CSD'),
(1001120, 'IDCVEN000046', 'PERFECTION', 'perfectionbhopal@yahoo.in', 'Retailer'),
(1001086, 'IDCVEN000015~LEGACY-23', 'PKG ENTERPRISES', 'pkgenterpriese@gmail.com', NULL),
(1001102, 'LEGACY-VENDOR-39', 'QUICK COOL', 'quick.coolref@gmail.com', 'Service Partner'),
(1001082, 'DCVEN000012', 'RUCHI ELECTRONICS', 'ruchielectronics@gmail.com', 'Gem Partner'),
(1001125, 'IDCVEN000051', 'Sachdeva Electronic Center', 'sachdeva31@rediffmail.com', 'CSD'),
(1001122, 'IDCVEN000048', 'SAINIK ELECTRONICS STORE', 'neera17tomar@gmail.com', 'Retailer'),
(1001100, 'LEGACY-VENDOR-37', 'Sashi Refrigeration', 'manoranjan@indcool.in', 'Service Partner'),
(1001101, 'LEGACY-VENDOR-38', 'SHANVI ENTERPRISES', 'shanvientp.services@gmail.com', 'Gem Partner'),
(1001098, 'IDCVEN000027~LEGACY-35', 'Shiv AC Service', 'parmarravi2124@gmail.com', 'Service Partner'),
(1001129, 'IDCVEN000055', 'Shiva Airconditioning Service', 'zamirhasan192@gmail.com', 'Service Partner'),
(1001135, 'IDCVEN000061', 'Sinai INC', 'michael.hr@sinaiic.com', 'Retailer'),
(1001124, 'IDCVEN000050', 'Subhash Chand Ashok Kumar', 'scakrm@gmail.com', 'CSD');

UPDATE vendors v
JOIN vendor_user_sync s ON s.vendor_id = v.id
SET
    v.email = s.login_email,
    v.vendor_type = COALESCE(s.vendor_type, v.vendor_type),
    v.is_active = 1
WHERE v.deleted_at IS NULL;

UPDATE users u
JOIN vendor_user_sync s ON LOWER(TRIM(u.email)) = LOWER(TRIM(s.login_email))
SET
    u.role = 'vendor',
    u.is_active = 1,
    u.deleted_at = NULL;

INSERT INTO users (name, email, password_hash, role, phone, is_active)
SELECT
    COALESCE(NULLIF(TRIM(v.contact_name), ''), v.name_of_firm, s.login_email) AS name,
    s.login_email,
    '$2b$12$S9KOheh2yrVMJ88JMs1l/uaKwIhUh/qdvqGZAxtTiwTZrJJug.Shq' AS password_hash,
    'vendor' AS role,
    v.contact_mobile AS phone,
    1 AS is_active
FROM vendor_user_sync s
JOIN vendors v ON v.id = s.vendor_id
LEFT JOIN users u ON LOWER(TRIM(u.email)) = LOWER(TRIM(s.login_email))
WHERE u.id IS NULL
  AND v.deleted_at IS NULL;

SELECT
    v.id AS vendor_id,
    v.vendor_code,
    v.name_of_firm,
    v.email AS vendor_email,
    v.vendor_type,
    u.id AS user_id,
    u.email AS user_email,
    u.role AS user_role,
    u.is_active AS user_is_active,
    CASE
        WHEN LOWER(TRIM(v.email)) <> LOWER(TRIM(u.email)) THEN 'EMAIL_MISMATCH'
        WHEN u.id IS NULL THEN 'USER_MISSING'
        WHEN u.role <> 'vendor' THEN 'ROLE_NOT_VENDOR'
        WHEN u.is_active <> 1 THEN 'USER_INACTIVE'
        ELSE 'OK'
    END AS status
FROM vendor_user_sync s
JOIN vendors v ON v.id = s.vendor_id
LEFT JOIN users u ON LOWER(TRIM(u.email)) = LOWER(TRIM(s.login_email))
ORDER BY status DESC, v.name_of_firm;

COMMIT;
