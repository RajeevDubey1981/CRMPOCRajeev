import { useEffect } from "react";

import { launchIntro } from "./parcelPack.js";

// Mount on a page to float a few courier parcels up once, when the page opens.
export default function ParcelIntro() {
  useEffect(() => launchIntro(), []);
  return null;
}
