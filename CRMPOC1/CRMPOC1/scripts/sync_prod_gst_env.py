from pathlib import Path

src_path = Path("/tmp/indcool_local_gst.env")
dst_path = Path("/var/www/indcool/api/.env")

keys = {
    "GST_LOOKUP_ENABLED",
    "GST_PROVIDER_URL",
    "GST_PROVIDER_API_KEY",
    "GST_PROVIDER_API_SECRET",
    "GST_PROVIDER_AUTHORIZATION",
}

source_values: dict[str, str] = {}
for raw_line in src_path.read_text(encoding="utf-8").splitlines():
    if "=" not in raw_line or raw_line.lstrip().startswith("#"):
        continue
    key, value = raw_line.split("=", 1)
    key = key.strip()
    if key in keys:
        source_values[key] = value.strip()

required = {
    "GST_LOOKUP_ENABLED",
    "GST_PROVIDER_URL",
    "GST_PROVIDER_API_KEY",
    "GST_PROVIDER_API_SECRET",
}
missing = sorted(key for key in required if not source_values.get(key))
if missing:
    raise SystemExit(f"Missing required GST env values: {', '.join(missing)}")

existing_lines = dst_path.read_text(encoding="utf-8").splitlines()
updated_lines: list[str] = []
seen: set[str] = set()

for raw_line in existing_lines:
    if "=" not in raw_line or raw_line.lstrip().startswith("#"):
        updated_lines.append(raw_line)
        continue
    key, _ = raw_line.split("=", 1)
    key = key.strip()
    if key in keys:
        updated_lines.append(f"{key}={source_values.get(key, '')}")
        seen.add(key)
    else:
        updated_lines.append(raw_line)

missing_from_dest = [key for key in sorted(keys) if key not in seen and key in source_values]
if missing_from_dest:
    if updated_lines and updated_lines[-1].strip():
        updated_lines.append("")
    updated_lines.append("# GST live lookup")
    for key in missing_from_dest:
        updated_lines.append(f"{key}={source_values[key]}")

backup_path = dst_path.with_name(".env.backup-gst-20260919")
backup_path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")
dst_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

print(f"backup={backup_path}")
print("updated_keys=" + ",".join(sorted(key for key in keys if key in source_values)))
