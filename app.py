# app.py
# S/4HANA Migration Readiness Monitor

import os
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

from checks import (
    category1, category2, category3, category4,
    category5, category6, category7, category8
)
import narrator

app = Flask(__name__)

# ── Connections ────────────────────────────────────────

def get_hana_connection():
    try:
        from hdbcli import dbapi
        conn = dbapi.connect(
            address=os.getenv("HANA_HOST"),
            port=int(os.getenv("HANA_PORT", 30015)),
            user=os.getenv("HANA_USER"),
            password=os.getenv("HANA_PASSWORD")
        )
        return conn
    except Exception:
        return None

def get_rfc_connection():
    try:
        import pyrfc
        conn = pyrfc.Connection(
            ashost=os.getenv("RFC_HOST"),
            sysnr=os.getenv("RFC_SYSNR", "00"),
            client=os.getenv("RFC_CLIENT", "100"),
            user=os.getenv("RFC_USER"),
            passwd=os.getenv("RFC_PASSWORD")
        )
        return conn
    except Exception:
        return None

# ── Normalize findings ─────────────────────────────────

def normalize_results(results):
    """
    Convert [text, action] finding pairs into flat structure.
    Each finding can be:
      - A string: "finding text"
      - A list:   ["finding text", "action text"]
    Output adds finding_actions dict keyed by "catIndex|findingIndex"
    """
    for r in results:
        flat_findings   = []
        finding_actions = {}
        for i, f in enumerate(r.get("findings", [])):
            if isinstance(f, list):
                flat_findings.append(f[0])
                if len(f) > 1 and f[1]:
                    finding_actions[i] = f[1]
            else:
                flat_findings.append(f)
        r["findings"]        = flat_findings
        r["finding_actions"] = finding_actions
    return results

# ── Run all checks ─────────────────────────────────────

def run_all_checks():
    hana_conn = get_hana_connection()
    rfc_conn  = get_rfc_connection()

    results = [
        category1.run_check(rfc_conn),
        category2.run_check(hana_conn),
        category3.run_check(rfc_conn),
        category4.run_check(rfc_conn),
        category5.run_check(rfc_conn),
        category6.run_check(rfc_conn),
        category7.run_check(rfc_conn),
        category8.run_check(rfc_conn),
    ]

    if hana_conn:
        hana_conn.close()
    if rfc_conn:
        rfc_conn.close()

    return normalize_results(results)

# ── Routes ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/report")
def report():
    import traceback
    try:
        results  = run_all_checks()
        narrative = narrator.generate(results)

        if isinstance(narrative, dict):
            blocker_summary = narrative.get("blocker_summary", "")
            full_narrative  = narrative.get("full_analysis", "")
        else:
            blocker_summary = ""
            full_narrative  = str(narrative)

        # Overall score
        scores        = [r.get("score", 50) for r in results]
        overall_score = round(sum(scores) / len(scores))

        # Overall status
        if any(r.get("status") == "CRITICAL" for r in results):
            overall_status = "CRITICAL"
        elif any(r.get("status") == "WARNING" for r in results):
            overall_status = "WARNING"
        else:
            overall_status = "PASS"

        # Demo flag
        demo_mode = any(r.get("demo") for r in results)

        # System info
        system_info = {
            "sid":       "PRD",
            "client":    "100",
            "release":   "SAP ECC 6.0 EHP8",
            "db":        "Oracle 19c",
            "landscape": "D01 \u2192 Q01 \u2192 P01",
            "host":      "sap-prd-app01.internal.corp"
        } if demo_mode else {
            "sid":       os.getenv("RFC_SID", "Unknown"),
            "client":    os.getenv("RFC_CLIENT", "100"),
            "release":   "Live System",
            "db":        "HANA",
            "landscape": "Connected",
            "host":      os.getenv("RFC_HOST", "Unknown")
        }

        # Build flat finding_actions dict keyed by "catIndex|findingIndex"
        finding_actions = {}
        for ci, cat in enumerate(results):
            for fi, act in cat.get("finding_actions", {}).items():
                finding_actions[str(ci) + "|" + str(fi)] = act

        return jsonify({
            "overall_score":   overall_score,
            "overall_status":  overall_status,
            "narrative":       full_narrative,
            "blocker_summary": blocker_summary,
            "categories":      results,
            "finding_actions": finding_actions,
            "demo_mode":       demo_mode,
            "system_info":     system_info,
            "generated_at":    datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        })

    except Exception as e:
        return jsonify({
            "error":     str(e),
            "traceback": traceback.format_exc()
        }), 500

# ── Run ────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
