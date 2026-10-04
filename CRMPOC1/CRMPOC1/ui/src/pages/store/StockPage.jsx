import { useEffect, useMemo, useState } from "react";

import Pagination from "../../components/Pagination.jsx";
import { storeApi, storeError } from "../../api/store.js";
import { fmtDateTime } from "./GrnList.jsx";

const TABS = [["summary", "Stock by item"], ["units", "Serials and batches"], ["ledger", "Ledger"]];
const STATUS_BADGE = {
  Available: "bg-emerald-100 text-emerald-800",
  Quarantine: "bg-rose-100 text-rose-800",
  Reserved: "bg-amber-100 text-amber-800",
  Issued: "bg-slate-100 text-slate-700",
  Scrapped: "bg-slate-200 text-slate-600",
};

function Table({ head, children, empty, loading, cols }) {
  return (
    <div className="crm-scroll rounded-lg bg-white shadow-sm">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-100 text-left text-slate-700"><tr>{head}</tr></thead>
        <tbody className="divide-y divide-slate-100">
          {loading && <tr><td colSpan={cols} className="px-3 py-6 text-center text-slate-500">Loading...</td></tr>}
          {!loading && empty && <tr><td colSpan={cols} className="px-3 py-6 text-center text-slate-500">{empty}</td></tr>}
          {!loading && children}
        </tbody>
      </table>
    </div>
  );
}

export default function StockPage() {
  const [tab, setTab] = useState("summary");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [itemId, setItemId] = useState(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [summary, setSummary] = useState([]);
  const [units, setUnits] = useState({ items: [], total: 0 });
  const [ledger, setLedger] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const q = useMemo(() => ({ search: search || undefined, status: status || undefined, item_id: itemId || undefined, page, per_page: perPage }), [search, status, itemId, page, perPage]);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setErr("");
    const run = tab === "summary" ? storeApi.stock({ search: search || undefined }).then((d) => live && setSummary(d))
      : tab === "units" ? storeApi.stockUnits(q).then((d) => live && setUnits(d))
        : storeApi.ledger({ search: search || undefined, page, per_page: perPage }).then((d) => live && setLedger(d));
    run.catch((e) => live && setErr(storeError(e, "Failed to load stock"))).finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [tab, q, search, page, perPage]);

  function openUnits(row) {
    setItemId(row.item_id);
    setSearch("");
    setPage(1);
    setTab("units");
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Stock and ledger</h1>
        <p className="text-sm text-slate-500">Only goods received with an approved GRN count as stock. Oldest stock is listed first.</p>
      </div>

      <div className="rounded-lg bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {TABS.map(([k, label]) => (
            <button key={k} type="button" onClick={() => { setTab(k); setPage(1); }} className={`rounded-full px-3 py-1 text-sm ${tab === k ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>{label}</button>
          ))}
          {tab === "units" && (
            <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="rounded-md border border-slate-300 px-2 py-1.5 text-sm">
              <option value="">All statuses</option>
              {Object.keys(STATUS_BADGE).map((s) => <option key={s}>{s}</option>)}
            </select>
          )}
          {itemId && tab === "units" && <button type="button" onClick={() => { setItemId(null); setPage(1); }} className="text-sm text-brand-700 hover:underline">Show all items</button>}
          <input
            type="text"
            placeholder={tab === "ledger" ? "Search document, serial or item" : "Search item or serial"}
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="ml-auto w-full rounded-md border border-slate-300 px-3 py-2 text-sm md:w-72"
          />
        </div>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {tab === "summary" && (
        <Table
          loading={loading}
          cols={6}
          empty={summary.length === 0 ? "No stock yet. Receive goods with a GRN first." : null}
          head={<><th className="px-3 py-2">Item</th><th className="px-3 py-2">Code</th><th className="px-3 py-2 text-right">Available</th><th className="px-3 py-2 text-right">Quarantine</th><th className="px-3 py-2 text-right">Total</th><th className="px-3 py-2">Oldest received</th></>}
        >
          {summary.map((r) => (
            <tr key={r.item_id} className="cursor-pointer hover:bg-slate-50" onClick={() => openUnits(r)}>
              <td className="px-3 py-2 font-medium text-slate-800">{r.item_name}</td>
              <td className="px-3 py-2 font-mono text-xs text-slate-600">{r.item_code}</td>
              <td className="px-3 py-2 text-right font-semibold text-emerald-700">{r.available}</td>
              <td className="px-3 py-2 text-right text-rose-700">{r.quarantine}</td>
              <td className="px-3 py-2 text-right">{r.total}</td>
              <td className="px-3 py-2 text-slate-600">{fmtDateTime(r.oldest_received)}</td>
            </tr>
          ))}
        </Table>
      )}

      {tab === "units" && (
        <>
          <Table
            loading={loading}
            cols={9}
            empty={units.items.length === 0 ? "Nothing found." : null}
            head={<><th className="px-3 py-2">Item</th><th className="px-3 py-2">Serial 1</th><th className="px-3 py-2">Serial 2</th><th className="px-3 py-2 text-right">Qty</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Bin</th><th className="px-3 py-2">GRN</th><th className="px-3 py-2 text-right">Age</th></>}
          >
            {units.items.map((u) => (
              <tr key={u.id}>
                <td className="px-3 py-2">{u.item_name}</td>
                <td className="px-3 py-2 font-mono text-xs">{u.serial_no || "-"}</td>
                <td className="px-3 py-2 font-mono text-xs">{u.serial_no_2 || "-"}</td>
                <td className="px-3 py-2 text-right">{u.qty}</td>
                <td className="px-3 py-2">{u.stock_type}</td>
                <td className="px-3 py-2"><span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_BADGE[u.status] || "bg-slate-100"}`}>{u.status}</span></td>
                <td className="px-3 py-2 text-slate-600">{u.bin_location || "-"}</td>
                <td className="px-3 py-2 font-mono text-xs">{u.grn_no || "-"}</td>
                <td className="px-3 py-2 text-right">{u.age_days} d</td>
              </tr>
            ))}
          </Table>
          <Pagination page={page} perPage={perPage} total={units.total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
        </>
      )}

      {tab === "ledger" && (
        <>
          <Table
            loading={loading}
            cols={8}
            empty={ledger.items.length === 0 ? "No movements yet." : null}
            head={<><th className="px-3 py-2">When</th><th className="px-3 py-2">Document</th><th className="px-3 py-2">Item</th><th className="px-3 py-2">Serial</th><th className="px-3 py-2 text-right">In</th><th className="px-3 py-2 text-right">Out</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">By</th></>}
          >
            {ledger.items.map((r) => (
              <tr key={r.id}>
                <td className="px-3 py-2 text-slate-600">{fmtDateTime(r.created_at)}</td>
                <td className="px-3 py-2 font-mono text-xs font-bold">{r.doc_no}</td>
                <td className="px-3 py-2">{r.item_name}</td>
                <td className="px-3 py-2 font-mono text-xs">{r.serial_no || "-"}</td>
                <td className="px-3 py-2 text-right text-emerald-700">{r.qty_in || ""}</td>
                <td className="px-3 py-2 text-right text-amber-700">{r.qty_out || ""}</td>
                <td className="px-3 py-2">{r.stock_type || "-"}</td>
                <td className="px-3 py-2 text-slate-600">{r.by_user_name || "-"}</td>
              </tr>
            ))}
          </Table>
          <Pagination page={page} perPage={perPage} total={ledger.total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
        </>
      )}
    </div>
  );
}
