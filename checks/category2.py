# checks/category2.py
# Category 2 — Database and Storage Checks

import os


def run_check(hana_conn=None):
    """
    Checks HANA database health and storage readiness.
    Uses hdbcli connection — works on HANA Express too.
    """

    # ── Demo Mode ──────────────────────────────────────────
    if hana_conn is None:
        return {
            "category": "Database and Storage",
            "status": "CRITICAL",
            "score": 35,
            "findings": [
                ["Free disk space 4.1TB — insufficient for SUM shadow processing",
                    "Raise archiving request with FI/MM teams → archive pre-2019 FI and pre-2020 MM documents"],
                ["Required minimum: 6.9TB (3x current DB size per SAP Note 1793345)",
                 "Monitor disk space daily → confirm 6.9TB available before SUM start"],
                ["Recommendation: Archive FI documents pre-2019 — estimated saving: 1.8TB",
                    "Run SARA → schedule FI document archiving object FI_DOCUMNT"],
                ["Recommendation: Archive MM/SD documents pre-2020 — estimated saving: 0.6TB",
                    "Run SARA → schedule MM document archiving object MM_MATBEL"],
                ["After archiving: 6.5TB available — meets requirement ✅", ""],
                ["BSEG note: Will be replaced by ACDOCA in S/4HANA — expect 40% size reduction post-migration",
                    "Inform ABAP team → update custom reports reading BSEG to use ACDOCA after migration"],
                ["DB growth rate: ~15GB/month — factor into migration timeline planning",
                    "Add 3 months growth buffer to disk sizing → review with DBA team"],
                ["Action: Raise archiving request with functional team — lead time 3-4 weeks",
                    "Contact FI/MM functional leads this week → archiving lead time is 3-4 weeks"],
            ],
            "demo": True
        }

    # ── Live Mode ──────────────────────────────────────────
    try:
        findings = []
        status = "PASS"
        score = 100

        cursor = hana_conn.cursor()

        # Check disk volumes
        cursor.execute("""
            SELECT
                VOLUME_ID,
                USED_SIZE / 1024 / 1024 / 1024 AS USED_GB,
                TOTAL_SIZE / 1024 / 1024 / 1024 AS TOTAL_GB,
                CASE WHEN TOTAL_SIZE > 0
                     THEN ROUND(USED_SIZE * 100.0 / TOTAL_SIZE, 1)
                     ELSE 100
                END AS PCT_USED
            FROM M_VOLUME_FILES
            WHERE FILE_TYPE = 'DATA'
        """)
        volumes = cursor.fetchall()

        for vol in volumes:
            vol_id, used_gb, total_gb, pct = vol
            used_gb = round(float(used_gb or 0), 1)
            total_gb = round(float(total_gb or 0), 1)
            pct = round(float(pct or 0), 1)

            if pct >= 90:
                findings.append(
                    f"CRITICAL: Volume {vol_id} at {pct}% "
                    f"({used_gb}GB / {total_gb}GB)"
                )
                status = "CRITICAL"
                score -= 30
            elif pct >= 75:
                findings.append(
                    f"WARNING: Volume {vol_id} at {pct}% "
                    f"({used_gb}GB / {total_gb}GB)"
                )
                if status != "CRITICAL":
                    status = "WARNING"
                score -= 15
            else:
                findings.append(
                    f"Volume {vol_id}: {pct}% used "
                    f"({used_gb}GB / {total_gb}GB) ✅"
                )

        # Check top 5 largest tables
        cursor.execute("""
            SELECT TOP 5
                TABLE_NAME,
                ROUND(TABLE_SIZE / 1024 / 1024 / 1024, 2) AS SIZE_GB
            FROM M_TABLE_STATISTICS
            WHERE SCHEMA_NAME NOT LIKE '_SYS%'
            ORDER BY TABLE_SIZE DESC
        """)
        large_tables = cursor.fetchall()

        if large_tables:
            findings.append("Top 5 largest tables:")
            for tbl, size_gb in large_tables:
                findings.append(f"  {tbl}: {size_gb}GB")

        # Check HANA services
        cursor.execute("""
            SELECT SERVICE_NAME, ACTIVE_STATUS
            FROM M_SERVICE_STATUS
        """)
        services = cursor.fetchall()

        all_active = all(s[1] == 'YES' for s in services)
        if all_active:
            findings.append(f"All {len(services)} HANA services active ✅")
        else:
            inactive = [s[0] for s in services if s[1] != 'YES']
            findings.append(
                f"CRITICAL: Inactive services: {', '.join(inactive)}")
            status = "CRITICAL"
            score -= 40

        cursor.close()

        return {
            "category": "Database and Storage",
            "status": status,
            "score": max(score, 0),
            "findings": findings,
            "demo": False
        }

    except Exception as e:
        return {
            "category": "Database and Storage",
            "status": "WARNING",
            "score": 50,
            "findings": [f"Could not retrieve live data: {str(e)}"],
            "demo": True
        }
