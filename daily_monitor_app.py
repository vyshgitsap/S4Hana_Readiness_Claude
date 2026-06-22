# daily_monitor_app.py
# Flask wrapper for Daily Monitor — BTP CF deployment

import os
from flask import Flask
from daily_monitor import (
    check_db_health,
    check_background_jobs,
    check_locks,
    check_dumps,
    generate_ai_summary,
    generate_html_report
)

app = Flask(__name__)


@app.route('/')
def index():
    """Main dashboard — runs all checks and returns HTML report"""
    results = [
        check_db_health(),
        check_background_jobs(),
        check_locks(),
        check_dumps()
    ]
    ai_summary = generate_ai_summary(results)
    html = generate_html_report(results, ai_summary)
    return html


@app.route('/health')
def health():
    """Health check endpoint for BTP"""
    return {"status": "ok", "app": "S4HANA Daily Monitor"}, 200


@app.route('/refresh')
def refresh():
    """Force refresh all checks"""
    return index()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
