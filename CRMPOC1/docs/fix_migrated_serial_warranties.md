## Fixing Missing Warranty Information for Migrated Serials in PROD

### Context

Some serials migrated from the legacy system (e.g. `IDCACEZI24091301498`) show **no warranty information in the PROD UI**, even though their legacy warranty end-dates exist in the serial history.

Example API response for `/api/serials/{serial_no}/history`:

```json
"pcb_warranty_years": null,
"component_warranty_years": null,
"machine_warranty_years": null,
"pcb_warranty_date": null,
"component_warranty_date": null,
"machine_warranty_date": null
```

At the same time, there is a `migration / legacy_serial_recovery` event whose `metadata_json` contains fields like:

```json
"pcb_warrantyupto":   "2025-11-28",
"comp_warrantyupto":  "2034-11-28",
"machin_warrantyupto": "2025-11-28"
```

The **root cause** is that the legacy warranty end-dates are stored only in the history event metadata and were **not** populated into the new `order_items` warranty-year columns that the API and UI use:

- `order_items.pcb_warranty_years`
- `order_items.component_warranty_years`
- `order_items.machine_warranty_years`

`/api/serials/{serial_no}/history` computes warranty dates only from these columns and the order dates.

### Relevant Backend Logic

From `CRMPOC1/api/app/routers/serials.py`:

```python
warranty_base = order.actual_delivery_date or order.expected_delivery_date or order.order_date

header = SerialHistoryHeader(
    ...
    pcb_warranty_years=item.pcb_warranty_years,
    component_warranty_years=item.component_warranty_years,
    machine_warranty_years=item.machine_warranty_years,
    pcb_warranty_date=_add_years(warranty_base, item.pcb_warranty_years),
    component_warranty_date=_add_years(warranty_base, item.component_warranty_years),
    machine_warranty_date=_add_years(warranty_base, item.machine_warranty_years),
)
```

```python
def _add_years(base_date: date | None, years: int | None) -> date | None:
    if base_date is None or years is None:
        return None
    try:
        return base_date.replace(year=base_date.year + years)
    except ValueError:
        # Handle leap-day rollover consistently for non-leap target years.
        return base_date.replace(month=2, day=28, year=base_date.year + years)
```

So, if any of the three `*_warranty_years` fields is `NULL`, the corresponding warranty date will be `NULL` in the API response. The front-end then shows no warranty.

### Goal

Provide **DB scripts and a process** that a DBA / infra engineer can run in PROD to:

1. Back up relevant data.
2. Identify all migrated serials with legacy warranty end-dates in `serial_history_events.metadata_json`.
3. For each such serial:
   - Find the related `order_items` row.
   - Determine the base date from the corresponding `orders` row.
   - Derive `pcb_warranty_years`, `component_warranty_years`, `machine_warranty_years` from the legacy `*_warrantyupto` dates.
   - Update the `order_items` row.
4. Validate that `/api/serials/{serial_no}/history` now returns non-null warranty data.

> NOTE: The scripts below are written for **SQL Server** (T-SQL) because the application connects using `pyodbc`. Adjust syntax if PROD uses a different RDBMS.

---

## 1. Safety: Backup and Scope

**Strongly recommended before running this in PROD:**

1. Take a full DB backup or at least back up the affected tables (`order_items`, `orders`, `serial_history_events`).
2. Execute this first in a **staging** environment using a recent PROD copy.

### 1.1. Quick Backup of Affected Rows (Optional but Recommended)

```sql
-- Backup tables (minimal, row-level) for serial history and order items

SELECT * INTO serial_history_events_backup_YYYYMMDD
FROM serial_history_events;

SELECT * INTO order_items_backup_YYYYMMDD
FROM order_items;
```

Replace `YYYYMMDD` with the current date.

---

## 2. Identify Migrated Serials with Legacy Warranty Dates

Migrated serials are recorded as events in `serial_history_events` with:

- `event_type = 'migration'`
- `event_subtype = 'legacy_serial_recovery'`

The legacy warranty dates live in `metadata_json` with keys:

- `pcb_warrantyupto`
- `comp_warrantyupto`
- `machin_warrantyupto`

### 2.1. Inspect a Sample of Such Events

```sql
SELECT TOP 50
    id,
    serial_no,
    event_at,
    event_type,
    event_subtype,
    metadata_json
FROM serial_history_events
WHERE event_type = 'migration'
  AND event_subtype = 'legacy_serial_recovery'
ORDER BY event_at DESC;
```

Verify that `metadata_json` contains the expected legacy fields (e.g. the example serial `IDCACEZI24091301498`).

---

## 3. Deriving Warranty-Year Values

### 3.1. Business Rule

For each migrated serial:

1. **Base date** (call it `warranty_base`) is:
   - `orders.actual_delivery_date`, if not null
   - else `orders.expected_delivery_date`, if not null
   - else `orders.order_date`.

2. Legacy warranty end-dates come from `metadata_json`:
   - `pcb_warrantyupto`
   - `comp_warrantyupto`
   - `machin_warrantyupto`

3. Warranty years are the whole-year difference between these dates and `warranty_base`.

   **Example formula (T-SQL):**

   ```sql
   DATEDIFF(YEAR, warranty_base, pcb_warrantyupto)
   ```

   You may choose to clamp negative or zero values to 0 or 1, depending on business rules.

> IMPORTANT: Confirm with business/functional owners what the standard warranty durations should be (e.g. PCB 1 year, Components 10 years, Machine 1 year). If they are fixed, you can skip date-diff logic and directly set constants.

---

## 4. Bulk Update Script (T-SQL, SQL Server)

The script below:

1. Extracts migrated serials and their legacy warranty end-dates from `serial_history_events.metadata_json`.
2. Joins them with `order_items` by serial number (`serial_no` or `serial_no_2`).
3. Joins with `orders` to get the warranty base date.
4. Computes the year differences.
5. Updates `order_items` for rows where warranty-year fields are **currently NULL**.

> NOTE: This assumes `metadata_json` is stored as a JSON text column and SQL Server 2016+ JSON functions are available (`JSON_VALUE`). If your schema is different, adjust accordingly.

### 4.1. Dry-Run: Preview What Will Be Updated

```sql
-- DRY RUN: no updates, just preview the computed warranty years.

WITH MigratedSerials AS (
    SELECT
        she.id AS history_event_id,
        she.serial_no,
        she.metadata_json,
        TRY_CONVERT(date, JSON_VALUE(she.metadata_json, '$.pcb_warrantyupto'), 120)    AS pcb_warrantyupto,
        TRY_CONVERT(date, JSON_VALUE(she.metadata_json, '$.comp_warrantyupto'), 120)   AS comp_warrantyupto,
        TRY_CONVERT(date, JSON_VALUE(she.metadata_json, '$.machin_warrantyupto'), 120) AS machin_warrantyupto
    FROM serial_history_events she
    WHERE she.event_type = 'migration'
      AND she.event_subtype = 'legacy_serial_recovery'
),
OrderJoin AS (
    SELECT
        ms.history_event_id,
        ms.serial_no,
        ms.pcb_warrantyupto,
        ms.comp_warrantyupto,
        ms.machin_warrantyupto,
        oi.id              AS order_item_id,
        oi.order_id,
        oi.serial_no       AS oi_serial_no,
        oi.serial_no_2     AS oi_serial_no_2,
        COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date) AS warranty_base,
        o.order_no
    FROM MigratedSerials ms
    JOIN order_items oi
        ON  LOWER(oi.serial_no)   = LOWER(ms.serial_no)
        OR  LOWER(oi.serial_no_2) = LOWER(ms.serial_no)
    JOIN orders o
        ON o.id = oi.order_id
),
ComputedYears AS (
    SELECT
        oj.*,
        CASE
            WHEN oj.warranty_base IS NULL OR oj.pcb_warrantyupto IS NULL THEN NULL
            ELSE DATEDIFF(YEAR, oj.warranty_base, oj.pcb_warrantyupto)
        END AS pcb_warranty_years_computed,
        CASE
            WHEN oj.warranty_base IS NULL OR oj.comp_warrantyupto IS NULL THEN NULL
            ELSE DATEDIFF(YEAR, oj.warranty_base, oj.comp_warrantyupto)
        END AS comp_warranty_years_computed,
        CASE
            WHEN oj.warranty_base IS NULL OR oj.machin_warrantyupto IS NULL THEN NULL
            ELSE DATEDIFF(YEAR, oj.warranty_base, oj.machin_warrantyupto)
        END AS machine_warranty_years_computed
    FROM OrderJoin oj
)
SELECT TOP 200
    history_event_id,
    serial_no,
    order_item_id,
    order_id,
    order_no,
    warranty_base,
    pcb_warrantyupto,
    comp_warrantyupto,
    machin_warrantyupto,
    pcb_warranty_years_computed,
    comp_warranty_years_computed,
    machine_warranty_years_computed
FROM ComputedYears
ORDER BY history_event_id DESC;
```

Review this output with stakeholders to ensure the computed year counts are acceptable.

### 4.2. Bulk Update (Once Validated)

```sql
BEGIN TRAN;

WITH MigratedSerials AS (
    SELECT
        she.id AS history_event_id,
        she.serial_no,
        she.metadata_json,
        TRY_CONVERT(date, JSON_VALUE(she.metadata_json, '$.pcb_warrantyupto'), 120)    AS pcb_warrantyupto,
        TRY_CONVERT(date, JSON_VALUE(she.metadata_json, '$.comp_warrantyupto'), 120)   AS comp_warrantyupto,
        TRY_CONVERT(date, JSON_VALUE(she.metadata_json, '$.machin_warrantyupto'), 120) AS machin_warrantyupto
    FROM serial_history_events she
    WHERE she.event_type = 'migration'
      AND she.event_subtype = 'legacy_serial_recovery'
),
OrderJoin AS (
    SELECT
        ms.history_event_id,
        ms.serial_no,
        ms.pcb_warrantyupto,
        ms.comp_warrantyupto,
        ms.machin_warrantyupto,
        oi.id              AS order_item_id,
        oi.order_id,
        oi.serial_no       AS oi_serial_no,
        oi.serial_no_2     AS oi_serial_no_2,
        COALESCE(o.actual_delivery_date, o.expected_delivery_date, o.order_date) AS warranty_base,
        o.order_no,
        oi.pcb_warranty_years,
        oi.component_warranty_years,
        oi.machine_warranty_years
    FROM MigratedSerials ms
    JOIN order_items oi
        ON  LOWER(oi.serial_no)   = LOWER(ms.serial_no)
        OR  LOWER(oi.serial_no_2) = LOWER(ms.serial_no)
    JOIN orders o
        ON o.id = oi.order_id
),
ComputedYears AS (
    SELECT
        oj.*,
        CASE
            WHEN oj.warranty_base IS NULL OR oj.pcb_warrantyupto IS NULL THEN NULL
            ELSE DATEDIFF(YEAR, oj.warranty_base, oj.pcb_warrantyupto)
        END AS pcb_warranty_years_computed,
        CASE
            WHEN oj.warranty_base IS NULL OR oj.comp_warrantyupto IS NULL THEN NULL
            ELSE DATEDIFF(YEAR, oj.warranty_base, oj.comp_warrantyupto)
        END AS comp_warranty_years_computed,
        CASE
            WHEN oj.warranty_base IS NULL OR oj.machin_warrantyupto IS NULL THEN NULL
            ELSE DATEDIFF(YEAR, oj.warranty_base, oj.machin_warrantyupto)
        END AS machine_warranty_years_computed
    FROM OrderJoin oj
)
UPDATE oi
SET
    oi.pcb_warranty_years       = cy.pcb_warranty_years_computed,
    oi.component_warranty_years = cy.comp_warranty_years_computed,
    oi.machine_warranty_years   = cy.machine_warranty_years_computed
FROM order_items oi
JOIN ComputedYears cy ON cy.order_item_id = oi.id
WHERE
    -- Only update records where we computed non-null warranties
    (cy.pcb_warranty_years_computed IS NOT NULL
     OR cy.comp_warranty_years_computed IS NOT NULL
     OR cy.machine_warranty_years_computed IS NOT NULL)
    -- And current values are still NULL (so we do not override any manually maintained data)
    AND oi.pcb_warranty_years       IS NULL
    AND oi.component_warranty_years IS NULL
    AND oi.machine_warranty_years   IS NULL;

-- Inspect how many rows were affected
SELECT @@ROWCOUNT AS UpdatedOrderItemsCount;

-- OPTIONAL: Inspect a few updated rows
SELECT TOP 50
    id,
    order_id,
    serial_no,
    serial_no_2,
    pcb_warranty_years,
    component_warranty_years,
    machine_warranty_years
FROM order_items
WHERE pcb_warranty_years IS NOT NULL
   OR component_warranty_years IS NOT NULL
   OR machine_warranty_years IS NOT NULL
ORDER BY id DESC;

-- If everything looks good:
-- COMMIT TRAN;
-- Otherwise:
-- ROLLBACK TRAN;
```

> IMPORTANT: Do not forget to explicitly `COMMIT` or `ROLLBACK` the transaction after reviewing the results.

---

## 5. Post-Deployment Validation

After running the bulk update and committing:

1. Pick a few known migrated serials (including `IDCACEZI24091301498`).
2. Call the API in PROD:

   - `GET /api/serials/{serial_no}/history`

3. Verify in the JSON response:

   - `header.pcb_warranty_years` is non-null (and matches expectations).
   - `header.component_warranty_years` is non-null.
   - `header.machine_warranty_years` is non-null.
   - `header.pcb_warranty_date`, `header.component_warranty_date`, `header.machine_warranty_date` are non-null and reasonable.

4. Open the PROD UI serial lookup / history page for those serials and confirm that warranty information is now visible.

---

## 6. Optional: Code Safeguards for Future Migrations

Even after data is corrected, it is advisable to protect against similar issues in future migrations:

1. **Migration scripts** should not only create `legacy_serial_recovery` events but also populate:
   - `order_items.pcb_warranty_years`
   - `order_items.component_warranty_years`
   - `order_items.machine_warranty_years`
   based on the legacy end-dates and order base date.

2. Alternatively, `get_serial_history` could be enhanced to **fallback** to legacy `*_warrantyupto` dates from the latest `legacy_serial_recovery` event when the `*_warranty_years` are null. However, this adds runtime complexity and should be carefully designed.

For now, the DB fix described in this document will restore warranty display for migrated serials in PROD.
