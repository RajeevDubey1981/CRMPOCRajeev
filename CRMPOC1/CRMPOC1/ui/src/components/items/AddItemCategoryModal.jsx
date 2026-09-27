import { useState } from "react";

import Modal from "../Modal.jsx";
import { addItemCategoryExtra } from "../../utils/itemCategoryExtras.js";

export default function AddItemCategoryModal({ open, onClose, onAdded }) {
  const [name, setName] = useState("");
  const [err, setErr] = useState("");

  function close() {
    setName("");
    setErr("");
    onClose();
  }

  function submit(e) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setErr("Enter a category name.");
      return;
    }
    addItemCategoryExtra(trimmed);
    onAdded?.(trimmed);
    close();
  }

  return (
    <Modal open={open} onClose={close} title="Add category" maxWidth="max-w-md">
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-slate-600">
          New categories appear in the category dropdown. They are stored permanently once you assign them to an item and save.
        </p>
        {err && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Category name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. VRF Outdoor Unit"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            autoFocus
          />
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={close} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
            Cancel
          </button>
          <button type="submit" className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white">
            Add category
          </button>
        </div>
      </form>
    </Modal>
  );
}
