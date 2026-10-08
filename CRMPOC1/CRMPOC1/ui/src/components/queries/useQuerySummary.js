import { useCallback, useEffect, useState } from "react";

import { queriesApi } from "../../api/queries.js";

/** The query counts for the person logged in (open, answered, new for me), refreshed every minute and when asked. */
export default function useQuerySummary() {
  const [summary, setSummary] = useState(null);
  const reload = useCallback(() => {
    queriesApi.summary().then(setSummary).catch(() => {});
  }, []);

  useEffect(() => {
    reload();
    const timer = setInterval(reload, 60000);
    window.addEventListener("queries-changed", reload);
    return () => {
      clearInterval(timer);
      window.removeEventListener("queries-changed", reload);
    };
  }, [reload]);

  return { summary, reload };
}

// the server sends UTC times without a zone mark; read them as UTC
function parseServerTime(value) {
  const text = String(value);
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(text) ? text : `${text}Z`);
}

export function timeAgo(value) {
  if (!value) return "";
  const then = parseServerTime(value);
  if (Number.isNaN(then.getTime())) return "";
  const minutes = Math.round((Date.now() - then.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} d ago`;
  return then.toLocaleDateString();
}

export const STATUS_STYLE = {
  Open: "bg-amber-100 text-amber-800",
  Answered: "bg-sky-100 text-sky-800",
  Closed: "bg-slate-200 text-slate-600",
};
