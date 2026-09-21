import http.cookiejar
import json
import urllib.error
import urllib.request

BASE = "http://100.84.254.18:8095"
SCRIPT_TAG = "DEMO-WALKTHROUGH-v1"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
RESULTS = []


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


def check(step, ok, detail=""):
    RESULTS.append((step, bool(ok), str(detail)[:220]))
    print(("PASS " if ok else "FAIL ") + step + (" | " + str(detail)[:160] if detail else ""), flush=True)


def main():
    # 1. تسجيل الدخول
    s, login = call("/api/auth/login", {"username": "admin", "password": "Admin@12345678"}, "POST")
    check("1-login", s == 200, f"status={s} user={(login or {}).get('username')}")
    if s != 200:
        return finish(1)
    s, me = call("/api/auth/me")
    check("2-me", s == 200 and (me or {}).get("username") == "admin", f"status={s}")

    # 2. السياق الحالي
    s, years = call("/api/fiscal/years")
    years = years if isinstance(years, list) else []
    check("3-fiscal-years", s == 200, f"count={len(years)}")
    s, journals = call("/api/journals")
    journals = journals if isinstance(journals, list) else []
    check("4-journals", s == 200, f"count={len(journals)}")
    s, tree = call("/api/accounts/tree")
    tree = tree if isinstance(tree, list) else []
    all_acc = {}
    def walk(nodes):
        for n in nodes:
            all_acc[n["code"]] = n
            walk(n.get("children", []))
    walk(tree)
    check("5-accounts-tree", s == 200 and len(all_acc) > 5, f"accounts={len(all_acc)}")
    s, ccs = call("/api/accounts/cost-centers")
    ccs = ccs if isinstance(ccs, list) else []
    s, partners = call("/api/partners")
    partners = partners if isinstance(partners, list) else []

    # 3. مركز تكلفة الديمو
    cc = next((c for c in ccs if c["code"] == "CC-DEMO"), None)
    if cc is None:
        s, cc = call("/api/accounts/cost-centers", {"code": "CC-DEMO", "name": "Demo Project"}, "POST")
        check("6-cc-create", s in (200, 201), f"status={s}")
        cc_id = cc.get("id")
    else:
        check("6-cc-exists", True, cc["code"])
        cc_id = cc["id"]

    # 4. شريك مانح ديمو
    donor = next((p for p in partners if p["code"] == "DON-DEMO"), None)
    if donor is None:
        s, donor = call("/api/partners", {"code": "DON-DEMO", "name": "Demo Donor", "partner_type": "donor"}, "POST")
        check("7-donor-create", s in (200, 201), f"status={s} id={(donor or {}).get('id')}")
    else:
        check("7-donor-exists", True, donor["code"])
    if not isinstance(donor, dict) or not donor.get("id"):
        s, partners = call("/api/partners")
        donor = next((p for p in partners if p["code"] == "DON-DEMO"), {})
    donor_id, cc_id = donor.get("id"), cc_id

    # 5. مشروع الديمو
    s, projs = call("/api/projects")
    projs = projs if isinstance(projs, list) else []
    proj = next((p for p in projs if p["code"] == "PRJ-DEMO-001"), None)
    if proj is None:
        s, proj = call("/api/projects", {
            "code": "PRJ-DEMO-001", "name": "Demo Media Project", "donor_id": donor_id,
            "grant_reference": "DEM-001", "program": "Training", "status": "active",
            "start_date": "2026-01-01", "end_date": "2026-09-30",
            "budget_total": 100000.0, "currency": "EGP",
            "cost_center_id": cc_id, "description": "demo walkthrough",
        }, "POST")
        check("8-project-create", s in (200, 201), f"status={s}")
    else:
        check("8-project-exists", True, proj["code"])
    proj_id = proj.get("id") if isinstance(proj, dict) else None

    return finish(0)


def finish(code=0):
    fails = [r for r in RESULTS if not r[1]]
    print("SUMMARY pass=%d fail=%d" % (len(RESULTS) - len(fails), len(fails)), flush=True)
    for step, ok, detail in RESULTS:
        if not ok:
            print("FAILED:", step, detail, flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
