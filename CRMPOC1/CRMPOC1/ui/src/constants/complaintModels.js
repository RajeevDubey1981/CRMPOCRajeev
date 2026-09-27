/** Keep in sync with api/app/data/complaint_models.py — client fallback if API is empty. */
export const COMPLAINT_MODEL_FALLBACK = [
  { id: -1, item_code: "IDC-CM-WAC", item_name: "Window AC" },
  { id: -2, item_code: "IDC-CM-SAC", item_name: "Split AC" },
  { id: -3, item_code: "IDC-CM-FRG", item_name: "Fridge" },
  { id: -4, item_code: "IDC-CM-GYS", item_name: "Geyser" },
  { id: -5, item_code: "IDC-CM-WCL", item_name: "Water Cooler" },
  { id: -6, item_code: "IDC-CM-ACL", item_name: "Air Cooler" },
];

export function mergeComplaintModelOptions(apiRows) {
  const map = new Map();
  COMPLAINT_MODEL_FALLBACK.forEach((row) => map.set(row.item_name, row));
  (apiRows || []).forEach((row) => {
    if (row?.item_name) map.set(row.item_name, row);
  });
  return [...map.values()].sort((a, b) => a.item_name.localeCompare(b.item_name));
}
