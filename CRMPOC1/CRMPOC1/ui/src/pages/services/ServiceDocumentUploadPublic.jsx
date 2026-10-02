import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { servicesApi } from "../../api/services.js";
import { installationsApi } from "../../api/installations.js";

const DOCUMENT_OPTIONS = ["Purchase Order", "Original Purchase Bill/Invoice"];

const fieldClass =
  "w-full rounded-xl border border-slate-300 px-3 py-3 text-base sm:text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";

function InfoField({ label, value }) {
  return (
    <div className="min-w-0">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 break-words text-sm text-slate-800">{value || "-"}</div>
    </div>
  );
}

function FileUploadCard({ documentType, file, onChange }) {
  const inputId = `upload-${documentType.replace(/\s+/g, "-").toLowerCase()}`;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
      <label htmlFor={inputId} className="mb-3 block text-sm font-medium text-slate-800">
        {documentType}
      </label>
      <label
        htmlFor={inputId}
        className="flex min-h-[7rem] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-center transition active:border-sky-400 active:bg-sky-50 sm:min-h-[6.5rem]"
      >
        <span className="text-sm font-medium text-sky-700">
          {file ? "Tap to change file" : "Tap to choose file"}
        </span>
        <span className="mt-1 text-xs text-slate-500">PDF, JPG, JPEG, PNG — max 2 MB</span>
        {file && (
          <span className="mt-3 max-w-full break-all rounded-md bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm">
            {file.name}
          </span>
        )}
      </label>
      <input
        id={inputId}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,image/jpeg,image/png,application/pdf"
        onChange={(e) => onChange(e.target.files?.[0] || null)}
        className="sr-only"
      />
    </div>
  );
}

export default function ServiceDocumentUploadPublic() {
  const { token } = useParams();
  const [context, setContext] = useState(null);
  const [customerName, setCustomerName] = useState("");
  const [serialNo, setSerialNo] = useState("");
  const [files, setFiles] = useState({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    servicesApi.publicDocumentContext(token)
      .then((result) => {
        setContext({ ...result, module: "service" });
        setCustomerName(result.customer_name || "");
        setSerialNo(result.serial_no || "");
      })
      .catch(() => {
        installationsApi.publicDocumentContext(token)
          .then((result) => {
            setContext(result);
            setCustomerName(result.customer_name || "");
            setSerialNo(result.serial_no || "");
          })
          .catch((error) => setErr(error.response?.data?.detail || "Upload link is invalid or expired"));
      });
  }, [token]);

  async function submit() {
    const selected = Object.entries(files).filter(([, value]) => value);
    if (selected.length === 0) {
      setErr("Please upload at least one document.");
      return;
    }
    setBusy(true);
    setErr("");
    setSuccess("");
    try {
      for (const [documentType, file] of selected) {
        const formData = new FormData();
        formData.append("document_type", documentType);
        formData.append("customer_name", customerName);
        if (serialNo.trim()) {
          formData.append("serial_no", serialNo.trim());
        }
        formData.append("file", file);
        if (context.module === "installation") {
          await installationsApi.publicUploadDocuments(token, formData);
        } else {
          await servicesApi.publicUploadDocuments(token, formData);
        }
      }
      setSuccess("Documents uploaded successfully. Our service team will review them and continue the request.");
      setFiles({});
    } catch (error) {
      setErr(error.response?.data?.detail || "Document upload failed");
    } finally {
      setBusy(false);
    }
  }

  if (err && !context) {
    return (
      <div className="min-h-screen bg-slate-100 px-4 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-[max(1.5rem,env(safe-area-inset-top))] sm:py-10">
        <div className="mx-auto max-w-xl rounded-2xl bg-rose-50 px-4 py-4 text-sm text-rose-700 sm:px-6 sm:py-5">
          {err}
        </div>
      </div>
    );
  }

  if (!context) {
    return (
      <div className="min-h-screen bg-slate-100 px-4 py-10 text-center text-slate-500 sm:mt-0">
        Loading upload page...
      </div>
    );
  }

  const requiredDocuments = context.required_documents?.length ? context.required_documents : DOCUMENT_OPTIONS;

  return (
    <div className="min-h-screen bg-slate-100 px-3 py-4 pb-[max(6.5rem,env(safe-area-inset-bottom))] pt-[max(1rem,env(safe-area-inset-top))] sm:px-4 sm:py-8 sm:pb-10">
      <div className="mx-auto w-full max-w-3xl rounded-2xl bg-white p-4 shadow-lg sm:rounded-3xl sm:p-6 md:p-8">
        <div className="mb-5 sm:mb-6">
          <div className="text-xs font-medium uppercase tracking-[0.15em] text-sky-700 sm:text-sm sm:tracking-[0.2em]">
            INDcool Service Support
          </div>
          <h1 className="mt-2 text-2xl font-bold leading-tight text-slate-900 sm:text-3xl">
            Upload Customer Documents
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            Please upload the requested documents for{" "}
            {context.module === "installation" ? "installation request" : "service request"}{" "}
            <span className="font-medium text-slate-800">{context.request_no}</span>.
            No login is required for this secure upload page.
          </p>
        </div>

        <div className="grid gap-3 rounded-2xl bg-slate-50 p-4 sm:gap-4 sm:p-5 md:grid-cols-2">
          <InfoField label="Customer" value={context.customer_name} />
          <InfoField label="Email" value={context.customer_email} />
          <InfoField label="Order No" value={context.order_no} />
          <InfoField label="Serial No" value={context.serial_no} />
          <div className="min-w-0 md:col-span-2">
            <InfoField label="Problem Description" value={context.problem_description} />
          </div>
        </div>

        <div className="mt-5 space-y-4 sm:mt-6">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">Customer Name</span>
            <input
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className={fieldClass}
              autoComplete="name"
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">
              Serial Number <span className="font-normal text-slate-500">(optional)</span>
            </span>
            <input
              value={serialNo}
              onChange={(e) => setSerialNo(e.target.value)}
              className={fieldClass}
              placeholder="Enter product serial number if available"
              readOnly={context.serial_no_locked}
              disabled={context.serial_no_locked}
            />
            <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
              {context.serial_no_locked
                ? "This serial number is linked to your service request and will be used during order verification."
                : "If your serial number is from a previous INDcool order, enter it here. We will verify only that unit instead of all items on the order."}
            </p>
          </label>

          {requiredDocuments.map((documentType) => (
            <FileUploadCard
              key={documentType}
              documentType={documentType}
              file={files[documentType]}
              onChange={(file) => setFiles((current) => ({ ...current, [documentType]: file }))}
            />
          ))}
        </div>

        {err && (
          <div className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm leading-relaxed text-rose-700">
            {err}
          </div>
        )}
        {success && (
          <div className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm leading-relaxed text-emerald-700">
            {success}
          </div>
        )}

        <div className="mt-6 hidden sm:flex sm:justify-end">
          <button
            type="button"
            onClick={submit}
            disabled={busy}
            className="min-h-11 touch-manipulation rounded-xl bg-sky-700 px-5 py-3 text-sm font-medium text-white hover:bg-sky-800 disabled:opacity-50"
          >
            {busy ? "Uploading..." : "Submit Documents"}
          </button>
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-10 border-t border-slate-200 bg-white/95 px-3 py-3 backdrop-blur-sm sm:hidden pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <button
          type="button"
          onClick={submit}
          disabled={busy}
          className="min-h-12 w-full touch-manipulation rounded-xl bg-sky-700 px-5 py-3.5 text-base font-medium text-white active:bg-sky-800 disabled:opacity-50"
        >
          {busy ? "Uploading..." : "Submit Documents"}
        </button>
      </div>
    </div>
  );
}
