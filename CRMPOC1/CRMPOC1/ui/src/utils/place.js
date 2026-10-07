import { INDIAN_STATES } from "../constants/indianStates.js";

const ALIASES = { orissa: "Odisha", pondicherry: "Puducherry", uttaranchal: "Uttarakhand", "new delhi": "Delhi" };

/** Pin code and state found in an address text, for the boxes that are still empty. Never overwrites typed values. */
export function guessPlace(address) {
  const text = String(address || "");
  const pins = text.match(/(?<!\d)[1-9]\d{5}(?!\d)/g);
  const low = ` ${text.toLowerCase().replace(/[^a-z ]/g, " ").replace(/\s+/g, " ")} `;
  let state = "";
  for (const s of INDIAN_STATES) {
    if (low.includes(` ${s.toLowerCase()} `)) { state = s; break; }
  }
  if (!state) {
    for (const [alias, s] of Object.entries(ALIASES)) {
      if (low.includes(` ${alias} `)) { state = s; break; }
    }
  }
  return { pincode: pins ? pins[pins.length - 1] : "", state };
}

/** Fill only what is empty in `place` from the address text. Returns a patch (possibly empty). */
export function fillPlaceFromAddress(place, address) {
  const guess = guessPlace(address);
  const patch = {};
  if (!place?.pincode && guess.pincode) patch.pincode = guess.pincode;
  if (!place?.state && guess.state) patch.state = guess.state;
  return patch;
}
