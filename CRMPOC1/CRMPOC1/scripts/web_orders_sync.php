<?php
/**
 * Sends the website's orders to the CRM (Web Orders). Runs on the website server, every minute, from cron:
 *
 *   * * * * * php /var/www/indcool.in/crm_sync/web_orders_sync.php >> /var/www/indcool.in/crm_sync/sync.log 2>&1
 *
 * It only READS the website database (orders, order_items, order_addresses, payment_logs) and never changes the website.
 * Every run sends the orders that changed in the last few minutes (and everything since the last good run, so a CRM
 * outage is caught up), plus one sweep of the last 3 days at the start of every hour. The CRM saves each order again
 * safely, so sending one twice does no harm.
 *
 *   php web_orders_sync.php            normal run
 *   php web_orders_sync.php --all      send every order once (the first run, or to repair)
 *   php web_orders_sync.php --minutes=600   send what changed in the last 600 minutes
 *
 * Settings: crm_sync.env next to this file (CRM_URL, CRM_KEY, SITE_ROOT). The database login is read from the
 * website's own .env.
 */
declare(strict_types=1);

date_default_timezone_set('Asia/Kolkata');
$dir = __DIR__;
$lock = fopen($dir . '/sync.lock', 'c');
if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) {
    exit(0); // the previous run is still going
}

function line(string $m): void { echo date('Y-m-d H:i:s') . ' ' . $m . PHP_EOL; }

$cfg = @parse_ini_file($dir . '/crm_sync.env', false, INI_SCANNER_RAW);
if (!$cfg || empty($cfg['CRM_URL']) || empty($cfg['CRM_KEY']) || empty($cfg['SITE_ROOT'])) { line('crm_sync.env is missing CRM_URL, CRM_KEY or SITE_ROOT'); exit(2); }
$crmUrl = rtrim(trim($cfg['CRM_URL']), '/') . '/api/web-orders/ingest';
$crmKey = trim($cfg['CRM_KEY'], " \t\"'");

$env = [];
foreach (@file(rtrim($cfg['SITE_ROOT'], '/') . '/.env', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [] as $l) {
    if ($l[0] === '#' || strpos($l, '=') === false) continue;
    [$k, $v] = explode('=', $l, 2);
    $env[trim($k)] = trim($v, " \t\"'");
}
try {
    $pdo = new PDO(sprintf('mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4', $env['DB_HOST'] ?? 'localhost', $env['DB_PORT'] ?? '3306', $env['DB_DATABASE'] ?? ''),
        $env['DB_USERNAME'] ?? '', $env['DB_PASSWORD'] ?? '', [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
} catch (Throwable $e) { line('cannot open the website database: ' . $e->getMessage()); exit(3); }

$state = $dir . '/last_ok.txt';
$lastOk = is_file($state) ? (int)trim((string)file_get_contents($state)) : 0;
$all = in_array('--all', $argv ?? [], true);
$minutes = 20;
foreach ($argv ?? [] as $a) if (preg_match('/^--minutes=(\d+)$/', $a, $m)) $minutes = (int)$m[1];
if ($lastOk) $minutes = max($minutes, (int)ceil((time() - $lastOk) / 60) + 5);   // catch up after an outage
if ((int)date('i') === 0) $minutes = max($minutes, 4320);                         // hourly sweep of the last 3 days
$since = date('Y-m-d H:i:s', time() - $minutes * 60);

if ($all) {
    $ids = array_column($pdo->query('SELECT id FROM orders ORDER BY id')->fetchAll(), 'id');
} else {
    $sql = 'SELECT id FROM orders WHERE updated_at >= :t OR created_at >= :t'
        . ' UNION SELECT order_id FROM order_items WHERE updated_at >= :t OR created_at >= :t'
        . ' UNION SELECT order_id FROM order_addresses WHERE updated_at >= :t OR created_at >= :t'
        . ' UNION SELECT order_id FROM payment_logs WHERE updated_at >= :t OR created_at >= :t';
    $st = $pdo->prepare($sql);
    $st->execute([':t' => $since]);
    $ids = array_column($st->fetchAll(), 'id');
}
sort($ids);

function post(string $url, string $key, array $orders): array {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 60, CURLOPT_CONNECTTIMEOUT => 15,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'X-Web-Orders-Key: ' . $key],
        CURLOPT_POSTFIELDS => json_encode(['orders' => $orders], JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE),
    ]);
    $body = curl_exec($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $err = curl_error($ch);
    curl_close($ch);
    return [$code, (string)$body, $err];
}

$sent = $created = $updated = $failed = 0;
$ok = true;
if (!$ids) {
    [$code, $body, $err] = post($crmUrl, $crmKey, []);   // nothing changed: still tell the CRM that the sync is alive
    if ($code !== 200) { line("heartbeat refused: HTTP $code $err " . substr($body, 0, 200)); $ok = false; }
}
foreach (array_chunk($ids, 40) as $chunk) {
    $in = implode(',', array_map('intval', $chunk));
    $orders = $pdo->query("SELECT * FROM orders WHERE id IN ($in)")->fetchAll();
    $by = [];
    foreach ($orders as $o) { $o['items'] = []; $o['addresses'] = []; $o['payments'] = []; $by[$o['id']] = $o; }
    foreach ($pdo->query("SELECT * FROM order_items WHERE order_id IN ($in) ORDER BY id")->fetchAll() as $r) {
        if (isset($r['product_info']) && is_string($r['product_info'])) { $d = json_decode($r['product_info'], true); if ($d !== null) $r['product_info'] = $d; }
        $by[$r['order_id']]['items'][] = $r;
    }
    foreach ($pdo->query("SELECT * FROM order_addresses WHERE order_id IN ($in) ORDER BY id")->fetchAll() as $r) $by[$r['order_id']]['addresses'][] = $r;
    foreach ($pdo->query("SELECT * FROM payment_logs WHERE order_id IN ($in) ORDER BY id")->fetchAll() as $r) {
        if (isset($r['response'])) $r['response'] = mb_substr((string)$r['response'], 0, 1500);
        $by[$r['order_id']]['payments'][] = $r;
    }
    [$code, $body, $err] = post($crmUrl, $crmKey, array_values($by));
    if ($code !== 200) { line("CRM refused a batch: HTTP $code $err " . substr($body, 0, 200)); $ok = false; break; }
    $res = json_decode($body, true) ?: [];
    $sent += count($by); $created += (int)($res['created'] ?? 0); $updated += (int)($res['updated'] ?? 0); $failed += (int)($res['failed'] ?? 0);
    if (!empty($res['errors'])) line('CRM could not save: ' . implode(' | ', $res['errors']));
}
if ($ok) file_put_contents($state, (string)time());
if ($ids || !$ok) line(sprintf('%s: sent %d order(s), %d new, %d updated, %d failed (looking back %d min%s)', $ok ? 'ok' : 'STOPPED', $sent, $created, $updated, $failed, $minutes, $all ? ', all orders' : ''));
if (is_file($dir . '/sync.log') && filesize($dir . '/sync.log') > 2000000) file_put_contents($dir . '/sync.log', '');
exit($ok ? 0 : 1);
