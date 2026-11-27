import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { webOrdersApi } from "../../api/webOrders.js";
import { fmtIST } from "../../utils/time.js";
import { Badge } from "./WebOrders.jsx";

const REFRESH_MS = 20000;
const rupees = (n) => (n === null || n === undefined ? "-" : `₹${Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`);
const when = (v) => (v ? fmtIST(v, "String", "en-IN", { dateStyle: "medium", timeStyle: "short" }) : "-");

const EVENT_TEXT = {
  placed: (e) => `Order placed${e.new_value ? ` (${e.new_value})` : ""}`,
  status: (e) => `Order status changed from ${e.old_value || "none"} to ${e.new_value || "none"}`,
  payment_status: (e) => `Payment status ${e.old_value ? `changed from ${e.old_value} to` : "is"} ${e.new_value || "none"}`,
};

function Card({ title, children }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {children}
    </section>
  );
}

function Row({ k, v }) {
  if (v === null || v === undefined || v === "") return null;
  return <div className="flex justify-between gap-3 py-0.5 text-sm"><span className="text-slate-500">{k}</span><span className="text-right text-slate-800">{String(v)}</span></div>;
}

export default function WebOrderDetail() {
  const { id } = useParams();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const timer = useRef(null);

  const load = useCallback(async () => {
    try { setD(await webOrdersApi.get(id)); setErr(""); } catch (e) { setErr(e.response?.data?.detail || "Could not load this order"); }
  }, [id]);

  useEffect(() => {
    load();
    clearInterval(timer.current);
    timer.current = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer.current);
  }, [load]);

  if (err) return <p className="rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</p>;
  if (!d) return <p className="text-sm text-slate-500">Loading...</p>;
  const o = d.order;

  return (
    <div className="space-y-3">
      <div>
        <Link to="/web-orders" className="text-xs text-[#1e3a8a] hover:underline">&larr; Web Orders</Link>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold text-slate-800">{o.order_number || `Order #${o.site_order_id}`}</h1>
          <Badge>{o.status}</Badge>
          <Badge>{o.payment_status}</Badge>
        </div>
        <p className="text-sm text-slate-500">Placed {when(o.site_created_at)} · last changed on the website {when(o.site_updated_at)} · synced {when(o.last_synced_at)}</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <Card title="Items">
            {d.items.length === 0 && <p className="text-sm text-slate-400">No items.</p>}
            <ul className="divide-y divide-slate-100">
              {d.items.map((it) => (
                <li key={it.id} className="py-2 text-sm">
                  <div className="flex justify-between gap-3">
                    <div>
                      <div className="font-medium text-slate-800">{it.product_name || it.product_id}</div>
                      <div className="text-xs text-slate-500">{it.product_id} · quantity {it.quantity ?? "-"}{it.delivery_date ? ` · delivery ${it.delivery_date}` : ""}{it.time_slot ? ` · ${it.time_slot}` : ""}</div>
                    </div>
                    <div className="whitespace-nowrap text-slate-800">{rupees(it.price)}</div>
                  </div>
                  {it.product_info && typeof it.product_info === "object" && (
                    <div className="mt-1 text-xs text-slate-500">{Object.entries(it.product_info).filter(([, v]) => v !== null && typeof v !== "object").map(([k, v]) => `${k}: ${v}`).join(" · ")}</div>
                  )}
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Timeline">
            <ol className="space-y-2 border-l border-slate-200 pl-4">
              {d.events.map((e) => (
                <li key={e.id} className="relative text-sm">
                  <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-[#1e3a8a]" />
                  <div className="text-slate-800">{(EVENT_TEXT[e.kind] || (() => e.kind))(e)}</div>
                  <div className="text-xs text-slate-500">{when(e.happened_at)}</div>
                </li>
              ))}
            </ol>
          </Card>

          <Card title="Payment attempts">
            {d.payments.length === 0 && <p className="text-sm text-slate-400">No payment attempts recorded.</p>}
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <tbody>
                  {d.payments.map((p) => (
                    <tr key={p.id} className="border-t border-slate-100">
                      <td className="py-1.5 pr-3 text-slate-600">{when(p.attempted_at)}</td>
                      <td className="pr-3"><Badge>{p.status}</Badge></td>
                      <td className="pr-3">{rupees(p.amount)} {p.currency}</td>
                      <td className="text-xs text-slate-500">{p.payment_id || p.razorpay_order_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div className="space-y-3">
          <Card title="Customer">
            <Row k="Name" v={o.customer_name} /><Row k="Mobile" v={o.mobile} /><Row k="Email" v={o.email} />
            <Row k="Company" v={o.company_name} /><Row k="GST number" v={o.gst_number} />
            {d.whatsapp_conversation_id && <Link to={`/whatsapp?conv=${d.whatsapp_conversation_id}`} className="mt-2 inline-block rounded bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-800">Open the WhatsApp chat</Link>}
          </Card>

          <Card title="Amount">
            <Row k="Subtotal" v={rupees(o.subtotal)} />
            <Row k="Discount" v={o.discount_amount ? `- ${rupees(o.discount_amount)}${o.coupon_code ? ` (${o.coupon_code})` : ""}` : null} />
            <Row k="Shipping" v={rupees(o.shipping)} /><Row k="Tax" v={o.tax ? rupees(o.tax) : null} />
            <div className="mt-1 flex justify-between border-t border-slate-100 pt-1 text-sm font-semibold"><span>Total</span><span>{rupees(o.total)}</span></div>
            <Row k="Payment method" v={o.payment_method} /><Row k="Payment id" v={o.payment_id} /><Row k="Gateway order" v={o.razorpay_order_id} />
            <Row k="Stock deducted" v={o.stock_deducted_at ? when(o.stock_deducted_at) : null} />
          </Card>

          <Card title="Addresses">
            {d.addresses.length === 0 && <><Row k="Shipping" v={o.shipping_address} /><Row k="Billing" v={o.billing_address} /></>}
            {d.addresses.map((a) => (
              <div key={a.id} className="mb-2 text-sm last:mb-0">
                <div className="text-xs font-semibold capitalize text-slate-500">{a.kind}</div>
                <div className="text-slate-800">{a.full_name}{a.mobile ? ` · ${a.mobile}` : ""}</div>
                <div className="text-slate-600">{[a.address_line1, a.address_line2, a.city, a.state, a.pincode, a.country].filter(Boolean).join(", ")}</div>
              </div>
            ))}
          </Card>

          <Card title="Complaints from this customer">
            {d.complaints.length === 0 && <p className="text-sm text-slate-400">None on this mobile number.</p>}
            <ul className="space-y-1 text-sm">
              {d.complaints.map((c) => <li key={c.id}><Link to={`/complaints/${c.id}`} className="text-[#1e3a8a] hover:underline">{c.comp_no}</Link> <span className="text-slate-500">{c.query_type} · {c.status}</span></li>)}
            </ul>
          </Card>

          {o.extra && (
            <Card title="Other website details">
              {Object.entries(o.extra).map(([k, v]) => <Row key={k} k={k} v={typeof v === "object" ? JSON.stringify(v) : v} />)}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
