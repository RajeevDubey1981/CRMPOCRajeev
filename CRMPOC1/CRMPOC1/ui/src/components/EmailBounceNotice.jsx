// Red markers for a customer email address that bounced (address not found, mailbox full, ...).

export function BounceBadge({ reason, className = "" }) {
  return (
    <span
      title={reason || "The last email to this address could not be delivered"}
      className={`inline-flex items-center gap-1 rounded-full border border-red-300 bg-red-100 px-2 py-0.5 text-[11px] font-bold text-red-700 ${className}`}
    >
      <span aria-hidden="true">&#9888;</span> Email bounced
    </span>
  );
}

export function BounceBanner({ email, reason }) {
  return (
    <div role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
      <div className="font-bold">&#9888; The email to {email || "this customer"} bounced and was not delivered.</div>
      {reason && <div className="mt-0.5 text-xs text-red-700">{reason}</div>}
      <div className="mt-1 text-xs text-red-700">
        Please check the email address with the customer and correct it (Edit), then send the link again.
      </div>
    </div>
  );
}

// Classes for a "send link / documents" button that must show red when the email bounced.
export const BOUNCED_BUTTON = "border-red-700 bg-red-600 text-white hover:bg-red-700";
