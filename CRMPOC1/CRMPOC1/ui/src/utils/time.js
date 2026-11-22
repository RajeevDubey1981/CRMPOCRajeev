// The server stores times in UTC and sends them without a zone marker, which a browser reads as local time.
// Everything shown on screen goes through here so it always reads as Indian time.
const TZ = "Asia/Kolkata";
const HAS_ZONE = /[zZ]$|[+-]\d\d:?\d\d$/;

export function serverDate(value) {
  if (value instanceof Date) return value;
  if (typeof value === "string") {
    const s = value.trim();
    // A date with a time but no zone is UTC; a plain date (no time) is left as it is.
    if (/^\d{4}-\d\d-\d\d[T ]\d\d:\d\d/.test(s) && !HAS_ZONE.test(s)) return new Date(`${s.replace(" ", "T")}Z`);
    return new Date(s);
  }
  return new Date(value);
}

export function fmtIST(value, kind = "String", locale, opts) {
  const d = serverDate(value);
  if (Number.isNaN(d.getTime())) return "";
  const fn = kind === "Date" ? "toLocaleDateString" : kind === "Time" ? "toLocaleTimeString" : "toLocaleString";
  return d[fn](locale || "en-IN", { ...(opts || {}), timeZone: TZ });
}
