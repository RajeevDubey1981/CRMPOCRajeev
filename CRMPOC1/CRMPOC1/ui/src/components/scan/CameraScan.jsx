import { useEffect, useRef, useState } from "react";

// Live barcode and QR reading with the phone camera. Point it at the code and it reads by itself, no photo needed.
// Chrome on Android has a built-in reader. iPhone browsers do not, so a bundled reader (ZXing) is loaded when needed.
// If the live camera is blocked (some in-app browsers do that), "Take a photo" still works in every mobile browser.
export default function CameraScan({ onCode }) {
  const videoRef = useRef(null);
  const last = useRef({ code: "", at: 0 });
  const onCodeRef = useRef(onCode);
  const [err, setErr] = useState("");
  const [ready, setReady] = useState(false);
  const [photoMsg, setPhotoMsg] = useState("");

  useEffect(() => { onCodeRef.current = onCode; }, [onCode]);

  function emit(raw) {
    const now = Date.now();
    // the same code seen again while the camera is still pointed at it is not a new scan
    if (raw && (raw !== last.current.code || now - last.current.at > 4000)) {
      last.current = { code: raw, at: now };
      onCodeRef.current(raw);
    } else if (raw === last.current.code) {
      last.current.at = now;
    }
  }

  useEffect(() => {
    let stream = null;
    let timer = null;
    let controls = null;
    let stopped = false;
    const constraints = { video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } } };

    async function startNative() {
      stream = await navigator.mediaDevices.getUserMedia(constraints);
      if (stopped) { stream.getTracks().forEach((t) => t.stop()); return; }
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      setReady(true);
      const detector = new window.BarcodeDetector();
      const tick = async () => {
        if (stopped) return;
        try {
          const codes = await detector.detect(videoRef.current);
          if (codes.length) emit(codes[0].rawValue);
        } catch { /* keep scanning */ }
        timer = setTimeout(tick, 250);
      };
      tick();
    }

    async function startReader() {
      const [{ BrowserMultiFormatReader }, { DecodeHintType }] = await Promise.all([
        import("@zxing/browser"),
        import("@zxing/library"),
      ]);
      const hints = new Map([[DecodeHintType.TRY_HARDER, true]]);
      const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: 150 });
      const handle = await reader.decodeFromConstraints(
        constraints,
        videoRef.current,
        (result) => { if (result && !stopped) emit(result.getText()); },
      );
      if (stopped) { handle.stop(); return; }
      controls = handle;
      setReady(true);
    }

    (async () => {
      try {
        if ("BarcodeDetector" in window) await startNative(); else await startReader();
      } catch {
        if (!stopped) setErr("The live camera is not available in this browser. Open the CRM in Safari or Chrome and allow the camera, or take a photo of the barcode below.");
      }
    })();

    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      if (controls) controls.stop();
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };
  }, []);

  async function onPhoto(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setPhotoMsg("Reading the photo...");
    const url = URL.createObjectURL(file);
    try {
      const [{ BrowserMultiFormatReader }, { DecodeHintType }] = await Promise.all([
        import("@zxing/browser"),
        import("@zxing/library"),
      ]);
      const hints = new Map([[DecodeHintType.TRY_HARDER, true]]);
      const result = await new BrowserMultiFormatReader(hints).decodeFromImageUrl(url);
      setPhotoMsg("");
      last.current = { code: "", at: 0 };
      onCodeRef.current(result.getText());
    } catch {
      setPhotoMsg("No barcode could be read from that photo. Move closer, keep it sharp and well lit, and try again.");
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  return (
    <div className="space-y-2">
      {err ? (
        <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">{err}</div>
      ) : (
        <div className="relative overflow-hidden rounded-md bg-slate-900">
          <video ref={videoRef} playsInline muted className="h-52 w-full object-cover" />
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="h-24 w-4/5 rounded-md border-2 border-emerald-400/80">
              <div className="mt-[44px] h-0.5 w-full bg-rose-500/80" />
            </div>
          </div>
          <div className="pointer-events-none absolute bottom-1 left-0 right-0 text-center text-xs text-white/90">
            {ready ? "Point at the barcode. It reads by itself." : "Starting the camera..."}
          </div>
        </div>
      )}
      <label className="inline-flex cursor-pointer items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50">
        {err ? "Take a photo of the barcode" : "Or take a photo instead"}
        <input type="file" accept="image/*" capture="environment" className="hidden" onChange={onPhoto} />
      </label>
      {photoMsg && <p className="text-sm text-slate-600">{photoMsg}</p>}
    </div>
  );
}
