import { useState } from "react";

import ItemMasterList from "./ItemMasterList.jsx";
import SparePartsCatalogue from "./SparePartsCatalogue.jsx";

// Approving parts/item requests now lives on the combined Approvals page (Parts tab), not here.
const tabs = [
  ["items", "Items"],
  ["catalogue", "Spare parts"],
];

export default function ItemMastersPage() {
  const [tab, setTab] = useState("items");

  return (
    <div className="space-y-4">
      <nav className="flex flex-wrap gap-1 border-b border-slate-200 pb-2">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === key ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "items" && <ItemMasterList />}
      {tab === "catalogue" && <SparePartsCatalogue />}
    </div>
  );
}
