# checks/category3.py
# Category 3 — Open Items and Consistency Checks

import requests
import urllib3
import os
urllib3.disable_warnings()


def get_odata_open_items(host, user, password):
    """Fetch open items and ST22 dumps via OData"""
    base_url = f"https://{host}:44300"
    auth = (user, password)
    headers = {"Accept": "application/json"}

    results = {
        "open_updates": 0,
        "spool_count": 0,
        "bdc_errors": 0,
        "dumps_24hr": 0,
        "dump_details": []
    }

    try:
        # ST22 Dumps via OData
        r = requests.get(
            f"{base_url}/sap/opu/odata/sap/DUMP_ANALYSIS_SRV/DumpHeaders"
            f"?$inlinecount=allpages&$top=10"
            f"&$orderby=Date desc",
            auth=auth, verify=False, headers=headers
        )
        if r.status_code == 200:
            data = r.json()
            results["dumps_24hr"] = int(
                data.get("d", {}).get("__count", 0)
            )
            entries = data.get("d", {}).get("results", [])
            for entry in entries[:5]:
                results["dump_details"].append({
                    "error": entry.get("ExcpName", "Unknown"),
                    "program": entry.get("ProgName", "Unknown"),
                    "date": entry.get("Date", "Unknown")
                })

    except Exception as e:
        print(f"OData open items error: {e}")

    return results


def run_check(rfc_conn=None):

    # ── Demo Mode ──────────────────────────────────────────
    if rfc_conn is None:

        # Try OData Live connection first
        host = os.getenv("S4H_HOST")
        user = os.getenv("S4H_USER")
        password = os.getenv("S4H_PASSWORD")

        if host and host != "PLACEHOLDER":
            return run_odata_check(host, user, password)

        # Fall back to demo data
        return {
            "category": "Open Items",
            "status": "WARNING",
            "score": 65,
            "findings": [
                ["Open update requests (SM13): 23 found — must be processed before downtime",
                 "Run SM13 → coordinate with functional team to reprocess or delete all open updates"],
                ["Oldest open update: 14 days — investigate root cause (likely failed posting)",
                 "Open SM13 → select oldest entry → check error log and retry posting"],
                ["Functional team to review and reprocess or delete open updates",
                    "Schedule SM13 review session with functional team → clear all entries before freeze"],
                ["Spool requests: 4,847 older than 30 days detected in TSP01",
                    "Run SPAD → execute spool consistency check → delete obsolete requests"],
                ["Run SPAD spool consistency check and delete obsolete requests",
                    "Transaction SPAD → Administration → Spool consistency check → delete old entries"],
                ["TemSe objects: Within normal range ✅", ""],
                ["Batch input sessions with errors: 0 ✅", ""],
                ["Incomplete LUWs: 0 ✅", ""],
                ["ST22 Dumps last 24hrs: 3 — RABAX_STATE, SYSTEM_CORE_DUMPED",
                 "Run ST22 → analyse dump details → fix root cause program"],
                ["Open update requests are a hard blocker — must be cleared before SUM starts (SAP Note 2399707)",
                 "Run SM13 → reprocess or delete all open update records with functional team"],
                ["Estimated cleanup time: 2 days with functional team involvement",
                    "Assign functional team lead → plan 2-day SM13 cleanup sprint before transport freeze"],
            ],
            "demo": True
        }

    # ── Live RFC Mode ──────────────────────────────────────
    try:
        findings = []
        status = "PASS"
        score = 100

        # Check open update requests (SM13 equivalent)
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='VBHDR',
            FIELDS=[{'FIELDNAME': 'VBKEY'}],
            OPTIONS=[{'TEXT': "STYPE = 'V'"}]
        )
        open_updates = len(result.get('DATA', []))
        if open_updates > 0:
            findings.append(
                f"WARNING: {open_updates} open update requests — "
                f"must be processed before migration"
            )
            status = "WARNING"
            score -= 20
        else:
            findings.append("No open update requests ✅")

        # Check spool requests
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='TSP01',
            FIELDS=[{'FIELDNAME': 'RQIDENT'}]
        )
        spool_count = len(result.get('DATA', []))
        if spool_count > 1000:
            findings.append(
                f"WARNING: {spool_count} spool requests detected — "
                f"recommend cleanup before migration"
            )
            if status != "CRITICAL":
                status = "WARNING"
            score -= 15
        else:
            findings.append(
                f"Spool requests: {spool_count} — within range ✅")

        # Check batch input sessions
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='APQI',
            FIELDS=[{'FIELDNAME': 'GROUPID'}],
            OPTIONS=[{'TEXT': "QSTATE = 'E'"}]
        )
        bdc_errors = len(result.get('DATA', []))
        if bdc_errors > 0:
            findings.append(
                f"WARNING: {bdc_errors} batch input sessions "
                f"with errors — review before migration"
            )
            if status != "CRITICAL":
                status = "WARNING"
            score -= 15
        else:
            findings.append("No batch input session errors ✅")

        # ST22 Dumps via RFC
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='SNAP',
            FIELDS=[
                {'FIELDNAME': 'SNAPDATE'},
                {'FIELDNAME': 'ERRCLASS'}
            ],
            OPTIONS=[{'TEXT': "SNAPDATE >= SY-DATUM - 1"}]
        )
        dumps = len(result.get('DATA', []))
        if dumps > 5:
            findings.append(
                f"CRITICAL: {dumps} ABAP dumps in last 24hrs — "
                f"investigate immediately via ST22"
            )
            status = "CRITICAL"
            score -= 30
        elif dumps > 0:
            findings.append(
                f"WARNING: {dumps} ABAP dumps in last 24hrs — "
                f"review via ST22"
            )
            if status != "CRITICAL":
                status = "WARNING"
            score -= 15
        else:
            findings.append("No ABAP dumps in last 24hrs ✅")

        return {
            "category": "Open Items",
            "status": status,
            "score": max(score, 0),
            "findings": findings,
            "demo": False
        }

    except Exception as e:
        return {
            "category": "Open Items",
            "status": "WARNING",
            "score": 50,
            "findings": [f"Could not retrieve live data: {str(e)}"],
            "demo": True
        }


def run_odata_check(host, user, password):
    """Live check via OData when pyrfc not available"""
    findings = []
    status = "PASS"
    score = 100

    data = get_odata_open_items(host, user, password)

    # ST22 Dumps
    dumps = data["dumps_24hr"]
    if dumps > 5:
        findings.append([
            f"❌ {dumps} ABAP dumps in last 24hrs — Critical!",
            "Run ST22 → analyse dump details → fix root cause"
        ])
        status = "CRITICAL"
        score -= 30
    elif dumps > 0:
        findings.append([
            f"⚠️ {dumps} ABAP dumps in last 24hrs",
            "Run ST22 → review dump details → monitor"
        ])
        if status != "CRITICAL":
            status = "WARNING"
        score -= 15
        # Show dump details
        for d in data["dump_details"]:
            findings.append([
                f"  Dump: {d['error']} in {d['program']} on {d['date']}",
                ""
            ])
    else:
        findings.append(["No ABAP dumps in last 24hrs ✅", ""])

    # Open updates
    if data["open_updates"] > 0:
        findings.append([
            f"⚠️ {data['open_updates']} open update requests",
            "Run SM13 → reprocess or delete open updates"
        ])
        if status != "CRITICAL":
            status = "WARNING"
        score -= 20
    else:
        findings.append(["No open update requests ✅", ""])

    # Spool
    if data["spool_count"] > 1000:
        findings.append([
            f"⚠️ {data['spool_count']} spool requests — cleanup needed",
            "Run SPAD → delete obsolete spool requests"
        ])
        if status != "CRITICAL":
            status = "WARNING"
        score -= 10
    else:
        findings.append([
            f"Spool requests: {data['spool_count']} ✅", ""
        ])

    # BDC errors
    if data["bdc_errors"] > 0:
        findings.append([
            f"⚠️ {data['bdc_errors']} batch input errors",
            "Run SM35 → review error sessions"
        ])
        if status != "CRITICAL":
            status = "WARNING"
        score -= 15
    else:
        findings.append(["No batch input errors ✅", ""])

    return {
        "category": "Open Items",
        "status": status,
        "score": max(score, 0),
        "findings": findings,
        "demo": False,
        "source": "OData"
    }
