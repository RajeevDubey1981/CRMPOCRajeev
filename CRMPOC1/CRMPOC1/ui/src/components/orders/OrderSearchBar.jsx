import { useEffect, useRef, useState } from "react";

import { ordersApi } from "../../api/orders.js";

const MIN_AUTOCOMPLETE_CHARS = 2;
const AUTOCOMPLETE_DEBOUNCE_MS = 400;

function SpinnerLabel({ label = "Loading..." }) {
  return (
    <span className="inline-flex items-center gap-2 text-slate-500">
      <span className="inline-block animate-spin">|</span>
      <span>{label}</span>
    </span>
  );
}

function SuggestionItem({ item, onSelect }) {
  return (
    <button
      type="button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={() => onSelect(item)}
      className="block w-full px-3 py-2 text-left hover:bg-brand-50"
    >
      <div className="text-sm font-medium text-slate-800">{item.order_no || item.oem_bill_no || `Order #${item.order_id}`}</div>
      <div className="mt-0.5 text-xs text-slate-500">{item.display_label}</div>
    </button>
  );
}

export default function OrderSearchBar({
  value,
  onChange,
  onSelect,
  onDebouncedSearch,
  placeholder = "Search customer name / mobile / order / OEM bill / vendor",
  className = "",
  inputClassName = "",
}) {
  const autocompleteRef = useRef(null);
  const autocompleteRequestRef = useRef(0);
  const [internalValue, setInternalValue] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [hasSuggestionResults, setHasSuggestionResults] = useState(false);

  const searchInput = value !== undefined ? value : internalValue;
  const setSearchInput = onChange || setInternalValue;
  const normalizedSearchInput = searchInput.trim();

  const onDebouncedSearchRef = useRef(onDebouncedSearch);
  useEffect(() => {
    onDebouncedSearchRef.current = onDebouncedSearch;
  }, [onDebouncedSearch]);

  useEffect(() => {
    if (!onDebouncedSearchRef.current) return undefined;
    const handle = window.setTimeout(() => {
      onDebouncedSearchRef.current?.(normalizedSearchInput);
    }, AUTOCOMPLETE_DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [normalizedSearchInput]);

  useEffect(() => {
    function onDocClick(e) {
      if (autocompleteRef.current && !autocompleteRef.current.contains(e.target)) {
        setSuggestionsOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    const query = normalizedSearchInput;
    if (query.length < MIN_AUTOCOMPLETE_CHARS) {
      setSuggestions([]);
      setSuggestionsLoading(false);
      setHasSuggestionResults(false);
      return undefined;
    }

    const timeoutId = window.setTimeout(async () => {
      const requestId = ++autocompleteRequestRef.current;
      setSuggestionsLoading(true);
      try {
        const result = await ordersApi.autocomplete({ q: query, limit: 10 });
        if (requestId !== autocompleteRequestRef.current) return;
        setSuggestions(result);
        setHasSuggestionResults(true);
        setSuggestionsOpen(true);
      } catch {
        if (requestId !== autocompleteRequestRef.current) return;
        setSuggestions([]);
        setHasSuggestionResults(true);
      } finally {
        if (requestId === autocompleteRequestRef.current) {
          setSuggestionsLoading(false);
        }
      }
    }, AUTOCOMPLETE_DEBOUNCE_MS);

    return () => window.clearTimeout(timeoutId);
  }, [normalizedSearchInput]);

  function selectSuggestion(item) {
    const next = item.order_no || item.oem_bill_no || item.customer_contact || item.customer_name || item.vendor_code || item.vendor_name || "";
    setSearchInput(next);
    setSuggestionsOpen(false);
    onSelect?.(item, next.trim());
  }

  return (
    <div className={`relative ${className}`} ref={autocompleteRef}>
      <input
        type="text"
        placeholder={placeholder}
        value={searchInput}
        onFocus={() => {
          if (normalizedSearchInput.length >= MIN_AUTOCOMPLETE_CHARS) {
            setSuggestionsOpen(true);
          }
        }}
        onChange={(e) => {
          setSearchInput(e.target.value);
          setSuggestionsOpen(true);
          setHasSuggestionResults(false);
        }}
        className={`w-full rounded-md border border-slate-300 px-3 py-2 pr-10 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 ${inputClassName}`}
      />
      {suggestionsLoading && (
        <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">
          <span className="animate-spin">⟳</span>
        </div>
      )}
      {suggestionsOpen && normalizedSearchInput.length >= MIN_AUTOCOMPLETE_CHARS && (
        <div className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-md border border-slate-200 bg-white shadow-lg">
          {suggestionsLoading && (
            <div className="px-3 py-3 text-sm">
              <SpinnerLabel label="Fetching matches..." />
            </div>
          )}
          {!suggestionsLoading && suggestions.map((item) => (
            <SuggestionItem key={`${item.order_id}-${item.match_field}`} item={item} onSelect={selectSuggestion} />
          ))}
          {!suggestionsLoading && hasSuggestionResults && suggestions.length === 0 && (
            <div className="px-3 py-2 text-sm text-slate-400">No matches found.</div>
          )}
        </div>
      )}
    </div>
  );
}
