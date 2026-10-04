import { useEffect, useRef, useState } from "react";

// Reads barcodes and QR codes from the phone camera. Needs a browser with BarcodeDetector and the CRM opened over https.
export default function CameraScan({ onCode }) {
  const videoRef = useRef(null);
  const last = useRef({ code: "", at: 0 });
  const onCodeRef = useRef(onCode);
  const [err, setErr] = useState("");

  useEffect(() => { onCodeRef.current = onCode; }, [onCode]);

  useEffect(() => {
    let stream = null;
    let timer = null;
    let stopped = false;
    async function start() {
      if (!("BarcodeDetector" in window)) {
        setErr("This browser cannot read barcodes with the camera. Use a barcode scanner or type the serial.");
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (stopped) { stream.getTracks().forEach((t) => t.stop()); return; }
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        const detector = new window.BarcodeDetector();
        const tick = async () => {
          if (stopped) return;
          try {
            const codes = await detector.detect(videoRef.current);
            const now = Date.now();
            if (codes.length && (codes[0].rawValue !== last.current.code || now - last.current.at > 2500)) {
              last.current = { code: codes[0].rawValue, at: now };
              onCodeRef.current(codes[0].rawValue);
            }
          } catch { /* keep scanning */ }
          timer = setTimeout(tick, 350);
        };
        tick();
      } catch {
        setErr("The camera is not available. Allow camera access, and open the CRM over https.");
      }
    }
    start();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };
  }, []);

  if (err) return <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">{err}</div>;
  return <video ref={videoRef} playsInline muted className="h-44 w-full rounded-md bg-slate-900 object-cover" />;
}
