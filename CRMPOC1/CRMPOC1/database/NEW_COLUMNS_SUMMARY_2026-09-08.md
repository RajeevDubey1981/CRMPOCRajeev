# New Tables & Columns Summary — 2026-09-08

## Overview
One new table created today: `partner_agreements` for OTP-signed digital service agreements.

---

## Table: `partner_agreements`

**Purpose:** Stores partner agreement signing state and OTP verification records for digital acceptance via email OTP.

**Created by:** Migration `0037_partner_agreements`

**Total Columns:** 16

### Column Breakdown

#### Identification Columns (3)
| Column | Type | Nullable | Default | Unique | Index | Purpose |
|--------|------|----------|---------|--------|-------|---------|
| `id` | INT UNSIGNED | NO | AUTO_INCREMENT | YES (PK) | YES | Primary key, auto-incrementing |
| `agreement_no` | VARCHAR(50) | NO | — | YES | YES | Unique agreement reference (AGR-2026-00001 format) |
| `access_token` | VARCHAR(64) | NO | — | YES | YES | URL-safe token for public signing page link |

#### Relationship Columns (1)
| Column | Type | Nullable | Default | Index | Purpose |
|--------|------|----------|---------|-------|---------|
| `registration_id` | INT UNSIGNED | NO | — | YES | Foreign key → partner_registrations.id |

#### Agreement Metadata Columns (3)
| Column | Type | Nullable | Default | Index | Purpose |
|--------|------|----------|---------|-------|---------|
| `agreement_version` | VARCHAR(10) | NO | '1.0' | NO | Versioning of agreement text (1.0, 1.1, etc.) |
| `email` | VARCHAR(255) | NO | — | YES | Email address from registration (where OTP sent) |

#### Signing/Audit Columns (3)
| Column | Type | Nullable | Default | Index | Purpose |
|--------|------|----------|---------|-------|---------|
| `signed_at` | DATETIME(6) | YES | NULL | NO | Timestamp of successful signature |
| `ip_address` | VARCHAR(45) | YES | NULL | NO | Client IP at signing (IPv4/IPv6, max 45 chars) |
| `user_agent` | LONGTEXT | YES | NULL | NO | HTTP User-Agent header at signing time |

#### OTP State Columns (5)
| Column | Type | Nullable | Default | Index | Purpose |
|--------|------|----------|---------|-------|---------|
| `otp_code` | VARCHAR(10) | YES | NULL | NO | Current 6-digit OTP (cleared after use) |
| `otp_expires_at` | DATETIME(6) | YES | NULL | NO | Expiry time of current OTP (10 min TTL) |
| `otp_attempts` | INT | NO | 0 | NO | Failed attempts count (max 3 then lockout) |
| `otp_sent_at` | DATETIME(6) | YES | NULL | NO | Timestamp of last OTP send (resend cooldown ref) |
| `otp_send_count` | INT | NO | 0 | NO | Total sends for this agreement (max 5) |

#### Timestamp Columns (2) — from TimestampMixin
| Column | Type | Nullable | Default | Index | Purpose |
|--------|------|----------|---------|-------|---------|
| `created_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP | NO | Row creation (when approval triggered) |
| `updated_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP, ON UPDATE | NO | Last modification timestamp |

---

## Index Summary

| Index Name | Type | Columns | Purpose |
|-----------|------|---------|---------|
| `PRIMARY` | PRIMARY KEY | `id` | Row identity |
| `ix_partner_agreements_agreement_no` | UNIQUE | `agreement_no` | Enforce unique agreement references |
| `ix_partner_agreements_access_token` | UNIQUE | `access_token` | Enforce unique public URLs |
| `ix_partner_agreements_registration_id` | INDEX | `registration_id` | FK lookups, admin review page |
| `ix_partner_agreements_email` | INDEX | `email` | Partner lookups by email |

---

## Data Flow & Lifecycle

### Column Usage by Phase

**Phase 1: Approval (Admin Action)**
- `registration_id`, `agreement_no`, `access_token`, `agreement_version`, `email` → set
- `created_at` → auto-set
- `otp_*` → all NULL/0

**Phase 2: OTP Request (Partner Action)**
- `otp_code`, `otp_expires_at`, `otp_sent_at`, `otp_send_count` → updated
- `otp_attempts` → reset to 0

**Phase 3: OTP Entry (Partner Action)**
- `otp_attempts` → incremented on failure
- `otp_code`, `otp_expires_at` → cleared on success

**Phase 4: Signing (OTP Success)**
- `signed_at`, `ip_address`, `user_agent` → set
- `otp_code` → cleared
- `updated_at` → auto-updated

---

## Foreign Key Relationship

```
partner_agreements.registration_id
    ↓ (FK)
partner_registrations.id
```

- **Constraint:** `fk_partner_agreements_registration_id`
- **On Delete:** RESTRICT (prevent deletion of active registrations)
- **On Update:** CASCADE (if registration.id changes, cascade the update)

---

## Constraints & Validation Rules

| Field | Rule | Implementation |
|-------|------|-----------------|
| `otp_code` | 6 digits only | VARCHAR(10), validated in service layer |
| `otp_attempts` | Max 3 failures | Checked in `partner_agreement.py:verify_otp()` |
| `otp_send_count` | Max 5 sends | Checked in `partner_agreements_public.py` |
| `access_token` | Unique URL-safe | Generated with `secrets.token_urlsafe(32)` |
| `agreement_no` | Unique per agreement | Generated sequentially AGR-YYYY-XXXXX |
| `ip_address` | IPv4/IPv6 format | Max 45 chars (IPv6 + ports) |

---

## Size & Storage Estimates

| Column | Size | Notes |
|--------|------|-------|
| `id` | 4 bytes | AUTO_INCREMENT |
| `registration_id` | 4 bytes | INT UNSIGNED |
| `agreement_no` | ~30 bytes | AGR-2026-00001 (50 char max) |
| `agreement_version` | ~3 bytes | '1.0' (10 char max) |
| `access_token` | ~50 bytes | 64 char max |
| `email` | ~100 bytes | 255 char max |
| `signed_at` | 6 bytes | DATETIME(6) |
| `ip_address` | ~20 bytes | 45 char max |
| `user_agent` | ~500 bytes avg | LONGTEXT |
| `otp_code` | ~6 bytes | VARCHAR(10) |
| `otp_expires_at` | 6 bytes | DATETIME(6) |
| `otp_attempts` | 4 bytes | INT |
| `otp_sent_at` | 6 bytes | DATETIME(6) |
| `otp_send_count` | 4 bytes | INT |
| `created_at` | 6 bytes | DATETIME(6) |
| `updated_at` | 6 bytes | DATETIME(6) |
| **Per Row** | **~760 bytes** | Excluding user_agent variations |

---

## Query Performance Notes

### Fast Lookups (Indexed)
- Get agreement by `access_token` (public page load)
- Get agreement by `agreement_no` (reference lookup)
- Get agreement by `registration_id` (admin review page)
- Get agreement by `email` (email audit log)

### Slow Queries (Unindexed — avoid)
- Filter by `signed_at` range (scan required, add index if reporting needed)
- Filter by `otp_send_count` (scan required, add index for analytics)

---

## Backward Compatibility

✅ **No existing tables modified today.** Only addition.

✅ **No changes to partner_registrations table structure.**

✅ **No breaking changes to existing APIs.**

---

## Related Files Created/Modified

### Backend
- **Model:** `api/app/models/partner_agreement.py` (NEW)
- **Service:** `api/app/services/partner_agreement.py` (NEW)
- **Router:** `api/app/routers/partner_agreements_public.py` (NEW)
- **Schema:** `api/app/schemas/partner_agreement.py` (NEW)
- **Migration:** `api/alembic/versions/0037_partner_agreements.py` (NEW)
- **Email Service:** `api/app/services/email_service.py` (MODIFIED — 3 new functions)
- **Router:** `api/app/routers/partner_registrations.py` (MODIFIED — integrated with agreement flow)

### Frontend
- **Component:** `ui/src/pages/partners/PartnerAgreementSign.jsx` (NEW)
- **API Client:** `ui/src/api/partnerAgreementPublic.js` (NEW)
- **API Client:** `ui/src/api/partnerRegistrations.js` (MODIFIED — added agreement method)
- **Component:** `ui/src/pages/partners/PartnerRegistrationReview.jsx` (MODIFIED — agreement panel)
- **Routes:** `ui/src/App.jsx` (MODIFIED — new route)

### Templates
- `api/app/templates/email/partner_agreement_invite.html` (NEW)
- `api/app/templates/email/partner_agreement_otp.html` (NEW)
- `api/app/templates/email/partner_agreement_signed.html` (NEW)

### Database
- `database/migrations/0037_partner_agreements.sql` (NEW — raw SQL version)

---

## Testing Checklist

- [ ] Table created successfully in MySQL
- [ ] Foreign key constraint works
- [ ] Unique constraints enforced (agreement_no, access_token)
- [ ] Indexes created and queryable
- [ ] Timestamps auto-populated (created_at, updated_at)
- [ ] OTP flow: send → expire → verify lifecycle
- [ ] Replay protection: signed_at set prevents re-OTP
- [ ] Resend cooldown: 30-second gate enforced
- [ ] Max attempts: 3 failures lock OTP
- [ ] Max sends: 5 sends prevent DOS

---

**Migration applied:** ✅ 2026-09-08 18:13 UTC  
**Schema version:** 0037  
**Total new columns:** 16  
**Total new tables:** 1
