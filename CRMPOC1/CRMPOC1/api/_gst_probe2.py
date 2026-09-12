import json
import os
import requests

key = os.environ["GST_PROVIDER_API_KEY"]
secret = os.environ["GST_PROVIDER_API_SECRET"]

auth = requests.post(
    "https://api.sandbox.co.in/authenticate",
    headers={"x-api-key": key, "x-api-secret": secret, "x-api-version": "1.0"},
    timeout=20,
)
auth.raise_for_status()
token = auth.json().get("access_token") or (auth.json().get("data") or {}).get("access_token")

# Use a few real-looking / documented GSTINs
gstins = [
    "33ABKCS2033B1ZW",
    "27AACCN0053F1ZW",
    "24AAACS8577K1ZV",
    "29AADCB2230M1ZV",  # common demo
]

urls = [
    "https://api.sandbox.co.in/gst/compliance/public/gstin/search",
    "https://api.sandbox.co.in/gst/compliance/public/gstin/verify",
    "https://api.sandbox.co.in/gsp/public/gstin/search",
]

headers_base = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "x-api-key": key,
    "x-api-version": "1.0",
    "Authorization": token,
}

for url in urls:
    for gstin in gstins[:2]:
        for extra in [{}, {"x-accept-cache": "true"}]:
            headers = {**headers_base, **extra}
            r = requests.post(url, json={"gstin": gstin}, headers=headers, timeout=25)
            print(f"{r.status_code} cache={bool(extra)} {url.split('/')[-2:] } {gstin} :: {r.text[:160]}")
            if r.status_code == 200:
                print("OK", json.dumps(r.json())[:400])
                raise SystemExit(0)

print("DONE no success")
