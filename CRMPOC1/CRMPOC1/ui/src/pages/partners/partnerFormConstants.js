export const INDIAN_STATES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
  "Delhi",
  "Jammu and Kashmir",
  "Ladakh",
  "Puducherry",
  "Chandigarh",
];

export const PARTNER_TYPE_GEM_ID_EXEMPT = new Set(["CSD Dealer"]);
export const CSD_PARTNER_TYPE = "CSD Dealer";
export const CSD_SHOP_PHOTO_COUNT = 5;
export const DEFAULT_SHOP_PHOTO_COUNT = 1;

export function requiredShopPhotoCount(partnerType, fallback = DEFAULT_SHOP_PHOTO_COUNT) {
  if (!partnerType) return fallback;
  return partnerType.trim() === CSD_PARTNER_TYPE ? CSD_SHOP_PHOTO_COUNT : DEFAULT_SHOP_PHOTO_COUNT;
}

export function gemSellerIdRequired(partnerType) {
  if (!partnerType) return true;
  return !PARTNER_TYPE_GEM_ID_EXEMPT.has(partnerType.trim());
}

export const EMPTY_PARTNER_FORM = {
  partner_type: "Gem Partner",
  business_type: "Proprietorship",
  name: "",
  mobile: "",
  alternate_mobile: "",
  email: "",
  website: "",
  contact_person_name: "",
  contact_designation: "",
  firm_address: "",
  city: "",
  district: "",
  state: "",
  pincode: "",
  gst_no: "",
  pan_no: "",
  udyam_no: "",
  cin_no: "",
  aadhaar_no: "",
  gem_seller_id: "",
  year_of_establishment: "",
  annual_turnover: "",
  operating_states: "",
  product_categories: "",
  bank_name: "",
  bank_branch: "",
  account_holder_name: "",
  account_number: "",
  ifsc_code: "",
  remarks: "",
  declaration_accepted: false,
};

export const PARTNER_DOCUMENTS = [
  { key: "gst_certificate", label: "GST Registration Certificate", required: true },
  { key: "pan_card", label: "PAN Card (Entity / Proprietor)", required: true },
  { key: "cancelled_cheque", label: "Cancelled Cheque / Bank Statement", required: true },
  { key: "address_proof", label: "Address Proof (Utility Bill / Rent Deed)", required: true },
  { key: "aadhaar_card", label: "Aadhaar Card (Authorized Signatory)", required: true },
  { key: "msme_certificate", label: "MSME / Udyam Certificate", required: false },
  { key: "incorporation_certificate", label: "Incorporation / Partnership Deed", required: false },
  { key: "photo", label: "Passport Size Photograph", required: false },
];

export function buildShopPhotoDocuments(count) {
  const docs = [];
  for (let i = 1; i <= count; i++) {
    docs.push({
      key: `shop_photo_${i}`,
      label: `Shop Photograph ${i}${count > 1 ? ` of ${count}` : ""}`,
      required: true,
      isShopPhoto: true,
      index: i,
    });
  }
  return docs;
}
