# checks/category6.py
# Category 6 — User and Security Checks

def run_check(rfc_conn=None):

    # ── Demo Mode ──────────────────────────────────────────
    if rfc_conn is None:
        return {
            "category": "Users and Security",
            "status": "CRITICAL",
            "score": 50,
            "findings": [
                ["2 dialog users found with SAP_ALL profile in PRD — BATCHUSR1, LEGACY_INT",
                    "Run SU01 → remove SAP_ALL from BATCHUSR1 and LEGACY_INT → assign minimum required roles"],
                ["Action: Remove SAP_ALL immediately — security audit finding, blocks go-live sign-off",
                    "Run SUIM → identify minimum required authorisations → replace SAP_ALL with scoped roles"],
                ["SAP* password: Confirmed known and documented in migration runbook ✅", ""],
                ["DDIC password: Confirmed known and documented in migration runbook ✅", ""],
                ["Emergency migration user MIGADMIN_BASIS: Created, tested, documented ✅", ""],
                ["RFC service user RFC_ARIBA password expires in 18 days",
                    "Run SU01 → reset RFC_ARIBA password → update SM59 destination with new credentials"],
                ["Action: Reset RFC_ARIBA password and update SM59 destination before migration",
                    "Run SU01 for password reset → run SM59 → test RFC connection after update"],
                ["12 dialog users have password validity ending during migration window",
                    "Run SUIM → identify expiring users → extend validity or confirm inactive status"],
                ["Background job user BATCH_FI: Active, authorisations validated ✅", ""],
                ["Total locked users: 47 — verified as intentionally locked test/legacy accounts ✅", ""],
            ],
            "demo": True
        }

    # ── Live Mode ──────────────────────────────────────────
    try:
        findings = []
        status = "PASS"
        score = 100

        # Check for SAP_ALL profiles in production
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='UST04',
            FIELDS=[
                {'FIELDNAME': 'BNAME'},
                {'FIELDNAME': 'PROFILE'}
            ],
            OPTIONS=[{'TEXT': "PROFILE = 'SAP_ALL'"}]
        )
        sap_all_users = result.get('DATA', [])

        if sap_all_users:
            findings.append(
                f"CRITICAL: {len(sap_all_users)} users have SAP_ALL "
                f"profile — security risk, must remove before go-live"
            )
            status = "CRITICAL"
            score -= 30
        else:
            findings.append("No users with SAP_ALL profile ✅")

        # Check locked users
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='USR02',
            FIELDS=[
                {'FIELDNAME': 'BNAME'},
                {'FIELDNAME': 'UFLAG'}
            ],
            OPTIONS=[{'TEXT': "UFLAG <> '0'"}]
        )
        locked = len(result.get('DATA', []))
        if locked > 0:
            findings.append(
                f"INFO: {locked} locked users found — "
                f"verify service users are not locked"
            )
        else:
            findings.append("No unexpectedly locked users ✅")

        # Check password expiry — users expiring soon
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='USR02',
            FIELDS=[
                {'FIELDNAME': 'BNAME'},
                {'FIELDNAME': 'GLTGB'}
            ],
            OPTIONS=[{'TEXT': "GLTGB <> '00000000'"}]
        )
        expiring = result.get('DATA', [])
        if expiring:
            findings.append(
                f"WARNING: {len(expiring)} users have validity end dates set — "
                f"verify none expire during migration window"
            )
            if status != "CRITICAL":
                status = "WARNING"
            score -= 15
        else:
            findings.append("No user validity expiry concerns ✅")

        return {
            "category": "Users and Security",
            "status": status,
            "score": max(score, 0),
            "findings": findings,
            "demo": False
        }

    except Exception as e:
        return {
            "category": "Users and Security",
            "status": "WARNING",
            "score": 50,
            "findings": [f"Could not retrieve live data: {str(e)}"],
            "demo": True
        }
