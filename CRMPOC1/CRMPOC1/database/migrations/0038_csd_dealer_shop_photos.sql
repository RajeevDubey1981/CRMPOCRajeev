-- ==========================================================================
-- Migration: 0038_csd_dealer_shop_photos
-- Description: Add 5 shop photo columns to partner_registrations and
--              exempt CSD Dealer from GeM Seller ID requirement
-- Date: 2026-09-19
-- ==========================================================================

-- ========== ADD SHOP PHOTO COLUMNS ==========
ALTER TABLE `partner_registrations`
  ADD COLUMN `shop_photo_1_path` VARCHAR(500) NULL AFTER `photo_path`,
  ADD COLUMN `shop_photo_2_path` VARCHAR(500) NULL AFTER `shop_photo_1_path`,
  ADD COLUMN `shop_photo_3_path` VARCHAR(500) NULL AFTER `shop_photo_2_path`,
  ADD COLUMN `shop_photo_4_path` VARCHAR(500) NULL AFTER `shop_photo_3_path`,
  ADD COLUMN `shop_photo_5_path` VARCHAR(500) NULL AFTER `shop_photo_4_path`;
