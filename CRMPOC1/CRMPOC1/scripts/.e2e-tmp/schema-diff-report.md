# DB Schema Comparison (Actionable)

Generated: 2026-09-12T08:31:35.929828+00:00

## Summary

| Check | Local | Production |
|-------|-------|------------|
| Alembic | `0037_partner_agreements` | `0037_partner_agreements` |
| Tables missing on prod | 0 | |
| Columns missing on prod | 0 | |
| Actionable type issues | 0 | |
| Review-only drift (defaults/nullable) | 26 | |
| Cosmetic differences (ignored) | 86 | |
| **Needs migration** | **NO** | |

## Result

Production schema is aligned with local for tables/columns. No column migration required.

Cosmetic differences (datetime precision, text vs longtext, wider varchar on prod) were ignored.

## Review-only drift (no migration required)

These are legacy default/nullable differences. The application sets values in code.

- `calls.call_datetime`: local `datetime(6)` / prod `datetime`
- `calls.customer_name`: local `varchar(255)` / prod `varchar(255)`
- `calls.priority`: local `varchar(20)` / prod `varchar(50)`
- `calls.status`: local `varchar(30)` / prod `varchar(50)`
- `claims.status`: local `varchar(50)` / prod `varchar(50)`
- `complaints.send_sms`: local `tinyint(1)` / prod `tinyint(1)`
- `complaints.source`: local `varchar(50)` / prod `varchar(50)`
- `complaints.status`: local `varchar(50)` / prod `varchar(50)`
- `installation_requests.status`: local `varchar(50)` / prod `varchar(50)`
- `order_items.free_service_count`: local `int` / prod `int`
- `order_items.installation_status`: local `varchar(50)` / prod `varchar(50)`
- `order_items.item_qty`: local `int` / prod `int`
- `order_items.service_consume_count`: local `int` / prod `int`
- `orders.status`: local `varchar(50)` / prod `varchar(50)`
- `permissions.can_create`: local `tinyint(1)` / prod `tinyint(1)`
- ... and 11 more (see schema-diff.json)

