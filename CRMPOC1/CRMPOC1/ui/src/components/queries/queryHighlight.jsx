// Helpers for the Queries list: yellow highlight of what was searched, and reading a typed day the way the server does.

// Shows the part of `text` that was searched in yellow.
export function Mark({ text, term }) {
  const value = String(text ?? "");
  const needle = String(term ?? "").trim();
  if (!needle || !value) return value;
  const at = value.toLowerCase().indexOf(needle.toLowerCase());
  if (at < 0) return value;
  return (
    <>
      {value.slice(0, at)}
      <mark className="rounded bg-yellow-200 px-0.5 text-slate-900">{value.slice(at, at + needle.length)}</mark>
      {value.slice(at + needle.length)}
    </>
  );
}

const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

// 15/10/2026, 15-10-2026, 2026-10-15, 15 Oct, 15 Oct 2026 -> { y (or null), m, d }, else null (same rules as the server search)
export function typedDay(text) {
  const t = String(text || "").trim().toLowerCase().replace(/\s+/g, " ");
  let m = t.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);
  if (m) return { y: +m[3], m: +m[2], d: +m[1] };
  m = t.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) return { y: +m[1], m: +m[2], d: +m[3] };
  m = t.match(/^(\d{1,2}) ([a-z]{3,9})(?: (\d{4}))?$/);
  if (m && MONTHS.includes(m[2].slice(0, 3))) return { y: m[3] ? +m[3] : null, m: MONTHS.indexOf(m[2].slice(0, 3)) + 1, d: +m[1] };
  return null;
}

// Is the day a person typed in the search box the day this query was raised ("2026-10-15")?
export function isTypedDay(term, iso) {
  const want = typedDay(term);
  const [y, m, d] = String(iso || "").split("-").map(Number);
  return !!want && !!y && want.m === m && want.d === d && (want.y == null || want.y === y);
}

// Does the text in the search box mean this query's number (QRY-0005, qry 5, or part of the number)?
export function isTypedNumber(term, no, id) {
  const t = String(term || "").trim().toLowerCase().replace(/\s+/g, " ");
  if (!t) return false;
  const m = t.match(/^qry[-\s]?0*(\d+)$/);
  if (m) return Number(m[1]) === Number(id);
  return String(no || "").toLowerCase().includes(t) && t.length >= 3;
}
