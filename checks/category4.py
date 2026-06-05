# checks/category4.py
# Category 4 — Custom Code Checks

def run_check(rfc_conn=None):

    # ── Demo Mode ──────────────────────────────────────────
    if rfc_conn is None:
        return {
            "category": "Custom Code",
            "status": "CRITICAL",
            "score": 40,
            "findings": [
                ["847 custom objects found in Z/Y namespace (TADIR scan)",
                 "Run SE16 on TADIR → export full list for project documentation"],
                ["34 objects have Priority 1 findings — will cause dumps in S/4HANA",
                 "Run ATC with S4HANA_READINESS variant → assign Priority 1 findings to ABAP team immediately"],
                ["Most affected: 18 custom FI reports reading BSEG directly — table restructured in S/4HANA",
                 "ABAP team to replace BSEG SELECT statements with ACDOCA Universal Journal reads"],
                ["Most affected: 9 custom MM reports using obsolete function module MB_CREATE_GOODS_MOVEMENT",
                 "ABAP team to replace with BAPI_GOODSMVT_CREATE → retest in sandbox system"],
                ["Most affected: 7 custom programs accessing KNA1/LFA1 — replaced by Business Partner",
                 "ABAP team to update to Business Partner API BUT000 → test in QAS after migration"],
                ["156 objects have Priority 2 findings — behaviour changes requiring testing",
                 "Run ATC → create test cases for all Priority 2 objects → validate in QAS post-migration"],
                ["ATC check variant used: S4HANA_READINESS (transaction ATC)",
                 "Re-run ATC after each fix batch → track remediation progress weekly"],
                ["Remediation progress: 8 of 34 critical findings resolved and transported to QAS",
                 "Daily standup with ABAP team → target 2-3 fixes per day to meet timeline"],
                ["At current pace: remaining 26 critical items resolved in 13 days",
                 "Escalate to project manager → consider adding ABAP resource to accelerate remediation"],
                ["Recommendation: Assign 2 additional ABAP developers to accelerate remediation",
                 "Raise resource request with project manager → target completion by 20.06.2026"],
            ],
            "demo": True
        }

    # ── Live Mode ──────────────────────────────────────────
    try:
        findings = []
        status = "PASS"
        score = 100

        # Count total custom objects
        result = rfc_conn.call(
            'RFC_READ_TABLE',
            QUERY_TABLE='TADIR',
            FIELDS=[{'FIELDNAME': 'OBJ_NAME'}],
            OPTIONS=[{'TEXT': "DEVCLASS LIKE 'Z%' OR DEVCLASS LIKE 'Y%'"}]
        )
        total_custom = len(result.get('DATA', []))
        findings.append(
            f"Total custom objects in Z/Y namespace: {total_custom}")

        # Check ATC findings from readiness check results
        try:
            result = rfc_conn.call(
                'RFC_READ_TABLE',
                QUERY_TABLE='SCMG_T_CHECK_RES',
                FIELDS=[
                    {'FIELDNAME': 'PRIO'},
                    {'FIELDNAME': 'STATUS'}
                ]
            )
            atc_results = result.get('DATA', [])

            critical = sum(
                1 for r in atc_results
                if r.get('WA', '').strip().startswith('1')
            )
            warnings = sum(
                1 for r in atc_results
                if r.get('WA', '').strip().startswith('2')
            )

            if critical > 0:
                findings.append(
                    f"CRITICAL: {critical} Priority 1 findings — "
                    f"will cause runtime dumps in S/4HANA"
                )
                status = "CRITICAL"
                score -= 40
            else:
                findings.append("No critical custom code findings ✅")

            if warnings > 0:
                findings.append(
                    f"WARNING: {warnings} Priority 2 findings — "
                    f"require testing and possible remediation"
                )
                if status != "CRITICAL":
                    status = "WARNING"
                score -= 15
            else:
                findings.append("No custom code warnings ✅")

        except Exception:
            findings.append(
                "ATC results table not found — "
                "run SAP Readiness Check to populate findings"
            )

        return {
            "category": "Custom Code",
            "status": status,
            "score": max(score, 0),
            "findings": findings,
            "demo": False
        }

    except Exception as e:
        return {
            "category": "Custom Code",
            "status": "WARNING",
            "score": 50,
            "findings": [f"Could not retrieve live data: {str(e)}"],
            "demo": True
        }
