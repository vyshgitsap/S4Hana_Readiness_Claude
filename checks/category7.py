# checks/category7.py
# Category 7 — Background Job Checks

def run_check(rfc_conn=None):

    # ── Demo Mode ──────────────────────────────────────────
    if rfc_conn is None:
        return {
            "category": "Background Jobs",
            "status": "WARNING",
            "score": 60,
            "findings": [
                ["4 jobs scheduled during proposed migration window",
                    "Run SM37 → identify all jobs in migration window → coordinate reschedule with functional teams"],
                ["Monthly FI closing job RBALANCE01 scheduled 20.06.2026 23:00 — conflicts with migration start",
                    "Run SM37 → reschedule RBALANCE01 to 19.06.2026 → confirm with FI team lead"],
                ["Payroll run RPCALCD0 scheduled 21.06.2026 02:00 — within downtime window",
                    "Run SM37 → reschedule RPCALCD0 → coordinate with HR team on new payroll run date"],
                ["2 jobs currently in intercepted status — RBDAPP01, RSARFCEX",
                    "Run SM37 → select intercepted jobs → investigate root cause → release or delete"],
                ["127 periodic jobs documented for post-migration restart checklist",
                    "Export job list from SM37 → include in cutover runbook with restart sequence"],
                ["No jobs in active error status ✅", ""],
                ["Job server group configuration: Valid ✅", ""],
            ],
            "demo": True
        }

    # ── Live Mode ──────────────────────────────────────────
    try:
        findings = []
        status = "PASS"
        score = 100

        # Check for active/intercepted jobs
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='TBTCO',
            FIELDS=[
                {'FIELDNAME': 'JOBNAME'},
                {'FIELDNAME': 'STATUS'}
            ],
            OPTIONS=[{'TEXT': "STATUS = 'INT'"}]
        )
        intercepted = len(result.get('DATA', []))
        if intercepted > 0:
            findings.append(
                f"WARNING: {intercepted} jobs in intercepted status — "
                f"requires investigation before migration"
            )
            if status != "CRITICAL":
                status = "WARNING"
            score -= 20
        else:
            findings.append("No intercepted jobs ✅")

        # Check currently running jobs
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='TBTCO',
            FIELDS=[
                {'FIELDNAME': 'JOBNAME'},
                {'FIELDNAME': 'STATUS'}
            ],
            OPTIONS=[{'TEXT': "STATUS = 'R'"}]
        )
        running = len(result.get('DATA', []))
        findings.append(f"Currently running jobs: {running}")

        # Check total scheduled jobs
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='TBTCO',
            FIELDS=[{'FIELDNAME': 'JOBNAME'}],
            OPTIONS=[{'TEXT': "STATUS = 'S'"}]
        )
        scheduled = len(result.get('DATA', []))
        findings.append(
            f"{scheduled} periodic jobs — "
            f"document for post-migration restart checklist"
        )

        if scheduled > 200:
            findings.append(
                f"WARNING: Large number of scheduled jobs ({scheduled}) — "
                f"ensure restart checklist is complete"
            )
            if status != "CRITICAL":
                status = "WARNING"
            score -= 10

        return {
            "category": "Background Jobs",
            "status": status,
            "score": max(score, 0),
            "findings": findings,
            "demo": False
        }

    except Exception as e:
        return {
            "category": "Background Jobs",
            "status": "WARNING",
            "score": 50,
            "findings": [f"Could not retrieve live data: {str(e)}"],
            "demo": True
        }
