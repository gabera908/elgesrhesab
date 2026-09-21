import http.cookiejar
import json
import sys
import urllib.request as u

j = http.cookiejar.CookieJar()
o = u.build_opener(u.HTTPCookieProcessor(j))
o.open(u.Request(
    "http://100.84.254.18:8095/api/auth/login",
    data=json.dumps({"username": "admin", "password": "Admin@12345678"}).encode(),
    headers={"Content-Type": "application/json"},
))
raw = o.open("http://100.84.254.18:8095/api/projects").read().decode()
projs = json.loads(raw)
for p in projs:
    print(p["code"], "| cc_id:", p.get("cost_center_id"), "| cc_name:", p.get("cost_center_name"), "| budget:", p.get("budget_total"))
