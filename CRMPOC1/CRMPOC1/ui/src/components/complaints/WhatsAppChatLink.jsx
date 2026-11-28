import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { whatsappApi } from "../../api/whatsapp.js";
import { fmtIST } from "../../utils/time.js";

// On a complaint: a link to the customer's WhatsApp chat, when there is one and the viewer may open the WhatsApp inbox.
export default function WhatsAppChatLink({ complaintId }) {
  const [chat, setChat] = useState(null);

  useEffect(() => {
    let active = true;
    whatsappApi
      .forComplaint(complaintId)
      .then((r) => { if (active && r?.conversation_id) setChat(r); })
      .catch(() => null);
    return () => { active = false; };
  }, [complaintId]);

  if (!chat) return null;
  return (
    <section className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
      <div>
        <h2 className="text-sm font-medium text-emerald-900">WhatsApp chat with this customer</h2>
        <p className="text-xs text-emerald-800">
          {chat.messages} {chat.messages === 1 ? "message" : "messages"}
          {chat.last_message_at ? ` · last on ${fmtIST(chat.last_message_at, "String", "en-IN", { dateStyle: "medium", timeStyle: "short" })}` : ""}
          {chat.status === "needs_staff" ? " · waiting for staff" : ""}
        </p>
      </div>
      <Link to={`/whatsapp?conv=${chat.conversation_id}`} className="rounded-md bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-800">
        Open the chat
      </Link>
    </section>
  );
}
