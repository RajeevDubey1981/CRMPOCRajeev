export default function Pagination({ page, perPage, total, onPageChange, onPerPageChange }) {
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  return (
    <div className="flex flex-col items-center justify-between gap-3 sm:flex-row">
      <div className="text-sm text-slate-600">
        Showing {(page - 1) * perPage + (total ? 1 : 0)}–{Math.min(page * perPage, total)} of {total}
      </div>
      <div className="flex items-center gap-2 text-sm">
        <label className="text-slate-600">Rows:</label>
        <select
          value={perPage}
          onChange={(e) => onPerPageChange?.(Number(e.target.value))}
          className="rounded-md border border-slate-300 px-2 py-1 text-base sm:text-sm"
        >
          {[10, 20, 30, 50, 100].map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => onPageChange?.(Math.max(1, page - 1))}
          disabled={page <= 1}
          className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-50"
        >
          Prev
        </button>
        <span className="px-2">Page {page} / {totalPages}</span>
        <button
          type="button"
          onClick={() => onPageChange?.(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
          className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
