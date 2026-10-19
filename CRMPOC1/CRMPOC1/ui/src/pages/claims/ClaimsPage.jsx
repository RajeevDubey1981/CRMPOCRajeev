import { useState } from "react";

import ClaimList from "./ClaimList.jsx";
import ShortageClaimsTab from "./ShortageClaimsTab.jsx";

export default function ClaimsPage() {
  const [tab, setTab] = useState("customer");

  const tabs = [
    ["customer", "Customer Claims"],
    ["shortage", "Missing-Item Claims"],
  ];

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
      {tab === "customer" && <ClaimList />}
      {tab === "shortage" && <ShortageClaimsTab />}
    </div>
  );
}
