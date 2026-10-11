# Marketing

Its own database (`indcool_marketing`), separate from the CRM and from Sales. Linked to them only by user ids and
reference numbers. Off while `MARKETING_DATABASE_URL` is empty.

Release 1 (this one): the role `marketing`, the user tick `can_manage_marketing`, the Marketing menu, the ticks inside
Marketing (by kind of person and by person, with a history), and the settings. Contacts, consent, audiences,
campaigns, templates and channels come in the next releases.

## Switch it on (once, on the server)

1. Create the database and its own MySQL user (type the password yourself, do not share it):

```sql
CREATE DATABASE indcool_marketing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'indcool_mk'@'localhost' IDENTIFIED BY 'TYPE-A-STRONG-PASSWORD';
GRANT ALL PRIVILEGES ON indcool_marketing.* TO 'indcool_mk'@'localhost';
FLUSH PRIVILEGES;
```

2. Add one line to the server `api/.env`:

```
MARKETING_DATABASE_URL=mysql+mysqlconnector://indcool_mk:THE-SAME-PASSWORD@localhost/indcool_marketing
```

3. Deploy as usual: the deploy script upgrades the Marketing database (`alembic_marketing.ini`) when the line is set.

## Who has the menu

Admin and Sub Admin always; the role `marketing`; anyone whose user has "Can manage marketing" ticked. Engineers and
vendors never.
