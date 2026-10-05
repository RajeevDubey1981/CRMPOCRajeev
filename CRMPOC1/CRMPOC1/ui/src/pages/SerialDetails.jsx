import { useLocation, useNavigate } from "react-router-dom";

export default function SerialDetails() {
  const location = useLocation();
  const navigate = useNavigate();
  const serial = location.state?.serial;

  if (!serial) {
    return (
      <div className="p-8 text-center">
        <div className="text-red-600 mb-4">No serial data found</div>
        <button
          onClick={() => navigate(-1)}
          className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">{serial.serial_no}</h1>
          {serial.serial_no_2 && (
            <p className="text-sm text-slate-600 mt-1">Secondary: {serial.serial_no_2}</p>
          )}
        </div>
        <button
          onClick={() => navigate(-1)}
          className="rounded-md border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-100"
        >
          Back
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Product Information */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Product Information</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-600">Product Name</label>
              <p className="text-slate-900 font-medium">{serial.item_name || "-"}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">Item Code</label>
              <p className="text-slate-900 font-medium">{serial.item_code || "-"}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">Installation Status</label>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium mt-1 ${
                serial.installation_status === "Completed"
                  ? "bg-green-100 text-green-800"
                  : serial.installation_status === "In Progress"
                  ? "bg-blue-100 text-blue-800"
                  : "bg-yellow-100 text-yellow-800"
              }`}>
                {serial.installation_status || "-"}
              </span>
            </div>
          </div>
        </div>

        {/* Order Information */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Order Information</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-600">Order Number</label>
              <p className="text-slate-900 font-medium">{serial.order_no || "-"}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">Customer Name</label>
              <p className="text-slate-900 font-medium">{serial.customer_name || "-"}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">Contact Number</label>
              <p className="text-slate-900 font-medium">{serial.customer_contact || "-"}</p>
            </div>
          </div>
        </div>

        {/* Warranty Information */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Warranty Information</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-600">PCB Warranty Date</label>
              <p className="text-slate-900 font-medium">
                {serial.pcb_warranty_date?.split("T")[0] || "-"}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">Component Warranty Date</label>
              <p className="text-slate-900 font-medium">
                {serial.component_warranty_date?.split("T")[0] || "-"}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">Machine Warranty Date</label>
              <p className="text-slate-900 font-medium">
                {serial.machine_warranty_date?.split("T")[0] || "-"}
              </p>
            </div>
          </div>
        </div>

        {/* Service Information */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Service Information</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-600">Free Service Remaining</label>
              <div className="mt-1 flex items-center gap-2">
                <p className="text-2xl font-bold text-blue-600">{serial.free_service_count}</p>
                <p className="text-sm text-slate-600">services</p>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">Service Consumed</label>
              <div className="mt-1 flex items-center gap-2">
                <p className="text-2xl font-bold text-orange-600">{serial.service_consume_count}</p>
                <p className="text-sm text-slate-600">services</p>
              </div>
            </div>
            <div className="pt-2 border-t border-slate-200">
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{
                    width: `${
                      ((serial.service_consume_count || 0) /
                        ((serial.service_consume_count || 0) + (serial.free_service_count || 0))) *
                      100
                    }%`,
                  }}
                />
              </div>
              <p className="text-xs text-slate-500 mt-2">Service usage progress</p>
            </div>
          </div>
        </div>
      </div>

      {/* Additional Details */}
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Summary</h2>
        <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-slate-900">{serial.serial_no}</p>
            <p className="text-xs text-slate-600 mt-1">Serial Number</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-slate-900">{serial.order_no}</p>
            <p className="text-xs text-slate-600 mt-1">Order Number</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">{serial.free_service_count}</p>
            <p className="text-xs text-slate-600 mt-1">Free Services Left</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-slate-900">{serial.installation_status}</p>
            <p className="text-xs text-slate-600 mt-1">Installation Status</p>
          </div>
        </div>
      </div>
    </div>
  );
}
