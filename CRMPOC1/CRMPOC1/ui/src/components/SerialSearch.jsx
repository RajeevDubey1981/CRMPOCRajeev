import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { serialApi } from "../api/serials.js";

export default function SerialSearch() {
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const timeoutRef = useRef(null);
  const navigate = useNavigate();
  const dropdownRef = useRef(null);

  useEffect(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    if (!input.trim()) {
      setSuggestions([]);
      setError(null);
      setShowSuggestions(false);
      setSelectedIndex(-1);
      return;
    }

    setLoading(true);
    setShowSuggestions(true);
    setSelectedIndex(-1);

    timeoutRef.current = setTimeout(async () => {
      try {
        const { data } = await serialApi.search(input);
        setSuggestions(data || []);
        setError(data && data.length === 0 ? "No serials found matching your search" : null);
      } catch (err) {
        setSuggestions([]);
        setError(err.response?.data?.detail || "Search failed");
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timeoutRef.current);
  }, [input]);

  const handleSelectSerial = (serial) => {
    navigate(`/serials/history?serial=${encodeURIComponent(serial.serial_no)}`);
    setInput("");
    setSuggestions([]);
    setShowSuggestions(false);
  };

  const handleClear = () => {
    setInput("");
    setSuggestions([]);
    setError(null);
    setShowSuggestions(false);
    setSelectedIndex(-1);
  };

  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : prev));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
      case "Enter":
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleSelectSerial(suggestions[selectedIndex]);
        }
        break;
      case "Escape":
        e.preventDefault();
        setShowSuggestions(false);
        break;
      default:
        break;
    }
  };

  return (
    <div className="relative w-80" ref={dropdownRef}>
      <div className="flex items-center gap-2">
        <input
          type="text"
          placeholder="Search serial number..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onFocus={() => input && setShowSuggestions(true)}
          onKeyDown={handleKeyDown}
          className="flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-base focus:border-blue-500 focus:outline-none sm:text-sm"
        />
        {input && (
          <button
            onClick={handleClear}
            className="p-1 text-slate-400 hover:text-slate-600"
            title="Clear"
          >
            ✕
          </button>
        )}
      </div>

      {showSuggestions && (
        <div className="absolute right-0 top-10 mt-1 w-96 max-h-96 rounded border border-slate-200 bg-white shadow-lg z-50 overflow-y-auto">
          {loading && (
            <div className="px-4 py-8 text-center text-sm text-slate-600 flex items-center justify-center gap-2">
              <span className="animate-spin inline-block">⟳</span> Searching...
            </div>
          )}

          {!loading && error && (
            <div className="px-4 py-4 text-sm text-slate-600 text-center">
              📭 {error}
            </div>
          )}

          {!loading && suggestions.length > 0 && (
            <div className="divide-y divide-slate-100">
              {suggestions.map((suggestion, index) => (
                <button
                  key={suggestion.serial_no}
                  type="button"
                  onClick={() => handleSelectSerial(suggestion)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`w-full text-left px-4 py-3 transition ${
                    index === selectedIndex ? "bg-blue-50" : "hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-slate-900 truncate">
                        {suggestion.serial_no}
                      </div>
                      <div className="text-xs text-slate-600 mt-1 line-clamp-2">
                        {suggestion.item_name}
                      </div>
                      <div className="flex items-center gap-2 mt-1.5 text-xs">
                        <span className="text-slate-500">📋</span>
                        <span className="text-slate-700">{suggestion.order_no}</span>
                        <span className="text-slate-400">•</span>
                        <span className="text-slate-700 truncate">{suggestion.customer_name}</span>
                      </div>
                    </div>
                    <div className="flex-shrink-0">
                      <span
                        className={`inline-block px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${
                          suggestion.installation_status === "Completed"
                            ? "bg-green-100 text-green-800"
                            : suggestion.installation_status === "In Progress"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-yellow-100 text-yellow-800"
                        }`}
                      >
                        {suggestion.installation_status || "Pending"}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {!loading && suggestions.length === 0 && !error && input.length > 0 && (
            <div className="px-4 py-8 text-center text-sm text-slate-600">
              🔍 Start typing to find serials
            </div>
          )}
        </div>
      )}
    </div>
  );
}
