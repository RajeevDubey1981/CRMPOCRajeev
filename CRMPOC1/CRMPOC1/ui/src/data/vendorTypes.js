// What a vendor works as. A vendor can be several at once; anything else can be typed for one vendor.
export const VENDOR_TYPES = [
  { key: "GeM", hint: "Government e-Marketplace orders" },
  { key: "CSD", hint: "Canteen Stores Department (defence canteens)" },
  { key: "Retail", hint: "Retail customers and shops" },
  { key: "SSD", hint: "Sales Service Distributor: handles both sales and service" },
];

// The product categories of indcool.in, grouped the way the site shows them.
export const INDCOOL_CATEGORY_GROUPS = [
  { group: "Air conditioners", items: ["Residential Air Conditioners", "Commercial Air Conditioners", "Solar Air Conditioners", "Split AC", "Window AC", "Cassette AC", "Tower AC"] },
  { group: "Refrigeration and cooling", items: ["Refrigerator", "Direct Cool", "Frost Free", "Deep Freezer", "Water Cooler"] },
  { group: "Home appliances", items: ["Washing Machines", "Fans", "Geysers", "Other Appliances"] },
];
export const INDCOOL_CATEGORIES = INDCOOL_CATEGORY_GROUPS.flatMap((g) => g.items);
