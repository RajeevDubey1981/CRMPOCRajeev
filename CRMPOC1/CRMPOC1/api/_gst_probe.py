import json
import os
import requests

key = os.environ["GST_PROVIDER_API_KEY"]
secret = os.environ["GST_PROVIDER_API_SECRET"]
url = os.environ.get(
    "GST_PROVIDER_URL",
    "https://api.sandbox.co.in/gst/compliance/public/gstin/search",
)

auth = requests.post(
    "https://api.sandbox.co.in/authenticate",
    headers={"x-api-key": key, "x-api-secret": secret, "x-api-version": "1.0"},
    timeout=20,
)
print("AUTH", auth.status_code, auth.text[:400])
auth.raise_for_status()
body = auth.json()
token = body.get("access_token") or (body.get("data") or {}).get("access_token")
print("TOKEN_LEN", len(token or ""))

gstins = ["05ABNTY3290P8ZB", "29AFSPB9500E1ZY", "33ABKCS2033B1ZW"]
for gstin in gstins:
    for ver in ["1.0", "1.0.0"]:
        for auth_fmt in [token, f"Bearer {token}"]:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": key,
                "x-api-version": ver,
                "Authorization": auth_fmt,
            }
            r = requests.post(url, json={"gstin": gstin}, headers=headers, timeout=20)
            print(
                f"gstin={gstin} ver={ver} bearer={'Y' if auth_fmt.startswith('Bearer') else 'N'} "
                f"-> {r.status_code} {r.text[:220]}"
            )
            if r.status_code == 200:
                print("SUCCESS BODY", json.dumps(r.json())[:500])
                raise SystemExit(0)

print("ALL VARIANTS FAILED")
