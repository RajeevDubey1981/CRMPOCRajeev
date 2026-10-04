import { useEffect, useRef, useState } from "react";

// Reads barcodes and QR codes with the phone camera.
// Chrome on Android has a built-in reader. iPhone browsers do not, so a bundled reader (ZXing) is loaded when it is needed.
// If the live camera is blocked (some in-app browsers do that), "Take a photo" still works in every mobile browser.
export default function CameraScan({ onCode }) {
  const videoRef = useRef(null);
  const last = useRef({ code: "", at: 0 });
  const onCodeRef = useRef(onCode);
  const [err, setErr] = useState("");
  const [photoMsg, setPhotoMsg] = useState("");

  useEffect(() => { onCodeRef.current = onCode; }, [onCode]);

  function emit(raw) {
    const now = Date.now();
    if (raw && (raw !== last.current.code || now - last.current.at > 2500)) {
      last.current = { code: raw, at: now };
      onCodeRef.current(raw);
    }
  }

  useEffect(() => {
    let stream = null;
    let timer = null;
    let controls = null;
    let stopped = false;

    async function startNative() {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      if (stopped) { stream.getTracks().forEach((t) => t.stop()); return; }
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      const detector = new window.BarcodeDetector();
      const tick = async () => {
        if (stopped) return;
        try {
          const codes = await detector.detect(videoRef.current);
          if (codes.length) emit(codes[0].rawValue);
        } catch { /* keep scanning */ }
        timer = setTimeout(tick, 350);
      };
      tick();
    }

    async function startReader() {
      const { BrowserMultiFormatReader } = await import("@zxing/browser");
      const reader = new BrowserMultiFormatReader(undefined, { delayBetweenScanAttempts: 250 });
      const handle = await reader.decodeFromConstraints(
        { video: { facingMode: { ideal: "environment" } } },
        videoRef.current,
        (result) => { if (result && !stopped) emit(result.getText()); },
      );
      if (stopped) handle.stop(); else controls = handle;
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
      const { BrowserMultiFormatReader } = await import("@zxing/browser");
      const result = await new BrowserMultiFormatReader().decodeFromImageUrl(url);
      setPhotoMsg("");
      onCodeRef.current(result.getText());
    } catch {
      setPhotoMsg("No barcode could be read from that photo. Move closer, keep it sharp and well lit, and try again.");
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  return (
    <div className="space-y-2">
      {err
        ? <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">{err}</div>
        : <video ref={videoRef} playsInline muted className="h-44 w-full rounded-md bg-slate-900 object-cover" />}
      <label className="inline-flex cursor-pointer items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
        Take a photo of the barcode
        <input type="file" accept="image/*" capture="environment" className="hidden" onChange={onPhoto} />
      </label>
      {photoMsg && <p className="text-sm text-slate-600">{photoMsg}</p>}
    </div>
  );
}
