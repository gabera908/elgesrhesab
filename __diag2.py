import http.cookiejar
import json
import urllib.error
import urllib.request

BASE = "http://100.84.254.18:8095"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(path, payload=None, method="GET"):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=25) as r:
            body = r.read().decode(errors="replace")
            try:
                return r.status, json.loads(body)
            except ValueError:
                return r.status, body
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


call("/api/auth/login", {"username": "admin", "password": "Admin@12345678"}, "POST")

_, ccs = call("/api/accounts/cost-centers")
cc = next((c for c in ccs if c["code"] == "CC-DEMO"), None)
print("CC-DEMO:", cc["id"] if cc else None)

_, projs = call("/api/projects")
proj = next((p for p in projs if p["code"] == "PRJ-DEMO-001"), None)
print("PRJ before:", proj.get("cost_center_id"), proj.get("cost_center_name"))

s, upd = call(f"/api/projects/{proj['id']}", {"cost_center_id": cc["id"]}, "PUT")
print("PUT link cc:", s, "| cc_id:", (upd or {}).get("cost_center_id"), "| cc_name:", (upd or {}).get("cost_center_name"))

_, projs2 = call("/api/projects")
proj2 = next((p for p in projs2 if p["code"] == "PRJ-DEMO-001"), None)
print("PRJ after persist:", proj2.get("cost_center_id"), proj2.get("cost_center_name"))

pid = proj["id"]
s, gjp = call(f"/api/reports/general-journal?from_date=2026-01-01&to_date=2026-09-30&project_id={pid}")
print("GJ filtered:", s, "entries:", (gjp or {}).get("entries_count"))

s, tbp = call(f"/api/reports/trial-balance?from_date=2026-01-01&to_date=2026-09-30&project_id={pid}")
print("TB filtered:", s, "dr:", (tbp or {}).get("total_period_debit"), "cr:", (tbp or {}).get("total_period_credit"))

s, bs = call("/api/reports/balance-sheet?as_of_date=2026-09-30")
bs = bs or {}
print("BS:", s, "balanced:", bs.get("is_balanced"), "assets:", bs.get("total_assets"))
for sec in (bs.get("assets") or []) + (bs.get("liabilities") or []) + (bs.get("equity") or []):
    print("  section:", sec.get("section"), "total:", sec.get("total"))
    for a in sec.get("accounts", []):
        print("   ", a.get("code"), a.get("name"), "d:", a.get("debit"), "c:", a.get("credit"), "bal:", a.get("balance"))

s, xl = call("/api/export/trial-balance/excel?from_date=2026-01-01&to_date=2026-09-30")
print("EXCEL:", s, str(xl)[:300])
