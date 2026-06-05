# checks/category8.py
# Category 8 — Interface and RFC Checks

def run_check(rfc_conn=None):

    # ── Demo Mode ──────────────────────────────────────────
    if rfc_conn is None:
        return {
            "category": "Interfaces and RFC",
            "status": "CRITICAL",
            "score": 45,
            "findings": [
                ["34 RFC destinations found in RFCDES",
                    "Run SM59 → document all active destinations in cutover runbook"],
                ["CRITICAL: RFC_ARIBA_PRD unreachable — target ariba-prod.internal.corp not responding",
                    "Run SM59 → ping RFC_ARIBA_PRD → check DNS and network route → contact Ariba team"],
                ["CRITICAL: BI_PRD_REPORTING unreachable — BW system decommissioned, destination orphaned",
                    "Run SM59 → delete BI_PRD_REPORTING → update any programs referencing this destination"],
                ["CRITICAL: LEGACY_HR_SYSTEM unreachable — HR migrated to SuccessFactors in 2023",
                    "Run SM59 → delete LEGACY_HR_SYSTEM → confirm no active interfaces depend on it"],
                ["IDoc errors: 12,847 IDocs in status 51/52 across 6 partner profiles",
                    "Run WE05 → filter by error status → assign to functional team for reprocessing"],
                ["Largest IDoc backlog: Partner ARIBA_VENDOR — 8,234 purchase order IDocs in error",
                    "Run WE20 → check ARIBA_VENDOR partner profile → fix root cause → reprocess in batches"],
                ["IDoc backlog must be cleared before migration — risk of duplicate postings",
                    "Run WE05 daily → track clearance progress → target zero errors before cutover"],
                ["Trusted RFC connections: 4 found — all active ✅", ""],
                ["HTTP/HTTPS connections: 8 found — all responding ✅", ""],
            ],
            "demo": True
        }

    # ── Live Mode ──────────────────────────────────────────
    try:
        findings = []
        status = "PASS"
        score = 100

        # Get all RFC destinations
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='RFCDES',
            FIELDS=[
                {'FIELDNAME': 'RFCDEST'},
                {'FIELDNAME': 'RFCTYPE'}
            ]
        )
        destinations = result.get('DATA', [])
        total_rfc = len(destinations)
        findings.append(f"Total RFC destinations: {total_rfc}")

        # Ping each RFC destination
        unreachable = []
        for dest in destinations[:20]:  # limit to first 20
            dest_name = dest.get('WA', '').split()[0] if dest.get('WA') else ''
            if dest_name:
                try:
                    rfc_conn.call('RFC_PING',
                                  DEST=dest_name)
                except:
                    unreachable.append(dest_name)

        if unreachable:
            findings.append(
                f"CRITICAL: {len(unreachable)} unreachable RFC destinations: "
                f"{', '.join(unreachable[:5])}"
            )
            status = "CRITICAL"
            score -= 30
        else:
            findings.append(
                f"All checked RFC destinations reachable ✅"
            )

        # Check IDoc errors
        try:
            result = rfc_conn.call(
                'RFC_READ_TABLE',
                QUERY_TABLE='EDIDS',
                FIELDS=[{'FIELDNAME': 'DOCNUM'}],
                OPTIONS=[{'TEXT': "STATUS = '51' OR STATUS = '52'"}]
            )
            idoc_errors = len(result.get('DATA', []))

            if idoc_errors > 1000:
                findings.append(
                    f"CRITICAL: {idoc_errors:,} IDocs in error status — "
                    f"must be cleared before migration to prevent data loss"
                )
                status = "CRITICAL"
                score -= 30
            elif idoc_errors > 0:
                findings.append(
                    f"WARNING: {idoc_errors} IDocs in error status — "
                    f"review before migration"
                )
                if status != "CRITICAL":
                    status = "WARNING"
                score -= 15
            else:
                findings.append("No IDoc errors detected ✅")

        except:
            findings.append(
                "IDoc status check skipped — "
                "EDIDS table not accessible"
            )

        return {
            "category": "Interfaces and RFC",
            "status": status,
            "score": max(score, 0),
            "findings": findings,
            "demo": False
        }

    except Exception as e:
        return {
            "category": "Interfaces and RFC",
            "status": "WARNING",
            "score": 50,
            "findings": [f"Could not retrieve live data: {str(e)}"],
            "demo": True
        }
