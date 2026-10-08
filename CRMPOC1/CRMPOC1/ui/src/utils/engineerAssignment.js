/** Compare engineer/user ids from API (number) vs auth state (may be string). */
export function engineerIdsMatch(a, b) {
  if (a == null || b == null) return false;
  return Number(a) === Number(b);
}

// how near an engineer is to the customer, as the server works it out from the customer's address
export const ENGINEER_MATCH_TEXT = { pincode: "Same pin code", area: "Same area", district: "Same district", state: "Same state" };

export function formatEngineerOptionLabel(engineer) {
  const name = engineer?.name || "Engineer";
  const pending = Number(engineer?.pending_requests ?? 0);
  const rating = Number(engineer?.rating ?? 0);
  const near = ENGINEER_MATCH_TEXT[engineer?.match];
  const pins = [engineer?.pincode, ...(engineer?.extra_pincodes || [])].filter(Boolean).join("/");
  const place = [engineer?.district, engineer?.state, pins].filter(Boolean).join(", ");
  return `${near ? `${near} | ` : ""}${name} | ${place ? `${place} | ` : ""}Pending: ${pending} | Rating: ${rating.toFixed(1)}/5`;
}

export const ENGINEER_ASSIGNMENT_HINT =
  "Pending shows active assigned requests across installations, services, and complaints. Rating is calculated from completed vs returned/rejected installation jobs.";
