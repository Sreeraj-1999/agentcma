"""
Marine Diagnostic Agent — Streamlit UI

Usage:
    streamlit run app.py
"""

import sys
sys.path.insert(0, ".")

import streamlit as st
import json
from orchestrator.graph import run_diagnostic
from agents.base_agent import BaseAgent
from agents.telemetry_agent import TelemetryAgent
from datamarts.executor import list_datamarts

# ─── Page Config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Marine Diagnostic Agent",
    page_icon="🚢",
    layout="wide",
)

# ─── Custom CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .main-header p {
        margin: 0.3rem 0 0 0;
        opacity: 0.8;
        font-size: 0.95rem;
    }

    .datamart-card {
        background: #1a1a2e;
        border: 1px solid #2a2a4e;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .datamart-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(44, 83, 100, 0.3);
    }
    .datamart-card .dm-name {
        font-weight: 600;
        font-size: 0.95rem;
        color: #64b5f6;
        margin-bottom: 0.3rem;
    }
    .datamart-card .dm-source {
        font-size: 0.7rem;
        color: #81c784;
        background: rgba(129, 199, 132, 0.15);
        padding: 2px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 0.4rem;
    }
    .datamart-card .dm-desc {
        font-size: 0.82rem;
        color: #b0b8c8;
        line-height: 1.4;
    }

    .result-card {
        background: #0d1b2a;
        border: 1px solid #1e3a5f;
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 0.5rem;
    }

    .step-card {
        background: #111827;
        border: 1px solid #1e3a5f;
        border-left: 3px solid #64b5f6;
        border-radius: 0 8px 8px 0;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .step-card.condition-true {
        border-left-color: #81c784;
    }
    .step-card.condition-false {
        border-left-color: #e57373;
    }

    .alert-card {
        background: linear-gradient(135deg, #1a237e 0%, #b71c1c 100%);
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-top: 1rem;
        color: white;
    }

    .stat-box {
        background: #111827;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
    }
    .stat-box .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #64b5f6;
    }
    .stat-box .stat-label {
        font-size: 0.75rem;
        color: rgba(255,255,255,0.5);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stTextArea textarea {
        background: #0e1525 !important;
        border: 1px solid rgba(100, 181, 246, 0.2) !important;
        border-radius: 10px !important;
        color: #e0e6ed !important;
        font-family: 'Inter', monospace !important;
        font-size: 0.9rem !important;
    }
    .stTextArea textarea::placeholder {
        color: rgba(255,255,255,0.3) !important;
    }
    .stTextArea textarea:focus {
        border-color: #64b5f6 !important;
        box-shadow: 0 0 8px rgba(100, 181, 246, 0.2) !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Datamart Descriptions ──────────────────────────────────────
DATAMART_DESCRIPTIONS = {
    "telemetry": {
        "icon": "📡",
        "desc": "Live & historical sensor readings from vessel instrumentation — engine RPM, exhaust temps, pressures, alarms. ~629 sensor tags per vessel.",
        "source": "PostgreSQL",
    },
    "job_plan": {
        "icon": "📋",
        "desc": "Planned maintenance jobs with schedules, frequencies, and next due dates for all equipment onboard.",
        "source": "CSV",
    },
    "pending_jobs": {
        "icon": "⏳",
        "desc": "Pending and overdue maintenance job orders — jobs awaiting completion with priority and due dates.",
        "source": "CSV",
    },
    "completed_jobs": {
        "icon": "✅",
        "desc": "Historical completed maintenance records — what was done, when, and by whom.",
        "source": "CSV",
    },
    "equipment": {
        "icon": "⚙️",
        "desc": "Equipment master list — makers, models, serial numbers, and hierarchy codes for all vessel machinery.",
        "source": "CSV",
    },
    "running_hours": {
        "icon": "🕐",
        "desc": "Equipment running hour counter readings — tracks operational hours for maintenance scheduling.",
        "source": "CSV",
    },
    "voyage_plan": {
        "icon": "🗺️",
        "desc": "Voyage legs, port calls, arrival/departure times, and ETAs for voyage planning.",
        "source": "CSV",
    },
}

# ─── Header ─────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🚢 Marine Diagnostic Agent</h1>
    <p>Multi-agent diagnostic pipeline for vessel engine maintenance</p>
</div>
""", unsafe_allow_html=True)

# ─── Layout: Sidebar (Datamarts) + Main (Input & Results) ──────
col_left, col_right = st.columns([1, 2.5], gap="large")

# ─── Left Column: Available Datamarts ───────────────────────────
with col_left:
    st.markdown("#### 📦 Available Datamarts")
    for name, info in DATAMART_DESCRIPTIONS.items():
        st.markdown(f"""
        <div class="datamart-card">
            <div class="dm-name">{info['icon']} {name}</div>
            <span class="dm-source">{info['source']}</span>
            <div class="dm-desc">{info['desc']}</div>
        </div>
        """, unsafe_allow_html=True)

# ─── Right Column: Diagnostic Input & Results ───────────────────
with col_right:
    st.markdown("#### 🔍 Diagnostic Chain")

    # Vessel selector
    vessel = st.selectbox(
        "Vessel",
        ["Flora Schulte"],
        index=0,
        help="Select the vessel to diagnose",
    )

    # Condition input
    diagnostic_input = st.text_area(
        "Enter your diagnostic conditions",
        height=180,
        placeholder="""Example:
1) Check telemetry if there is exhaust deviation of more than 30 deg from average.
2) If yes, check pending jobs if there are any jobs related to main engine 
   cylinder inspection due in the next 10 days or overdue.
3) If no such jobs found, issue alert.

Action: Issue Alert card with Title 
"Perform Under piston space inspection in the next 10 days\"""",
    )

    # Run button
    col_run, col_clear = st.columns([1, 4])
    with col_run:
        run_clicked = st.button("🚀 Run Diagnostic", type="primary", use_container_width=True)
    with col_clear:
        if st.button("🗑️ Clear", use_container_width=False):
            if "result" in st.session_state:
                del st.session_state["result"]
            st.rerun()

    # ─── Run Diagnostic ─────────────────────────────────────────
    if run_clicked and diagnostic_input.strip():
        with st.spinner("🔄 Running diagnostic chain... (querying datamarts, analyzing data)"):
            try:
                result = run_diagnostic(diagnostic_input, vessel)
                st.session_state["result"] = result
            except Exception as e:
                st.error(f"❌ Error: {e}")

    # ─── Display Results ────────────────────────────────────────
    if "result" in st.session_state:
        result = st.session_state["result"]
        st.markdown("---")
        st.markdown("#### 📊 Results")

        # Status badges
        status = result["status"]
        status_map = {
            "action_needed": ("🔴", "Action Required"),
            "no_action": ("🟢", "No Action Needed"),
            "error": ("⚠️", "Error"),
            "rejected": ("🚫", "Rejected"),
        }
        icon, label = status_map.get(status, ("❓", status))

        # Stats row
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value">{icon}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value">{len(result.get('step_results', []))}</div>
                <div class="stat-label">Steps Completed</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-value">🚢</div>
                <div class="stat-label">{result.get('vessel_name', vessel)}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")

        # Step-by-step results
        for step in result.get("step_results", []):
            cond = step.get("condition_met")
            css_class = "condition-true" if cond is True else "condition-false" if cond is False else ""
            cond_badge = "✅ Yes" if cond is True else "❌ No" if cond is False else "ℹ️ Info"

            st.markdown(f"""
            <div class="step-card {css_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span style="font-weight: 600; color: #64b5f6;">Step {step['step_number']} — {step['datamart']}</span>
                    <span style="font-size: 0.85rem;">{cond_badge}</span>
                </div>
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7); margin-bottom: 0.4rem;">
                    <strong>Q:</strong> {step['question']}
                </div>
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.9);">
                    <strong>A:</strong> {step['answer']}
                </div>
                <div style="font-size: 0.78rem; color: rgba(255,255,255,0.5); margin-top: 0.3rem;">
                    Evidence: {step.get('evidence', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Alert card (if action needed)
        if status == "action_needed" and result.get("recommended_action"):
            st.markdown(f"""
            <div class="alert-card">
                <div style="font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
                    🚨 ALERT
                </div>
                <div style="font-size: 0.9rem; white-space: pre-wrap;">{result['recommended_action']}</div>
            </div>
            """, unsafe_allow_html=True)

        elif status == "no_action":
            # Check if any step had a data-not-available error
            error_steps = [s for s in result.get("step_results", []) if str(s.get("answer", "")).startswith("Error:")]
            if error_steps:
                for es in error_steps:
                    st.warning(f"⚠️ **Data not available** — {es['answer'].removeprefix('Error: ')}")
            else:
                st.success("✅ Diagnostic complete — no action required. Conditions not met.")

        elif status == "rejected":
            st.warning("🚫 Query rejected — not related to marine vessel maintenance.")

        # Expandable: raw step details
        with st.expander("🔧 Raw Details (SQL, queries)"):
            for step in result.get("step_results", []):
                st.markdown(f"**Step {step['step_number']} — {step['datamart']}**")
                st.code(step.get("query_used", "N/A"), language="sql")
                st.markdown("---")
