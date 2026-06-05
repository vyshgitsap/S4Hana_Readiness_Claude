# checks/category1.py
# Category 1 — System Landscape Checks

import os


def run_check(rfc_conn=None):
    """
    Checks SAP system landscape prerequisites for S/4HANA migration.
    Returns demo data if no RFC connection available.
    """

    # ── Demo Mode ─────────────────────────────────────────
    if rfc_conn is None:
        return {
            "category": "System Landscape",
            "status": "WARNING",
            "score": 70,
            "findings": [
                ["System: PRD | SAP ECC 6.0 EHP8 | Landscape: D01 → Q01 → P01",
                    "Document system details in migration runbook → confirm with project manager"],
                ["Kernel release: 753 patch 900 — below minimum 785 for S/4HANA 2023 — upgrade required before SUM (SAP Note 2399707)",
                 "Download kernel 785 from SAP Support Portal → apply via OS level and restart SAP"],
                ["Unicode: Active ✅", ""],
                ["Stack: Single ABAP stack — no dual stack split required ✅", ""],
                ["Oracle 19c Enterprise Edition — DMO required to migrate DB to HANA during conversion",
                    "Confirm DMO path in Maintenance Planner → size HANA target system accordingly"],
                ["OS: Red Hat Enterprise Linux 8.6 — supported for S/4HANA ✅", ""],
                ["Support Package: SAPKH60811 — meets minimum requirement ✅", ""],
                ["Installed Add-ons: 3 detected — compatibility check required (see Category details)",
                 "Run SAINT → check each add-on against S/4HANA compatibility list on SAP Support Portal"]

            ],
            "demo": True
        }

    # ── Live Mode ──────────────────────────────────────────
    try:
        findings = []
        status = "PASS"
        score = 100

        # Get system info via RFC
        sys_info = rfc_conn.call('RFC_SYSTEM_INFO')

        kernel = sys_info.get('RFCSI_EXPORT', {}).get('RFCKERNRL', 'Unknown')
        sysid = sys_info.get('RFCSI_EXPORT', {}).get('RFCSYSID', 'Unknown')
        db_system = sys_info.get('RFCSI_EXPORT', {}).get('RFCDBSYS', 'Unknown')
        unicode = sys_info.get('RFCSI_EXPORT', {}).get('RFCUNICOD', '')

        findings.append(f"System ID: {sysid}")
        findings.append(f"Kernel release: {kernel}")

        # Unicode check
        if unicode == 'U':
            findings.append("Unicode system confirmed ✅")
        else:
            findings.append(
                "CRITICAL: Non-unicode system — must convert to unicode before migration")
            status = "CRITICAL"
            score -= 40

        # Database check
        if db_system == 'HDB':
            findings.append("Database: SAP HANA — no DMO required ✅")
        else:
            findings.append(
                f"WARNING: Database is {db_system} — DMO required during migration")
            if status != "CRITICAL":
                status = "WARNING"
            score -= 20

        # Kernel version check (minimum 785 for S/4HANA 2023)
        try:
            kernel_int = int(kernel)
            if kernel_int >= 785:
                findings.append(f"Kernel {kernel} meets minimum requirement ✅")
            else:
                findings.append(
                    f"WARNING: Kernel {kernel} below minimum 785 — upgrade required")
                if status != "CRITICAL":
                    status = "WARNING"
                score -= 15
        except:
            findings.append(
                f"Kernel version {kernel} — manual verification required")

        return {
            "category": "System Landscape",
            "status": status,
            "score": max(score, 0),
            "findings": findings,
            "demo": False
        }

    except Exception as e:
        # If RFC call fails fall back to demo
        return {
            "category": "System Landscape",
            "status": "WARNING",
            "score": 50,
            "findings": [f"Could not retrieve live data: {str(e)}", "Showing demo data"],
            "demo": True
        }
