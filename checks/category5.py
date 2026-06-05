# checks/category5.py
# Category 5 — Transport System Checks

def run_check(rfc_conn=None):

    # ── Demo Mode ──────────────────────────────────────────
    if rfc_conn is None:
        return {
            "category": "Transport System",
            "status": "WARNING",
            "score": 65,
            "findings": [
                ["STMS landscape: DEV (D01) → QAS (Q01) → PRD (P01) | Domain: PRODDOMAIN",
                 "Document transport landscape in migration runbook → confirm all systems accessible"],
                ["Open transports in QAS import queue: 47",
                    "Run STMS → review queue → import or reject pending transports before freeze"],
                ["12 transports older than 30 days in queue — risk of stale objects",
                    "Run STMS → contact transport owners → resolve or reject stale transports this week"],
                ["Oldest transport: D01K900234 created 45 days ago — investigate delay",
                    "Open SE09 → check transport D01K900234 → contact responsible developer for status"],
                ["3 transports in failed import status — P01K900187, P01K900201, P01K900219",
                    "Run STMS → select failed transports → check import log → reimport or escalate to developer"],
                ["Transport directory (trans/): 67% used — sufficient for migration ✅", ""],
                ["Transport freeze date: Recommended 2 weeks before migration start",
                    "Issue transport freeze notice to all developers → set STMS import lock date"],
                ["Post-freeze rule: Emergency transports only via Change Manager approval",
                    "Document emergency transport process → communicate to all project teams"],
                ["STMS domain controller P01 accessible ✅", ""],
                ["2 transports imported after declared freeze date",
                    "Run STMS → identify post-freeze imports → assess risk with project manager"],
            ],
            "demo": True
        }

    # ── Live Mode ──────────────────────────────────────────
    try:
        findings = []
        status = "PASS"
        score = 100

        # Check transport queue
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='E070',
            FIELDS=[
                {'FIELDNAME': 'TRKORR'},
                {'FIELDNAME': 'TRSTATUS'},
                {'FIELDNAME': 'AS4DATE'}
            ],
            OPTIONS=[{'TEXT': "TRSTATUS = 'D'"}]
        )
        transports = result.get('DATA', [])
        total = len(transports)

        findings.append(f"Total open transports in queue: {total}")

        if total > 50:
            findings.append(
                f"WARNING: {total} open transports — "
                f"recommend reviewing before migration freeze"
            )
            if status != "CRITICAL":
                status = "WARNING"
            score -= 15

        # Check failed imports
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='E070',
            FIELDS=[{'FIELDNAME': 'TRKORR'}],
            OPTIONS=[{'TEXT': "TRSTATUS = 'A'"}]
        )
        failed = len(result.get('DATA', []))
        if failed > 0:
            findings.append(
                f"CRITICAL: {failed} transports with failed "
                f"import status — must resolve before migration"
            )
            status = "CRITICAL"
            score -= 30
        else:
            findings.append("No failed transport imports ✅")

        # Check RFC connection to TMS
        try:
            rfc_conn.call('STMS_API',
                          IV_FUNCTION='GET_DOMAIN_INFO')
            findings.append("STMS domain controller accessible ✅")
        except:
            findings.append(
                "WARNING: Cannot reach STMS domain controller"
            )
            if status != "CRITICAL":
                status = "WARNING"
            score -= 20

        return {
            "category": "Transport System",
            "status": status,
            "score": max(score, 0),
            "findings": findings,
            "demo": False
        }

    except Exception as e:
        return {
            "category": "Transport System",
            "status": "WARNING",
            "score": 50,
            "findings": [f"Could not retrieve live data: {str(e)}"],
            "demo": True
        }
