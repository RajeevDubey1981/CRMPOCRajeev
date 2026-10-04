// Sound and vibration for the scanner: a pleasant two-note beep for a good scan, a lower double buzz for a wrong one.
// The tones are made in the browser, so there is no sound file to load. Phones only allow sound after a tap, so
// unlockAudio() is called from the tap that opens the scanner.

const KEY = "indcool_scan_sound";
let ctx = null;

export function isSoundOn() {
  try { return localStorage.getItem(KEY) !== "off"; } catch { return true; }
}

export function setSoundOn(on) {
  try { localStorage.setItem(KEY, on ? "on" : "off"); } catch { /* storage can be blocked */ }
}

export function unlockAudio() {
  try {
    // On iPhone this lets the tone play even when the ring/silent switch is set to silent
    if (navigator.audioSession) navigator.audioSession.type = "playback";
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    if (!ctx) ctx = new AudioCtx();
    if (ctx.state === "suspended") ctx.resume();
  } catch { /* no audio on this device */ }
}

function tone(freq, start, duration, type = "sine", volume = 0.3) {
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  const t = ctx.currentTime + start;
  osc.type = type;
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(volume, t + 0.015);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + duration);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(t);
  osc.stop(t + duration + 0.03);
}

function buzz(pattern) {
  try { if (navigator.vibrate) navigator.vibrate(pattern); } catch { /* not supported, for example on iPhone */ }
}

export function playSuccess() {
  if (!isSoundOn()) return;
  unlockAudio();
  tone(880, 0, 0.12, "sine", 0.32);
  tone(1320, 0.13, 0.22, "sine", 0.32);
  buzz(70);
}

export function playError() {
  if (!isSoundOn()) return;
  unlockAudio();
  tone(220, 0, 0.18, "square", 0.22);
  tone(165, 0.22, 0.3, "square", 0.22);
  buzz([140, 70, 140]);
}
