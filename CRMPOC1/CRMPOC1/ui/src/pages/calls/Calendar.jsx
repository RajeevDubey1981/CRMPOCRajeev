import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { callsApi } from "../../api/calls.js";

function getDaysInMonth(date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
}

function getFirstDayOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
}

export default function Calendar() {
  const navigate = useNavigate();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  async function loadEvents() {
    setLoading(true);
    try {
      const data = await callsApi.calendarEvents({
        start: new Date(currentDate.getFullYear(), currentDate.getMonth(), 1).toISOString(),
        end: new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0).toISOString(),
      });
      setEvents(data || []);
    } catch (e) {
      console.error("Failed to load events", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEvents();
  }, [currentDate]);

  function getEventsForDate(day) {
    const dateStr = new Date(currentDate.getFullYear(), currentDate.getMonth(), day).toDateString();
    return events.filter((e) => {
      try {
        return new Date(e.start).toDateString() === dateStr;
      } catch {
        return false;
      }
    });
  }

  const daysInMonth = getDaysInMonth(currentDate);
  const firstDay = getFirstDayOfMonth(currentDate);
  const days = [];

  for (let i = 0; i < firstDay; i++) {
    days.push(null);
  }
  for (let i = 1; i <= daysInMonth; i++) {
    days.push(i);
  }

  const monthName = currentDate.toLocaleString("default", { month: "long", year: "numeric" });
  const prevMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1);
  const nextMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">Call Follow-ups Calendar</h1>
        <button
          onClick={() => navigate("/calls")}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50"
        >
          ← Back to Calls
        </button>
      </div>

      <div className="rounded-lg bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <button
            onClick={() => setCurrentDate(prevMonth)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
          >
            ← Previous
          </button>
          <h2 className="text-lg font-semibold text-slate-800">{monthName}</h2>
          <button
            onClick={() => setCurrentDate(nextMonth)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
          >
            Next →
          </button>
        </div>

        <div className="mb-4 grid grid-cols-7 gap-1 text-center">
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
            <div key={d} className="py-2 text-xs font-semibold text-slate-600">
              {d}
            </div>
          ))}
        </div>

        {loading && <div className="py-8 text-center text-slate-500">Loading…</div>}

        {!loading && (
          <div className="grid grid-cols-7 gap-1">
            {days.map((day, idx) => {
              const dayEvents = day ? getEventsForDate(day) : [];
              const hasEvents = dayEvents.length > 0;

              return (
                <div
                  key={idx}
                  className={`min-h-20 rounded-lg border p-2 ${
                    day === null ? "bg-slate-50" : hasEvents ? "border-blue-300 bg-blue-50" : "border-slate-200"
                  }`}
                >
                  {day && (
                    <>
                      <div className="mb-1 text-xs font-semibold text-slate-700">{day}</div>
                      <div className="space-y-0.5">
                        {dayEvents.map((event) => (
                          <button
                            key={event.id}
                            onClick={() => navigate(`/calls/${event.id}`)}
                            className="block w-full truncate rounded bg-blue-500 px-1 py-0.5 text-left text-xs text-white hover:bg-blue-600"
                            title={event.title}
                          >
                            {event.title}
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-6 rounded-lg bg-slate-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Events ({events.length})</h3>
          <div className="space-y-1 text-sm">
            {events.length === 0 && <p className="text-slate-600">No events this month</p>}
            {events.map((event) => (
              <button
                key={event.id}
                onClick={() => navigate(`/calls/${event.id}`)}
                className="block w-full truncate text-left text-slate-700 hover:text-blue-600"
              >
                <span className="font-mono text-xs">{new Date(event.start).toLocaleDateString()}</span> — {event.title}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
