import { api } from "./client.js";

// What a 6 digit pin code tells: { pincode, state, district, city, places }. Resolves to null when it is not known.
export function lookupPin(pin) {
  return api.get(`/api/places/pincode/${pin}`).then((r) => r.data).catch(() => null);
}
