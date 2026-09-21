import http.cookiejar
import json
import urllib.error
import urllib.request

BASE = "http://100.84.254.18:8095"

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


def finish(code=0):
    fails = [r for r in RESULTS if not r[1]]
    print("SUMMARY pass=%d fail=%d" % (len(RESULTS) - len(fails), len(fails)), flush=True)
    for step, ok, detail in RESULTS:
        if not ok:
            print("FAILED:", step, detail, flush=True)
    return code


def part1():
    s, body = call("/health")
    check("0-health", s == 200 and (body or {}).get("status") == "healthy", f"status={s}")
    s, login = call("/api/auth/login", {"username": "admin", "password": "Admin@12345678"}, "POST")
    check("1-login", s == 200, f"status={s}")
    if s != 200:
        return finish(1)
    s, me = call("/api/auth/me")
    check("2-me", s == 200 and (me or {}).get("username") == "admin", f"status={s}")
    s, tree = call("/api/accounts/tree")
    tree = tree if isinstance(tree, list) else []
    all_acc = {}
    def walk(nodes):
        for n in nodes:
            all_acc[n["code"]] = n
            walk(n.get("children", []))
    walk(tree)
    check("3-accounts-tree", s == 200 and len(all_acc) > 5, f"accounts={len(all_acc)}")
    s, years = call("/api/fiscal/years")
    years = years if isinstance(years, list) else []
    check("4-fiscal-years", s == 200, f"count={len(years)}")
    s, journals = call("/api/journals")
    journals = journals if isinstance(journals, list) else []
    check("5-journals", s == 200 and len(journals) >= 6, f"count={len(journals)}")
    s, ccs = call("/api/accounts/cost-centers")
    ccs = ccs if isinstance(ccs, list) else []
    s, partners = call("/api/partners")
    partners = partners if isinstance(partners, list) else []
    cc = next((c for c in ccs if c["code"] == "CC-DEMO"), None)
    if cc is None:
        s, cc = call("/api/accounts/cost-centers", {"code": "CC-DEMO", "name": "Demo Project"}, "POST")
        check("6-cc-create", s in (200, 201), f"status={s}")
        cc_id = cc.get("id") if isinstance(cc, dict) else None
    else:
        check("6-cc-exists", True, cc["code"])
        cc_id = cc["id"]
    donor = next((p for p in partners if p["code"] == "DON-DEMO"), None)
    if donor is None:
        s, donor = call("/api/partners", {"code": "DON-DEMO", "name": "Demo Donor", "partner_type": "donor"}, "POST")
        check("7-donor-create", s in (200, 201), f"status={s}")
    else:
        check("7-donor-exists", True, donor["code"])
    if not isinstance(donor, dict) or not donor.get("id"):
        s, partners = call("/api/partners")
        donor = next((p for p in partners if p["code"] == "DON-DEMO"), {})
    donor_id = donor.get("id")
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
    return proj, donor_id, cc_id, all_acc, journals


def part2(proj, donor_id, cc_id, all_acc, journals):
    s, entries = call("/api/journal-entries?limit=100")
    entries = entries if isinstance(entries, list) else []
    demo_refs = {"DEM-W-001", "DEM-W-002", "DEM-W-003"}
    have = {e.get("reference") for e in entries}
    missing = sorted(demo_refs - have)
    jmap = {j["code"]: j for j in journals}
    cash, exp, bank = all_acc.get("1.1.1"), all_acc.get("5.1.1"), all_acc.get("1.1.2.1")
    if missing and not (cash and exp and bank and jmap.get("CSH") and jmap.get("BNK")):
        check("9-entries-deps", False, "missing accounts/journals")
    else:
        created = []

        def mk(journal_code, entry_date, ref, narr, pairs):
            lines = []
            for acc, d, c in pairs:
                lines.append({"account_id": acc["id"], "debit": d, "credit": c, "name": narr, "cost_center_id": cc_id})
            return {"journal_id": jmap[journal_code]["id"], "entry_date": entry_date,
                    "reference": ref, "narration": narr, "lines": lines}

        specs = {
            "DEM-W-001": mk("CSH", "2026-09-05", "DEM-W-001", "Training cash", [(exp, 5000.0, 0.0), (cash, 0.0, 5000.0)]),
            "DEM-W-002": mk("BNK", "2026-09-12", "DEM-W-002", "Donor bank", [(bank, 20000.0, 0.0), (cash, 0.0, 20000.0)]),
            "DEM-W-003": mk("CSH", "2026-09-20", "DEM-W-003", "Supplies", [(exp, 2500.0, 0.0), (cash, 0.0, 2500.0)]),
        }
        for ref in missing:
            s, created_e = call("/api/journal-entries", specs[ref], "POST")
            if s == 201 and isinstance(created_e, dict):
                s2, _ = call(f"/api/journal-entries/{created_e['id']}/submit-review", {}, "POST")
                s3, _ = call(f"/api/journal-entries/{created_e['id']}/post", {}, "POST")
                created.append((ref, s, s2, s3))
        check("9-entries-posted", all(x[3] == 200 for x in created) or not missing,
              f"posted={len([x for x in created if x[3] == 200])}")
    s, entries = call("/api/journal-entries?limit=100")
    entries = entries if isinstance(entries, list) else []
    posted_demo = [e for e in entries if e.get("reference") in demo_refs and e.get("state") == "posted"]
    check("10-posted-demo", len(posted_demo) >= 2, f"posted_demo={len(posted_demo)}")

    s, gj = call("/api/reports/general-journal?from_date=2026-01-01&to_date=2026-09-30")
    check("11-general-journal", s == 200, f"entries={(gj or {}).get('entries_count')}")
    proj_id = proj.get("id") if isinstance(proj, dict) else None
    if proj_id:
        s, gjp = call(f"/api/reports/general-journal?from_date=2026-01-01&to_date=2026-09-30&project_id={proj_id}")
        check("12-gj-project", s == 200 and (gjp or {}).get("entries_count", 0) > 0,
              f"entries={(gjp or {}).get('entries_count')}")
        s, tbp = call(f"/api/reports/trial-balance?from_date=2026-01-01&to_date=2026-09-30&project_id={proj_id}")
        tbp = tbp if isinstance(tbp, dict) else {}
        ok2 = s == 200 and float(tbp.get("total_period_debit") or 0) == float(tbp.get("total_period_credit") or 0)
        check("13-tb-project", ok2, f"dr={tbp.get('total_period_debit')} cr={tbp.get('total_period_credit')}")
        budget = float((proj or {}).get("budget_total") or 0)
        actual = float(tbp.get("total_period_debit") or 0)
        check("14-budget-actual", budget > 0, f"budget={budget} actual={actual} remaining={budget - actual}")

    pages = [
        ("15-trial-balance", "/api/reports/trial-balance?from_date=2026-01-01&to_date=2026-09-30"),
        ("16-income-statement", "/api/reports/income-statement?from_date=2026-01-01&to_date=2026-09-30"),
        ("17-balance-sheet", "/api/reports/balance-sheet?as_of_date=2026-09-30"),
        ("18-cash-flow", "/api/reports/cash-flow?from_date=2026-01-01&to_date=2026-09-30"),
        ("19-american-journal", "/api/reports/american-journal?from_date=2026-01-01&to_date=2026-09-30"),
        ("20-cc-trial", "/api/reports/extra/cost-center-trial-balance?from_date=2026-01-01&to_date=2026-09-30"),
        ("21-partner-statement", f"/api/reports/extra/partner-statement?partner_id={donor_id}&from_date=2026-01-01&to_date=2026-09-30"),
        ("22-income-comparison", "/api/reports/extra/income-comparison?from_date=2026-01-01&to_date=2026-09-30"),
    ]
    for step, path in pages:
        s, body = call(path)
        detail = f"status={s}"
        if s == 200 and isinstance(body, dict):
            if body.get("is_balanced") is not None:
                detail += f" balanced={body.get('is_balanced')}"
            if body.get("entries_count") is not None:
                detail += f" entries={body.get('entries_count')}"
            if body.get("total_period_debit") is not None:
                detail += f" dr={body.get('total_period_debit')}"
            if body.get("net_profit") is not None:
                detail += f" net={body.get('net_profit')}"
        check(step, s == 200, detail)
    s, bs = call("/api/reports/balance-sheet?as_of_date=2026-09-30")
    check("23-bs-balanced", s == 200 and (bs or {}).get("is_balanced") is True,
          f"assets={(bs or {}).get('total_assets')}")
    s, csv_body = call("/api/export/trial-balance/csv?from_date=2026-01-01&to_date=2026-09-30")
    check("24-export-csv", s == 200 and "الكود" in str(csv_body), f"status={s}")
    s, xls_body = call("/api/export/trial-balance/excel?from_date=2026-01-01&to_date=2026-09-30")
    check("25-export-excel", s == 200 and len(str(xls_body)) > 1000, f"status={s}")


if __name__ == "__main__":
    data = part1()
    if data:
        part2(*data)
    finish(0)
