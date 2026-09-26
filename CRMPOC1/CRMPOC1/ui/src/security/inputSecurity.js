const TEXT_TYPES = new Set(["text", "search", "tel", "url", "email"]);
const ALLOWED_FILE_EXTENSIONS = new Set(["pdf", "doc", "docx", "jpg", "jpeg", "png", "csv"]);
const MAX_FILE_BYTES = 2 * 1024 * 1024;

export function sanitizeTextInput(value) {
  return String(value ?? "")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
    .replace(/<[^>]*>/g, "")
    .replace(/\b(?:javascript|vbscript|data):/gi, "");
}

function handleTextInput(event) {
  const element = event.target;
  if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement)) return;
  if (element instanceof HTMLInputElement && element.type === "password") return;
  if (element instanceof HTMLInputElement && !TEXT_TYPES.has(element.type)) return;

  const sanitized = sanitizeTextInput(element.value);
  if (sanitized !== element.value) {
    const cursor = element.selectionStart;
    element.value = sanitized;
    if (cursor != null) {
      const nextCursor = Math.min(cursor, sanitized.length);
      element.setSelectionRange(nextCursor, nextCursor);
    }
  }
}

function handleFileInput(event) {
  const element = event.target;
  if (!(element instanceof HTMLInputElement) || element.type !== "file") return;
  const file = element.files?.[0];
  if (!file) return;
  const extension = file.name.split(".").pop()?.toLowerCase() || "";
  const invalid = !ALLOWED_FILE_EXTENSIONS.has(extension) || file.size > MAX_FILE_BYTES;
  element.setCustomValidity(invalid ? "Unsupported file type or file exceeds the 2MB limit." : "");
  if (invalid) {
    element.value = "";
    element.reportValidity();
  }
}

export function installInputSecurityGuards() {
  document.addEventListener("input", handleTextInput, true);
  document.addEventListener("change", handleFileInput, true);
}
