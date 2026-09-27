import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { installationsApi } from "../../api/installations.js";
import { useAuth } from "../../auth/AuthContext.jsx";
import { isOperationsAdminRole } from "../../utils/roles.js";
import BulkInstallationWorkflowPanel from "./BulkInstallationWorkflowPanel.jsx";

export default function BulkInstallationWorkflowPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdminLike = isOperationsAdminRole(user?.role);
  const [searchParams] = useSearchParams();
  const ids = useMemo(
    () => searchParams.get("ids")?.split(",").map((value) => Number(value.trim())).filter((id) => id > 0) ?? [],
    [searchParams],
  );
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  async function loadRows() {
    if (!ids.length) {
      setRows([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setErr("");
    try {
      const results = await Promise.allSettled(ids.map((id) => installationsApi.get(id)));
      const loaded = results
        .filter((result) => result.status === "fulfilled")
        .map((result) => result.value);
      const failed = results.length - loaded.length;
      if (failed > 0) {
        setErr(`${failed} request(s) could not be loaded.`);
      }
      setRows(loaded);
    } catch (error) {
      setErr(error.response?.data?.detail || "Failed to load installation requests");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRows();
  }, [ids.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">
            {isAdminLike ? "Bulk installation review" : "Bulk installation workflow"}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {ids.length} request(s) selected — serial number and status per unit
          </p>
        </div>
        <Link
          to="/installations"
          className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Back to list
        </Link>
      </div>

      {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}

      {loading && (
        <div className="rounded-lg bg-white p-6 text-center text-sm text-slate-500 shadow-sm">
          Loading workflow…
        </div>
      )}

      {!loading && ids.length === 0 && (
        <div className="rounded-lg bg-white p-6 text-center text-sm text-slate-600 shadow-sm">
          No installation requests selected.{" "}
          <button type="button" onClick={() => navigate("/installations")} className="text-brand-600 underline">
            Return to the list
          </button>
        </div>
      )}

      {!loading && ids.length > 0 && (
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <BulkInstallationWorkflowPanel rows={rows} onSaved={loadRows} />
        </div>
      )}
    </div>
  );
}
