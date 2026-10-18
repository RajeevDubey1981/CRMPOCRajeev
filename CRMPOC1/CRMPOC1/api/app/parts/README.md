# Parts

Its own database (`indcool_parts`), separate from the CRM, Sales and Marketing. Linked to them only by user ids,
item codes, and service/installation request numbers. Off while `PARTS_DATABASE_URL` is empty.

What it holds: the spare-parts catalogue (part name, part code, part EAN, which item codes a part fits, price,
whether engineers can see it) and one unified queue of requests raised from the field — spare part, miscellaneous
expense, on-demand (not-in-catalogue) part, whole-unit replacement — each with its approval stage, its timeline,
its mandatory proof photos, and an optional link to a Queries "discuss" thread. Also the part-warranty-swap log
(fresh vs carry-forward, recorded at the moment a part is physically changed).

## Switch it on (once, on the server)

1. Create the database and its own MySQL user (type the password yourself, do not share it):

```sql
CREATE DATABASE indcool_parts CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'indcool_pt'@'localhost' IDENTIFIED BY 'TYPE-A-STRONG-PASSWORD';
GRANT ALL PRIVILEGES ON indcool_parts.* TO 'indcool_pt'@'localhost';
FLUSH PRIVILEGES;
```

2. Add one line to the server `api/.env`:

```
PARTS_DATABASE_URL=mysql+mysqlconnector://indcool_pt:THE-SAME-PASSWORD@localhost/indcool_parts
```

3. Deploy as usual: the deploy script upgrades the Parts database (`alembic_parts.ini`) when the line is set.

## Approval chain

- Spare part / on-demand part: Service Manager approves alone up to ₹1,000; above that, Admin or Sub Admin also
  signs off.
- Miscellaneous expense: always Service Manager, then Admin or Sub Admin.
- Whole-unit replacement: always Service Manager, then Admin or Sub Admin, regardless of value.

Engineers never see amounts. Admin and Sub Admin can act at either stage.
