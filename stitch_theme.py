"""
Stitch Design System theme and UI helpers for Voice for Livelihood.

Implements Google Stitch Material 3 design tokens:
- Primary Navy (#1A237E / #000666)
- Surface Canvas (#FBF9F8)
- High-legibility Inter Typography
- Google Material Symbols Outlined
- Bento card containers, dynamic completion calculations, and exact Stitch layout tokens.
"""

from typing import Any, Dict, List, Tuple
import streamlit as st

STITCH_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

    /* Google Stitch Base Theme */
    html, body, [class*="css"], .stMarkdown, .stText, p, span, label, div {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Main background canvas */
    .stApp {
        background-color: #FBF9F8 !important;
        color: #1B1C1C !important;
    }

    /* Top Padding & Container Width */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1180px !important;
    }

    /* Hide default Streamlit header bar decoration */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* Top and Sidebar Headers */
    h1, h2, h3, h4 {
        color: #000666 !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #F6F3F2 !important;
        border-right: 1px solid #C6C5D4 !important;
        padding-top: 1.25rem !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem !important;
    }

    /* Navigation Radio Items in Sidebar */
    section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        font-size: 15px !important;
        font-weight: 500 !important;
        color: #454652 !important;
        padding: 6px 10px !important;
        border-radius: 8px !important;
        transition: all 0.15s ease !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background-color: #EAE8E7 !important;
        color: #000666 !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #000666 0%, #1A237E 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 0.5rem !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 0.6rem 1.35rem !important;
        box-shadow: 0 4px 12px rgba(0, 6, 102, 0.15) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1A237E 0%, #283593 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 18px rgba(0, 6, 102, 0.25) !important;
        transform: translateY(-1px) !important;
    }

    /* Secondary / outline buttons */
    .stButton > button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #000666 !important;
        border: 1.5px solid #000666 !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #F0EDED !important;
        transform: translateY(-1px) !important;
    }

    /* Form Inputs */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox select {
        border: 1.5px solid #C6C5D4 !important;
        border-radius: 0.5rem !important;
        background-color: #FFFFFF !important;
        color: #1B1C1C !important;
        font-size: 14px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
        transition: all 0.15s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #000666 !important;
        box-shadow: 0 0 0 3px rgba(0, 6, 102, 0.12) !important;
    }

    /* Streamlit Bordered Container Cards */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px !important;
        border: 1px solid #C6C5D4 !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(0, 6, 102, 0.03) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #A5A5C0 !important;
        box-shadow: 0 6px 18px rgba(0, 6, 102, 0.07) !important;
    }

    /* Stitch Container Cards */
    .stitch-card {
        background-color: #FFFFFF;
        border: 1px solid #C6C5D4;
        border-radius: 0.875rem;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 3px 12px rgba(0, 6, 102, 0.04);
        transition: all 0.2s ease;
    }
    .stitch-card:hover {
        box-shadow: 0 6px 18px rgba(0, 6, 102, 0.07);
    }

    /* Breadcrumbs */
    .stitch-breadcrumb {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 14px;
        color: #454652;
        margin-bottom: 0.75rem;
    }
    .stitch-breadcrumb span.current {
        font-weight: 600;
        color: #1B1C1C;
    }

    /* Demo Mode Badge */
    .stitch-demo-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        background-color: #E0E0FF;
        color: #000767;
        font-size: 12px;
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        border: 1px solid #BDC2FF;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    /* Profile Completion Progress */
    .stitch-progress-container {
        background-color: #EAE8E7;
        border-radius: 9999px;
        height: 10px;
        width: 100%;
        overflow: hidden;
        margin-top: 0.75rem;
    }
    .stitch-progress-bar {
        background-color: #000666;
        height: 100%;
        border-radius: 9999px;
        transition: width 0.3s ease;
    }

    /* Status Badges & Pills */
    .stitch-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background-color: #F0EDED;
        border: 1px solid #C6C5D4;
        padding: 0.3rem 0.7rem;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 500;
        color: #1B1C1C;
    }

    /* Assistant Message Bubble */
    .stitch-assistant-bubble {
        background-color: #E0E0FF;
        color: #000767;
        border: 1px solid #BDC2FF;
        border-radius: 1rem 1rem 1rem 0.125rem;
        padding: 1.2rem 1.4rem;
        font-size: 17px;
        line-height: 1.55;
        font-weight: 500;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(0, 6, 102, 0.05);
    }

    /* User Transcript Bubble */
    .stitch-user-bubble {
        background-color: #F6F3F2;
        color: #1B1C1C;
        border: 1px solid #C6C5D4;
        border-radius: 1rem 1rem 0.125rem 1rem;
        padding: 0.75rem 1rem;
        font-size: 14px;
        line-height: 1.4;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }

    /* Large Central Pulsing Mic Animation */
    .stitch-mic-hero {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 120px;
        height: 120px;
        margin: 0.75rem auto;
    }
    .stitch-mic-ring-outer {
        position: absolute;
        inset: 0;
        border: 3px solid #FF9933;
        border-radius: 50%;
        opacity: 0.5;
        animation: stitch-ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
    }
    .stitch-mic-ring-inner {
        position: absolute;
        inset: 10px;
        border: 3px solid #FF9933;
        border-radius: 50%;
        opacity: 0.7;
        animation: stitch-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    .stitch-mic-button-core {
        position: relative;
        z-index: 10;
        width: 76px;
        height: 76px;
        background: linear-gradient(135deg, #000666 0%, #1A237E 100%);
        color: #FFFFFF;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 6px 20px rgba(0, 6, 102, 0.35);
        transition: transform 0.2s ease;
    }
    @keyframes stitch-ping {
        75%, 100% { transform: scale(1.25); opacity: 0; }
    }
    @keyframes stitch-pulse {
        50% { opacity: 0.3; }
    }

    /* Phrase Box */
    .stitch-phrase-box {
        background: linear-gradient(135deg, #FFFFFF 0%, #F6F3F2 100%);
        border: 2px solid #000666;
        border-radius: 0.875rem;
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0, 6, 102, 0.06);
    }
    .stitch-phrase-text {
        font-size: 26px;
        font-weight: 800;
        color: #000666;
        letter-spacing: 0.2em;
    }

    /* Bento Card */
    .stitch-bento-card {
        background-color: #FFFFFF;
        border: 1px solid #C6C5D4;
        border-radius: 0.875rem;
        padding: 1.15rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 2px 8px rgba(0, 6, 102, 0.03);
        transition: all 0.2s ease;
    }
    .stitch-bento-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(0, 6, 102, 0.07);
        border-color: #A5A5C0;
    }

    /* Chips */
    .stitch-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background-color: #E4E2E1;
        color: #454652;
        border: 1px solid #C6C5D4;
        padding: 0.25rem 0.55rem;
        border-radius: 0.375rem;
        font-size: 12px;
        font-weight: 500;
    }

    /* Disclaimer Card */
    .stitch-disclaimer {
        background-color: #E4E2E1;
        border: 1px solid #767683;
        border-radius: 0.5rem;
        padding: 0.85rem 1.15rem;
        display: flex;
        align-items: flex-start;
        gap: 0.65rem;
        margin-top: 1rem;
    }

    /* Material Symbols font utility */
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal !important;
        font-style: normal !important;
        font-size: 20px;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        -webkit-font-feature-settings: 'liga';
        -webkit-font-smoothing: antialiased;
        vertical-align: middle;
    }

    /* Stitch KPI Bento Card */
    .stitch-kpi-card {
        background-color: #FFFFFF;
        border: 1px solid #C6C5D4;
        border-radius: 0.875rem;
        padding: 1.15rem 1.25rem;
        box-shadow: 0 2px 6px rgba(0, 6, 102, 0.04);
        position: relative;
        overflow: hidden;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .stitch-kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 6, 102, 0.08);
        border-color: #000666;
    }
    .stitch-kpi-accent {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #FF9933, #000666, #138808);
    }
    .stitch-kpi-value {
        font-size: 26px;
        font-weight: 700;
        color: #000666;
        line-height: 1.2;
        margin: 6px 0;
    }
    .stitch-kpi-title {
        font-size: 13px;
        font-weight: 600;
        color: #454652;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* Tabs & Dataframes Styling */
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        font-size: 14px !important;
        color: #454652 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #000666 !important;
        border-bottom-color: #000666 !important;
    }
    .stDataFrame {
        border: 1px solid #C6C5D4 !important;
        border-radius: 0.75rem !important;
        overflow: hidden !important;
    }
</style>
"""


def inject_stitch_theme() -> None:
    """Inject Google Stitch Material 3 CSS styles into the Streamlit session."""
    st.markdown(STITCH_CSS, unsafe_allow_html=True)


def calculate_profile_completion(profile: Dict[str, Any]) -> int:
    """
    Calculate the actual dynamic profile completion percentage (0% to 100%).
    Evaluates 10 core fields with equal weighting (10% each).
    """
    if not profile:
        return 0

    evaluated_fields = [
        ("name", bool(str(profile.get("name", "")).strip())),
        ("age", bool(profile.get("age") and int(profile.get("age", 0)) > 0)),
        ("district", bool(str(profile.get("district", "")).strip())),
        ("education_level", bool(str(profile.get("education_level", "")).strip() and profile.get("education_level") != "No formal education")),
        ("current_livelihood", bool(str(profile.get("current_livelihood", "")).strip())),
        ("previous_work_experience", bool(str(profile.get("previous_work_experience", "")).strip())),
        ("skills", bool(str(profile.get("skills", "")).strip())),
        ("interests", bool(str(profile.get("interests", "")).strip())),
        ("employment_preference", bool(str(profile.get("employment_preference", "")).strip())),
        ("mobility_constraints", bool(str(profile.get("mobility_constraints", "")).strip())),
    ]

    filled_count = sum(1 for _, is_filled in evaluated_fields if is_filled)
    return int((filled_count / len(evaluated_fields)) * 100)


def render_stitch_breadcrumb(page_title: str) -> None:
    """Render Stitch breadcrumb navigation with immune chevron."""
    st.markdown(
        f"""
        <div class="stitch-breadcrumb">
            <span style="color: #000666; font-weight: 500;">Home</span>
            <span style="color: #767683; font-size: 14px; margin: 0 4px;">&rsaquo;</span>
            <span class="current">{page_title}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stitch_header(title: str, subtitle: str = "", demo_mode: bool = True) -> None:
    """Render standardized top Stitch header with title, subtitle, and Demo Mode badge."""
    badge_html = '<span class="stitch-demo-badge">Demo Mode</span>' if demo_mode else ''
    st.markdown(
        f"""
        <div style="position: relative; border-bottom: 1px solid #C6C5D4; padding-bottom: 12px; margin-bottom: 18px;">
            <div style="position: absolute; bottom: -1px; left: 0; width: 140px; height: 3px; background: linear-gradient(90deg, #FF9933, #000666, #138808); border-radius: 2px;"></div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h2 style="font-size: 24px; font-weight: 700; color: #000666; margin: 0;">{title}</h2>
                    {f'<p style="font-size: 14px; color: #454652; margin: 4px 0 0 0;">{subtitle}</p>' if subtitle else ''}
                </div>
                <div>
                    {badge_html}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stitch_kpi_card(
    title: str,
    value: Any,
    subtitle: str = "",
    icon: str = "analytics",
    badge_text: str = "",
    badge_color: str = "primary",
) -> None:
    """Render a modern Stitch KPI Bento Card with icon, styled metric, and badge."""
    badge_html = ""
    if badge_text:
        bg_col = "#E0E0FF" if badge_color == "primary" else ("#E8F5E9" if badge_color == "success" else "#FFF3E0")
        tx_col = "#000767" if badge_color == "primary" else ("#1B5E20" if badge_color == "success" else "#E65100")
        badge_html = f'<span style="background: {bg_col}; color: {tx_col}; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">{badge_text}</span>'

    st.markdown(
        f"""
        <div class="stitch-kpi-card">
            <div class="stitch-kpi-accent"></div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div class="stitch-kpi-title">
                    <span class="material-symbols-outlined" style="font-size: 18px; color: #000666;">{icon}</span>
                    <span>{title}</span>
                </div>
                {badge_html}
            </div>
            <div class="stitch-kpi-value">{value}</div>
            {f'<div style="font-size: 12px; color: #767683; margin-top: 2px;">{subtitle}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stitch_active_beneficiary_badge(name: str, beneficiary_id: str, district: str, language: str = "Hindi") -> None:
    """Render a modern beneficiary identity card with avatar initials in the sidebar."""
    clean_name = name or "Unnamed Beneficiary"
    initials = "".join([part[0].upper() for part in clean_name.split()[:2]]) or "B"
    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #C6C5D4; border-radius: 12px; padding: 10px 12px; margin: 8px 0 12px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.04);">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #000666, #1A237E); color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; flex-shrink: 0; box-shadow: 0 2px 6px rgba(0,6,102,0.2);">
                    {initials}
                </div>
                <div style="min-width: 0; flex: 1;">
                    <div style="font-size: 13px; font-weight: 700; color: #000666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        {clean_name}
                    </div>
                    <div style="font-size: 11px; color: #454652; display: flex; align-items: center; gap: 4px; margin-top: 1px;">
                        <span style="font-weight: 600; color: #1B1C1C;">{beneficiary_id}</span>
                        <span>•</span>
                        <span>{district}</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stitch_completion_card(completion_pct: int) -> None:
    """Render the Stitch profile completion card with dynamic percentage and progress bar."""
    badge_color = "#E8F5E9" if completion_pct >= 80 else ("#E0E0FF" if completion_pct >= 40 else "#FFF3E0")
    text_color = "#1B5E20" if completion_pct >= 80 else ("#000767" if completion_pct >= 40 else "#E65100")
    badge_text = "Match Ready 🚀" if completion_pct >= 80 else ("Intermediate Profile" if completion_pct >= 40 else "Initial Information")
    st.markdown(
        f"""
        <div class="stitch-card" style="position: relative; overflow: hidden; padding-top: 1.6rem;">
            <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #FF9933, #000666, #138808);"></div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 17px; font-weight: 700; color: #000666;">Profile Completion</span>
                        <span style="background: {badge_color}; color: {text_color}; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">{badge_text}</span>
                    </div>
                    <div style="font-size: 13px; color: #454652; margin-top: 4px;">
                        Complete your profile details to unlock more targeted NSQF skill pathways.
                    </div>
                </div>
                <div style="font-size: 26px; font-weight: 700; color: #000666;">
                    {completion_pct}%
                </div>
            </div>
            <div class="stitch-progress-container" style="height: 10px; border-radius: 9999px; background: #EAE8E7; margin-top: 14px; overflow: hidden;">
                <div class="stitch-progress-bar" style="width: {completion_pct}%; height: 100%; border-radius: 9999px; background: linear-gradient(90deg, #000666, #1A237E, #138808); transition: width 0.4s ease;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stitch_phrase_card(phrase_str: str) -> None:
    """Render the central dynamic challenge phrase card."""
    st.markdown(
        f"""
        <div class="stitch-phrase-box">
            <div class="stitch-phrase-text">{phrase_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stitch_trade_card(rank: int, trade: Dict[str, Any], portal_query: str = "") -> None:
    """Render a modern aesthetic NSQF Trade Recommendation Card."""
    trade_name = trade.get("trade_name", "")
    nsqf_level = trade.get("nsqf_level", "")
    sector = trade.get("sector", "")
    demand = trade.get("demand_score", 0)
    wage = trade.get("avg_monthly_wage_inr", 0)
    score = trade.get("score", 0)
    explanations = trade.get("explanations", [])

    accent_colors = ["#FF9933", "#000666", "#138808"]
    border_accent = accent_colors[(rank - 1) % len(accent_colors)]

    url = f"/app/static/skill-portal/index.html?{portal_query}" if portal_query else "#"

    exp_html = ""
    if explanations:
        exp_items = "".join([f"<li style='margin-bottom: 2px;'>{e}</li>" for e in explanations[:2]])
        exp_html = f"""
        <div style="background: #F6F3F2; border-radius: 8px; padding: 8px 12px; margin: 10px 0; font-size: 12px; color: #454652;">
            <ul style="margin: 0; padding-left: 18px;">{exp_items}</ul>
        </div>
        """

    st.markdown(
        f"""
        <div class="stitch-card" style="position: relative; overflow: hidden; border-left: 5px solid {border_accent}; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 18px; font-weight: 700; color: #000666;">{rank}. {trade_name}</span>
                        <span style="background: #FFF3E0; color: #E65100; border: 1px solid #FFE0B2; font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 6px;">NSQF Level {nsqf_level}</span>
                    </div>
                    <span style="font-size: 12px; font-weight: 500; color: #454652; margin-top: 2px; display: inline-block;">Sector: <b>{sector}</b></span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="background: #E0E0FF; color: #000767; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 9999px;">Match Score {score:.1f}</span>
                </div>
            </div>
            
            <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px;">
                <div style="background: #FFFFFF; border: 1px solid #C6C5D4; padding: 6px 12px; border-radius: 8px; font-size: 12px; display: flex; align-items: center; gap: 6px;">
                    <span style="color: #138808; font-weight: 700;">₹</span>
                    <span>Avg Monthly Wage: <b style="color: #000666;">₹{wage:,}</b></span>
                </div>
                <div style="background: #FFFFFF; border: 1px solid #C6C5D4; padding: 6px 12px; border-radius: 8px; font-size: 12px; display: flex; align-items: center; gap: 6px;">
                    <span style="color: #000666;">📈</span>
                    <span>Local Demand: <b style="color: #000666;">{demand:.0f}/10</b></span>
                </div>
            </div>

            {exp_html}

            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding-top: 10px; border-top: 1px solid #EAE8E7;">
                <span style="font-size: 11px; color: #138808; font-weight: 700; display: flex; align-items: center; gap: 4px;">
                    <span>✓</span> Certified Skill Mission Pathway
                </span>
                <a href="{url}" target="_blank" style="background: #000666; color: #FFFFFF; text-decoration: none; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 6px rgba(0,6,102,0.15); transition: all 0.2s ease;">
                    <span>Explore Course &amp; Modules</span>
                    <span style="font-size: 12px;">↗</span>
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stitch_disclaimer(title: str, body: str) -> None:
    """Render standardized prototype disclaimer card."""
    st.markdown(
        f"""
        <div class="stitch-disclaimer">
            <span style="font-size: 18px; margin-top: 1px;">ℹ️</span>
            <div>
                <div style="font-weight: 700; font-size: 13px; color: #1B1C1C;">{title}</div>
                <div style="font-size: 12px; color: #454652; margin-top: 2px;">{body}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
