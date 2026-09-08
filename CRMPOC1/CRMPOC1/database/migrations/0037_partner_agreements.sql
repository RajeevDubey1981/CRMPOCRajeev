-- ==========================================================================
-- Migration: 0037_partner_agreements
-- Description: Add partner_agreements table for OTP-signed service agreements
-- Date: 2026-09-08
-- ==========================================================================

-- ========== CREATE TABLE ==========
CREATE TABLE IF NOT EXISTS `partner_agreements` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `registration_id` INT UNSIGNED NOT NULL,
  `agreement_no` VARCHAR(50) NOT NULL,
  `agreement_version` VARCHAR(10) NOT NULL DEFAULT '1.0',
  `access_token` VARCHAR(64) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `signed_at` DATETIME(6) NULL,
  `ip_address` VARCHAR(45) NULL,
  `user_agent` LONGTEXT NULL,
  `otp_code` VARCHAR(10) NULL,
  `otp_expires_at` DATETIME(6) NULL,
  `otp_attempts` INT NOT NULL DEFAULT 0,
  `otp_sent_at` DATETIME(6) NULL,
  `otp_send_count` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  PRIMARY KEY (`id`),

  CONSTRAINT `fk_partner_agreements_registration_id`
    FOREIGN KEY (`registration_id`)
    REFERENCES `partner_registrations` (`id`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========== CREATE INDEXES ==========
CREATE INDEX `ix_partner_agreements_registration_id`
  ON `partner_agreements` (`registration_id`);

CREATE UNIQUE INDEX `ix_partner_agreements_agreement_no`
  ON `partner_agreements` (`agreement_no`);

CREATE UNIQUE INDEX `ix_partner_agreements_access_token`
  ON `partner_agreements` (`access_token`);

CREATE INDEX `ix_partner_agreements_email`
  ON `partner_agreements` (`email`);

-- ========== COMMENTS ==========
ALTER TABLE `partner_agreements`
  COMMENT = 'Digital signing of service agreements via Email OTP. One row per registration, stores OTP state and signing timestamps.';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `id` INT UNSIGNED NOT NULL AUTO_INCREMENT
  COMMENT = 'Primary key';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `registration_id` INT UNSIGNED NOT NULL
  COMMENT = 'Foreign key to partner_registrations';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `agreement_no` VARCHAR(50) NOT NULL
  COMMENT = 'Unique agreement reference number (AGR-YYYY-XXXXX format)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `agreement_version` VARCHAR(10) NOT NULL DEFAULT '1.0'
  COMMENT = 'Agreement text version (1.0, etc.) for historical tracking';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `access_token` VARCHAR(64) NOT NULL
  COMMENT = 'URL-safe token for public access to signing page (urlsafe base64)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `email` VARCHAR(255) NOT NULL
  COMMENT = 'Email address from partner registration (where OTP is sent)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `signed_at` DATETIME(6) NULL
  COMMENT = 'Timestamp when partner successfully signed agreement via OTP';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `ip_address` VARCHAR(45) NULL
  COMMENT = 'IP address of client when signing (IPv4 or IPv6)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `user_agent` LONGTEXT NULL
  COMMENT = 'HTTP User-Agent header at signing time';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `otp_code` VARCHAR(10) NULL
  COMMENT = 'Current 6-digit OTP (cleared after successful verification or expiry)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `otp_expires_at` DATETIME(6) NULL
  COMMENT = 'When the current OTP expires (10 minutes from issue)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `otp_attempts` INT NOT NULL DEFAULT 0
  COMMENT = 'Failed OTP entry attempts (max 3, then lockout)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `otp_sent_at` DATETIME(6) NULL
  COMMENT = 'Timestamp of last OTP send (used for resend cooldown)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `otp_send_count` INT NOT NULL DEFAULT 0
  COMMENT = 'Total number of OTP sends for this agreement (max 5)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
  COMMENT = 'Row creation timestamp (when admin approved the registration)';

ALTER TABLE `partner_agreements`
  MODIFY COLUMN `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
  COMMENT = 'Last modification timestamp';
