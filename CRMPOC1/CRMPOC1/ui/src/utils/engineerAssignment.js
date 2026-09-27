/** Compare engineer/user ids from API (number) vs auth state (may be string). */
export function engineerIdsMatch(a, b) {
  if (a == null || b == null) return false;
  return Number(a) === Number(b);
}

export function formatEngineerOptionLabel(engineer) {
  const name = engineer?.name || "Engineer";
  const pending = Number(engineer?.pending_requests ?? 0);
  const rating = Number(engineer?.rating ?? 0);
  return `${name} | Pending: ${pending} | Rating: ${rating.toFixed(1)}/5`;
}

export const ENGINEER_ASSIGNMENT_HINT =
  "Pending shows active assigned requests across installations, services, and complaints. Rating is calculated from completed vs returned/rejected installation jobs.";
