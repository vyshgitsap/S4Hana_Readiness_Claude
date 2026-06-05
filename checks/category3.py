# checks/category3.py
# Category 3 — Open Items and Consistency Checks

def run_check(rfc_conn=None):

    # ── Demo Mode ──────────────────────────────────────────
    if rfc_conn is None:
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
                ["Open update requests are a hard blocker — must be cleared before SUM starts (SAP Note 2399707)",
                 "Run SM13 → reprocess or delete all open update records with functional team"],
                ["Estimated cleanup time: 2 days with functional team involvement",
                    "Assign functional team lead → plan 2-day SM13 cleanup sprint before transport freeze"],
            ],
            "demo": True
        }

    # ── Live Mode ──────────────────────────────────────────
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
            findings.append(f"Spool requests: {spool_count} — within range ✅")

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
