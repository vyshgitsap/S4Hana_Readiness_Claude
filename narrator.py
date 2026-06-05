# narrator.py
import os
import re
import anthropic


def generate(results):

    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    # ── Build findings summary ─────────────────────────
    findings_text = ""
    for r in results:
        demo_tag = " [DEMO DATA]" if r.get("demo") else ""
        findings_text += (
            f"\n{'='*50}\n"
            f"Category: {r['category']}{demo_tag}\n"
            f"Status: {r['status']} | Score: {r['score']}/100\n"
            f"Findings:\n"
        )
        for f in r.get("findings", []):
            findings_text += f"  - {f}\n"

    scores = [r.get("score", 50) for r in results]
    overall_score = round(sum(scores) / len(scores))
    critical_count = sum(1 for r in results if r.get("status") == "CRITICAL")
    warning_count = sum(1 for r in results if r.get("status") == "WARNING")

    prompt = f"""
You are an expert SAP Basis consultant reviewing
S/4HANA migration readiness findings.

Overall score: {overall_score}/100
Critical categories: {critical_count}
Warning categories: {warning_count}

Detailed findings:
{findings_text}

Provide THREE sections in exactly this format:

BLOCKER_SUMMARY:
Write exactly 2-3 sentences. Focus only on what is
actively blocking migration from starting. Name the
specific issues, specific counts, and specific risk
if not fixed. No SAP jargon. End with estimated days
to migration-ready if priority actions start today.

ACTION_ITEMS:
For every finding that needs action (skip findings with checkmark,
"confirmed", "meets minimum", "within normal range", "no errors",
"correctly configured", "all active", "all responding"),
provide actions in this exact format:

CAT: <exact category name>
IDX: <finding index number starting from 0>
ACTION: <step 1> → <step 2>

Example:
CAT: System Landscape
IDX: 1
ACTION: Download kernel 785 from SAP Support Portal → Apply via OS level and restart SAP

CAT: Custom Code
IDX: 3
ACTION: Run ATC in SE38 → Assign Priority 1 findings to ABAP team for BSEG remediation

CAT: Interfaces and RFC
IDX: 6
ACTION: Run SM59 → ping PROD_CRM and LEGACY_BI and remove orphaned destinations

Only provide actions for findings that need work.
Maximum 2 steps per action, each step maximum 10 words.

FINDING: <finding text, max 80 chars>
ACTION: <step 1 in plain English> → <step 2 in plain English>

Rules for ACTION:
- Maximum 2 steps separated by →
- Each step maximum 10 words
- Use real SAP transaction codes where relevant
- Examples of good actions:
  "Run SM59 → ping each destination and remove orphaned entries"
  "Assign to ABAP team → fix BSEG direct reads using ACDOCA"
  "Run SU01 → remove SAP_ALL from BATCHUSR1 and LEGACY_INT"
  "Run SM37 → reschedule RBALANCE01 to 19.06.2026 22:00"
  "Run SPAD → delete spool requests older than 30 days"
  "Apply kernel 785 via OS → restart SAP instance"
  "Run SM13 → reprocess or delete all open update records"
  "Raise archiving request → target FI documents pre-2019"

FULL_ANALYSIS:
1. OVERALL STATUS - one line with score
2. EXECUTIVE SUMMARY - 3-4 sentences, no markdown symbols
3. TOP 3 PRIORITY ACTIONS - what, who, why for each
4. CATEGORY BREAKDOWN - one line per category
5. ESTIMATED TIMELINE - days to migration-ready
"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        full_text = response.content[0].text
        blocker = ""
        analysis = full_text
        actions = {}

        # Extract BLOCKER_SUMMARY
        if "BLOCKER_SUMMARY:" in full_text:
            parts = full_text.split("ACTION_ITEMS:")
            blocker = parts[0].replace("BLOCKER_SUMMARY:", "").strip()
            blocker = re.sub(r'[#*-]{2,}', '', blocker).strip()

            if len(parts) > 1:
                action_and_rest = parts[1].split("FULL_ANALYSIS:")
                action_block = action_and_rest[0].strip()
                analysis = (
                    action_and_rest[1].strip()
                    if len(action_and_rest) > 1
                    else ""
                )

               # Parse CAT/IDX/ACTION format
                triples = re.findall(
                    r'CAT:\s*(.+?)\nIDX:\s*(\d+)\nACTION:\s*(.+?)(?=\nCAT:|\Z)',
                    action_block,
                    re.DOTALL
                )
                for cat, idx, action in triples:
                    key = f"{cat.strip()}|{idx.strip()}"
                    clean_action = action.strip().replace('\n', ' ')
                    actions[key] = clean_action
        return {
            "blocker_summary": blocker,
            "full_analysis":   analysis,
            "action_items":    actions
        }

    except Exception as e:
        return {
            "blocker_summary": f"Analysis failed: {str(e)}",
            "full_analysis":   f"Analysis failed: {str(e)}",
            "action_items":    {}
        }
