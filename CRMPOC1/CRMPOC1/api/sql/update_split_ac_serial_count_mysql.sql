UPDATE item_masters
SET serial_count = 2
WHERE item_name LIKE '%SPLIT AC%';

SELECT ROW_COUNT() AS rows_updated;

SELECT id, item_code, item_name, serial_count
FROM item_masters
WHERE item_name LIKE '%SPLIT AC%';
