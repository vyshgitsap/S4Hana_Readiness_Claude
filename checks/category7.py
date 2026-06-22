# checks/category7.py
# Category 7 — Background Job Checks

import requests
import urllib3
import os
urllib3.disable_warnings()


def get_odata_jobs(host, user, password):
    """Fetch background job data via OData"""
    base_url = f"https://{host}:44300"
    auth = (user, password)

    results = {
        "intercepted": 0,
        "running": 0,
        "scheduled": 0,
        "failed": 0
    }

    # Job monitoring via OData
    url = f"{base_url}/sap/opu/odata/sap/JOBMONITORING_SRV/JobHeaders"

    try:
        # Get intercepted jobs
        r = requests.get(
            f"{url}?$filter=Status eq 'INT'&$inlinecount=allpages",
            auth=auth, verify=False,
            headers={"Accept": "application/json"}
        )
        if r.status_code == 200:
            data = r.json()
            results["intercepted"] = int(
                data.get("d", {}).get("__count", 0)
            )

        # Get running jobs
        r = requests.get(
            f"{url}?$filter=Status eq 'R'&$inlinecount=allpages",
            auth=auth, verify=False,
            headers={"Accept": "application/json"}
        )
        if r.status_code == 200:
            data = r.json()
            results["running"] = int(
                data.get("d", {}).get("__count", 0)
            )

        # Get scheduled jobs
        r = requests.get(
            f"{url}?$filter=Status eq 'S'&$inlinecount=allpages",
            auth=auth, verify=False,
            headers={"Accept": "application/json"}
        )
        if r.status_code == 200:
            data = r.json()
            results["scheduled"] = int(
                data.get("d", {}).get("__count", 0)
            )

        # Get failed jobs
        r = requests.get(
            f"{url}?$filter=Status eq 'A'&$inlinecount=allpages",
            auth=auth, verify=False,
            headers={"Accept": "application/json"}
        )
        if r.status_code == 200:
            data = r.json()
            results["failed"] = int(
                data.get("d", {}).get("__count", 0)
            )

    except Exception as e:
        print(f"OData call error: {e}")

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

    # ── Live RFC Mode ──────────────────────────────────────
    try:
        findings = []
        status = "PASS"
        score = 100

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


def run_odata_check(host, user, password):
    """Live check via OData when pyrfc not available"""
    findings = []
    status = "PASS"
    score = 100

    jobs = get_odata_jobs(host, user, password)

    # Intercepted jobs
    if jobs["intercepted"] > 0:
        findings.append([
            f"⚠️ {jobs['intercepted']} jobs in intercepted status",
            "Go to SM37 → investigate intercepted jobs → release or delete"
        ])
        status = "WARNING"
        score -= 20
    else:
        findings.append(["No intercepted jobs ✅", ""])

    # Failed jobs
    if jobs["failed"] > 0:
        findings.append([
            f"❌ {jobs['failed']} jobs in failed/aborted status",
            "Go to SM37 → check failed jobs → restart or reschedule"
        ])
        status = "CRITICAL"
        score -= 30
    else:
        findings.append(["No failed jobs ✅", ""])

    # Running jobs
    findings.append([
        f"Currently running jobs: {jobs['running']}",
        ""
    ])

    # Scheduled jobs
    findings.append([
        f"{jobs['scheduled']} periodic jobs — document for restart checklist",
        "Export from SM37 → include in cutover runbook"
    ])

    if jobs["scheduled"] > 200:
        findings.append([
            f"⚠️ Large number of scheduled jobs ({jobs['scheduled']})",
            "Ensure complete restart checklist before migration"
        ])
        if status != "CRITICAL":
            status = "WARNING"
        score -= 10

    return {
        "category": "Background Jobs",
        "status": status,
        "score": max(score, 0),
        "findings": findings,
        "demo": False,
        "source": "OData"
    }
