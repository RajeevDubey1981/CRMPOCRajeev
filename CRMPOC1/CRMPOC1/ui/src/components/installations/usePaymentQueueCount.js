import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client.js";

/** How many installation payments are sitting at the viewer's own stage right now -- refreshed
 * every minute, and right after an action in the queue itself (see payment-queue-changed below). */
export default function usePaymentQueueCount(enabled) {
  const [count, setCount] = useState(0);

  const reload = useCallback(() => {
    if (!enabled) return;
    api.get("/api/dashboard/my-payment-queue").then((r) => setCount(r.data.length)).catch(() => {});
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return undefined;
    reload();
    const timer = setInterval(reload, 60000);
    window.addEventListener("payment-queue-changed", reload);
    return () => {
      clearInterval(timer);
      window.removeEventListener("payment-queue-changed", reload);
    };
  }, [enabled, reload]);

  return enabled ? count : 0;
}
