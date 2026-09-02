"""
Voice for Livelihood -- prototype demo

Pipeline:

Voice input
    ↓
Indic Conformer ASR
    ↓
Transcript
    ↓
Keyword + local demand matcher
    ↓
NSQF trade recommendation
    ↓
Multilingual recommendation text
    ↓
Indic Parler-TTS
    ↓
Spoken response
"""

import os
import tempfile

import streamlit as st

from matcher import (
    load_trades,
    match_trades,
    match_profile,
    build_recommendation_text,
)

from speech import (
    LANGUAGES,
    load_asr_model,
    transcribe,
    load_tts_model,
    synthesize,
)

import importlib
import profile_store
importlib.reload(profile_store)

from profile_store import (
    load_profiles,
    get_profile,
    save_profile,
    list_profiles,
    generate_beneficiary_id,
    update_profile_slots,
)

from resume_generator import (
    generate_resume_docx,
    generate_resume_preview_text,
)

from followup_store import (
    load_followups,
    get_beneficiary_followups,
    mark_training_complete,
    record_survey_response,
    get_milestone_timing,
)

from attendance_store import (
    load_attendance,
    save_attendance_record,
    generate_challenge_phrase,
    verify_phrase_match,
)

from conversation_manager import (
    ConversationSession,
    STEP_LABELS,
)

from stitch_theme import (
    inject_stitch_theme,
    calculate_profile_completion,
    render_stitch_breadcrumb,
    render_stitch_header,
    render_stitch_completion_card,
    render_stitch_phrase_card,
    render_stitch_disclaimer,
    render_stitch_kpi_card,
    render_stitch_active_beneficiary_badge,
    render_stitch_trade_card,
)


# ---------------------------------------------------------------------------
# PAGE
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Voice for Livelihood",
    page_icon="🎙️",
    layout="wide",
)

inject_stitch_theme()

DISTRICTS = [
    "Nagpur",
    "Pune",
    "Mumbai",
    "Amravati",
    "Nashik",
    "Aurangabad",
    "Default (any district)",
]


# ---------------------------------------------------------------------------
# MODELS (CACHED)
# ---------------------------------------------------------------------------

@st.cache_resource(
    show_spinner=(
        "Loading speech recognition model "
        "(first run only)..."
    )
)
def get_asr_model():

    return load_asr_model()


@st.cache_resource(
    show_spinner=(
        "Loading text-to-speech model "
        "(first run only)..."
    )
)
def get_tts_bundle():

    return load_tts_model()


@st.cache_data
def get_trades_df():

    return load_trades(
        os.path.join(
            "data",
            "nsqf_trades.csv",
        )
    )


# Initialize global active beneficiary and language state
if "active_beneficiary_id" not in st.session_state:
    all_init_profs = load_profiles()
    st.session_state.active_beneficiary_id = all_init_profs[0].get("beneficiary_id") if all_init_profs else None

if "selected_language" not in st.session_state:
    init_prof = get_profile(st.session_state.active_beneficiary_id) if st.session_state.active_beneficiary_id else None
    st.session_state.selected_language = (init_prof.get("language") if init_prof else None) or "Hindi"


# ---------------------------------------------------------------------------
# NAVIGATION (STITCH SIDEBAR DESIGN)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="margin-bottom: 16px; padding: 0 4px;">
            <div style="display: flex; align-items: center; gap: 8px; color: #000666;">
                <span style="font-size: 22px;">🎙️</span>
                <span style="font-size: 19px; font-weight: 700; color: #000666;">Voice for Livelihood</span>
            </div>
            <p style="font-size: 13px; color: #454652; margin: 4px 0 0 0;">Livelihood &amp; Skill Development</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🎙️ Start Voice Assistant", type="primary", use_container_width=True):
        st.session_state.selected_nav_page = "Voice Assistant"
        st.rerun()

    # Global Active Beneficiary Selector in Sidebar
    all_side_profiles = load_profiles()
    if all_side_profiles:
        st.markdown("<p style='font-size: 11px; font-weight: 700; color: #454652; text-transform: uppercase; margin: 12px 0 4px 0;'>Active Beneficiary</p>", unsafe_allow_html=True)
        side_prof_map = {
            f"{p.get('beneficiary_id', '')} - {p.get('name', 'Unnamed')} ({p.get('district', '')})": p.get("beneficiary_id")
            for p in all_side_profiles
        }
        current_side_id = st.session_state.get("active_beneficiary_id")
        side_idx = 0
        side_labels = list(side_prof_map.keys())
        for idx, lbl in enumerate(side_labels):
            if side_prof_map[lbl] == current_side_id:
                side_idx = idx
                break
        
        selected_side_label = st.selectbox(
            "Active Beneficiary",
            side_labels,
            index=side_idx,
            key="sidebar_active_ben_select",
            label_visibility="collapsed",
        )
        new_side_id = side_prof_map[selected_side_label]
        if new_side_id != st.session_state.get("active_beneficiary_id"):
            st.session_state.active_beneficiary_id = new_side_id
            b_info = get_profile(new_side_id)
            if b_info and b_info.get("language"):
                st.session_state.selected_language = b_info.get("language")
            st.session_state.conv_session = ConversationSession(
                beneficiary_id=new_side_id,
                language=st.session_state.get("selected_language", "Hindi"),
                district=b_info.get("district", "Nagpur") if b_info else "Nagpur"
            )
            st.rerun()

        active_prof_side = get_profile(st.session_state.get("active_beneficiary_id"))
        if active_prof_side:
            render_stitch_active_beneficiary_badge(
                name=active_prof_side.get("name", "Unnamed Beneficiary"),
                beneficiary_id=active_prof_side.get("beneficiary_id", ""),
                district=active_prof_side.get("district", "Nagpur"),
                language=active_prof_side.get("language", "Hindi"),
            )

    st.markdown("<p style='font-size: 11px; font-weight: 700; color: #454652; text-transform: uppercase; margin: 12px 0 4px 0;'>Navigation</p>", unsafe_allow_html=True)

    NAV_PAGES = [
        "Dashboard",
        "Voice Assistant",
        "Beneficiary Profile",
        "Skill Pathways",
        "Training",
        "Follow-up",
        "Attendance",
        "Resume",
    ]

    default_idx = 1
    if "selected_nav_page" in st.session_state and st.session_state.selected_nav_page in NAV_PAGES:
        default_idx = NAV_PAGES.index(st.session_state.selected_nav_page)

    page = st.radio(
        "Navigation Menu",
        NAV_PAGES,
        index=default_idx,
        label_visibility="collapsed",
    )
    st.session_state.selected_nav_page = page

    st.divider()
    st.caption("© 2024 Sahayak | Official Prototype")


import base64
import streamlit.components.v1 as components

# Declare Stitch Voice Assistant Frontend Component
_stitch_voice_assistant_component = components.declare_component(
    "stitch_voice_assistant",
    path=os.path.join(os.path.dirname(__file__), "frontend", "voice_assistant"),
)


# ===========================================================================
# PAGE: VOICE ASSISTANT (ACTUAL STITCH FRONTEND COMPONENT)
# ===========================================================================

if page == "Voice Assistant":

    # Hide default Streamlit sidebar and wrapper padding when Stitch Voice Assistant is active
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] { display: none !important; }
            .main .block-container { padding: 0 !important; max-width: 100vw !important; }
            header[data-testid="stHeader"] { display: none !important; }
            footer { display: none !important; }
            iframe { border: none !important; width: 100% !important; min-height: 100vh !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    active_b_id = st.session_state.get("active_beneficiary_id")
    active_prof = get_profile(active_b_id) if active_b_id else None
    active_lang = st.session_state.get("selected_language") or (active_prof.get("language") if active_prof else "Hindi")
    active_dist = active_prof.get("district", "Nagpur") if active_prof else "Nagpur"

    # Initialize or synchronize session state with active beneficiary
    if "conv_session" not in st.session_state or (active_b_id and st.session_state.conv_session.beneficiary_id != active_b_id):
        st.session_state.conv_session = ConversationSession(
            beneficiary_id=active_b_id,
            language=active_lang,
            district=active_dist,
        )
    if "last_processed_event_id" not in st.session_state:
        st.session_state.last_processed_event_id = None

    session: ConversationSession = st.session_state.conv_session

    # Prepare Recommendations & TTS if complete
    recommendations = []
    rec_spoken_text = ""
    rec_audio_base64 = None

    if session.is_complete:
        trades_df = get_trades_df()
        recommendations = match_profile(
            session.slots,
            district=session.district,
            trades_df=trades_df,
            top_n=3,
        )
        rec_spoken_text = build_recommendation_text(recommendations, session.language)

        # Synthesize recommendation audio if not yet cached
        rec_cache_key = f"rec_audio_{session.beneficiary_id}_{session.language}"
        if rec_cache_key not in st.session_state:
            st.session_state[rec_cache_key] = ""
            try:
                tts_bundle = get_tts_bundle()
                tmp_rec_out = os.path.join(tempfile.gettempdir(), f"rec_{session.beneficiary_id}.mp3")
                out = synthesize(
                    tts_bundle,
                    rec_spoken_text,
                    LANGUAGES.get(session.language, "hi"),
                    out_path=tmp_rec_out,
                )
                if out and os.path.exists(tmp_rec_out):
                    with open(tmp_rec_out, "rb") as f:
                        st.session_state[rec_cache_key] = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                print("TTS rec error:", e)

        rec_audio_base64 = st.session_state.get(rec_cache_key) or None

    # Prepare TTS audio for current question
    curr_q = session.get_current_question()
    tts_audio_base64 = None

    if not session.is_complete:
        q_cache_key = f"q_tts_{session.beneficiary_id}_{session.current_step_idx}_{session.language}"
        if q_cache_key not in st.session_state:
            st.session_state[q_cache_key] = ""
            try:
                tts_bundle = get_tts_bundle()
                tmp_q_out = os.path.join(tempfile.gettempdir(), f"q_{session.beneficiary_id}_{session.current_step_idx}.mp3")
                out = synthesize(
                    tts_bundle,
                    curr_q,
                    LANGUAGES.get(session.language, "hi"),
                    out_path=tmp_q_out,
                )
                if out and os.path.exists(tmp_q_out):
                    with open(tmp_q_out, "rb") as f:
                        st.session_state[q_cache_key] = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                print("TTS question error:", e)

        tts_audio_base64 = st.session_state.get(q_cache_key) or None

    # Load list of existing profiles for the selector
    all_profiles = load_profiles()
    profile_list = [
        {
            "id": p.get("beneficiary_id"),
            "name": p.get("name") or "Unnamed Beneficiary",
            "district": p.get("district") or "",
            "is_complete": bool(p.get("name") and p.get("skills")),
        }
        for p in all_profiles
    ]

    # Render the exact Stitch Frontend Component
    event = _stitch_voice_assistant_component(
        language=session.language,
        district=session.district,
        beneficiary_id=session.beneficiary_id,
        step_label=STEP_LABELS.get(session.current_step, session.current_step) if not session.is_complete else "Complete",
        step_idx=session.current_step_idx,
        question=curr_q,
        history=session.history,
        slots=session.slots,
        progress=session.get_progress(),
        is_complete=session.is_complete,
        recommendations=recommendations,
        rec_spoken_text=rec_spoken_text,
        tts_audio_base64=tts_audio_base64,
        rec_audio_base64=rec_audio_base64,
        profiles=profile_list,
        default=None,
        key="stitch_voice_assistant_component",
    )

    # Handle Bridge Events from the Stitch Frontend (with Deduplication)
    if event and isinstance(event, dict):
        event_id = event.get("event_id")
        if event_id and event_id != st.session_state.last_processed_event_id:
            st.session_state.last_processed_event_id = event_id
            action = event.get("action")

            if action == "audio_recorded" and event.get("audio_base64"):
                try:
                    audio_bytes = base64.b64decode(event["audio_base64"])
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp.write(audio_bytes)
                        tmp_path = tmp.name

                    try:
                        asr_model = get_asr_model()
                        transcript = transcribe(
                            asr_model,
                            tmp_path,
                            LANGUAGES.get(session.language, "hi"),
                            decoding="ctc",
                        )
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

                    if transcript and transcript.strip():
                        session.process_turn(transcript.strip())
                        st.session_state.active_beneficiary_id = session.beneficiary_id
                        st.rerun()
                except Exception as e:
                    print("Audio transcription error:", e)

            elif action == "user_text" and event.get("text"):
                text = event["text"].strip()
                if text:
                    session.process_turn(text)
                    st.session_state.active_beneficiary_id = session.beneficiary_id
                    st.rerun()

            elif action == "navigate" and event.get("page"):
                st.session_state.selected_nav_page = event["page"]
                st.rerun()

            elif action == "change_language" and event.get("language"):
                new_lang = event["language"]
                st.session_state.selected_language = new_lang
                session.language = new_lang
                session.slots["language"] = new_lang
                session.save_profile()
                # Clear question TTS cache
                st.session_state.pop(f"q_tts_{session.beneficiary_id}_{session.current_step_idx}_{session.language}", None)
                st.rerun()

            elif action == "change_district" and event.get("district"):
                session.district = event["district"]
                session.slots["district"] = event["district"]
                session.save_profile()
                st.rerun()

            elif action == "select_profile" and event.get("beneficiary_id"):
                b_id = event["beneficiary_id"]
                if b_id == "NEW":
                    new_id = generate_beneficiary_id()
                    st.session_state.active_beneficiary_id = new_id
                    st.session_state.conv_session = ConversationSession(
                        beneficiary_id=new_id,
                        language=st.session_state.get("selected_language", session.language),
                        district=session.district,
                    )
                else:
                    st.session_state.active_beneficiary_id = b_id
                    b_prof = get_profile(b_id)
                    b_lang = (b_prof.get("language") if b_prof else None) or st.session_state.get("selected_language", "Hindi")
                    st.session_state.selected_language = b_lang
                    st.session_state.conv_session = ConversationSession(
                        beneficiary_id=b_id,
                        language=b_lang,
                        district=b_prof.get("district", "Nagpur") if b_prof else session.district,
                    )
                st.rerun()

            elif action == "reset":
                session.reset()
                st.rerun()


# ===========================================================================
# PAGE 1: SKILL PATHWAYS / VOICE RECOMMENDATION (ORIGINAL DEMO - PRESERVED)
# ===========================================================================

elif page in ["Skill Pathways", "🎙️ Voice Recommendation"]:

    render_stitch_breadcrumb("Skill Pathways")

    render_stitch_header(
        "Skill Pathways & Recommendations",
        "Speak your background and interests to discover NSQF-aligned skilling opportunities matched to local demand.",
        demo_mode=True,
    )

    # -----------------------------------------------------------------------
    # SETTINGS
    # -----------------------------------------------------------------------

    with st.sidebar:

        st.header("Settings")

        language_label = st.selectbox(
            "Language",
            list(LANGUAGES.keys()),
            index=0,
        )

        lang_code = LANGUAGES[
            language_label
        ]

        district = st.selectbox(
            "District (for local demand matching)",
            DISTRICTS,
            index=0,
        )

        district_key = (
            "default"
            if district.startswith("Default")
            else district.lower()
        )

        decoding = st.radio(
            "ASR decoding",
            ["ctc", "rnnt"],
            index=0,
            help=(
                "ctc is faster, rnnt is usually more accurate"
            ),
        )

        st.divider()

        st.caption(
            "Models: "
            "ai4bharat/indic-conformer-600m-multilingual "
            "(ASR) · "
            "ai4bharat/indic-parler-tts (TTS)"
        )

    active_b_id = st.session_state.get("active_beneficiary_id")
    active_profile = get_profile(active_b_id) if active_b_id else None
    trades_df = get_trades_df()

    if active_profile:
        st.markdown(
            f"""
            <div style="background-color: #f0eded; border: 1px solid #c6c5d4; border-radius: 12px; padding: 14px 18px; margin-bottom: 18px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-weight: 700; color: #000666; font-size: 15px;">Active Beneficiary: {active_profile.get('name', 'Unnamed')} ({active_profile.get('beneficiary_id', '')})</span>
                    <span style="background-color: #1a237e; color: #fff; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px;">{active_profile.get('district', district)}</span>
                </div>
                <div style="font-size: 12px; color: #454652; line-height: 1.5;">
                    <b>Work Experience:</b> {active_profile.get('current_livelihood') or 'None listed'} &nbsp;|&nbsp; 
                    <b>Skills:</b> {active_profile.get('skills') or 'None listed'} &nbsp;|&nbsp; 
                    <b>Preference:</b> {active_profile.get('employment_preference') or 'Wage Employment'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Compute and display recommendations for the active beneficiary!
        act_matches = match_profile(
            active_profile,
            district=active_profile.get("district", district_key),
            trades_df=trades_df,
            top_n=3,
        )
        st.subheader("🎯 Recommended Pathways for Active Beneficiary")
        import urllib.parse
        for i, m in enumerate(act_matches, start=1):
            portal_query = urllib.parse.urlencode({
                "beneficiary_id": active_profile.get("beneficiary_id", ""),
                "name": active_profile.get("name", ""),
                "district": active_profile.get("district", district),
                "lang": active_profile.get("language", language_label),
                "trade": m["trade_name"],
                "skills": active_profile.get("skills", ""),
                "work": active_profile.get("current_livelihood", ""),
                "pref": active_profile.get("employment_preference", ""),
            })
            render_stitch_trade_card(i, m, portal_query)

        st.divider()
        st.subheader("🎙️ Re-match or Explore via Voice Input")
    else:
        st.info("No active beneficiary selected. You can record a voice response below to discover pathways.")

    # -----------------------------------------------------------------------
    # RECORDING
    # -----------------------------------------------------------------------

    st.write(
        f'Try answering in **{language_label}**: '
        f'"What work have you done before, '
        f'and what would you like to learn?"'
    )

    audio_value = st.audio_input(
        "Record your answer"
    )

    uploaded_file = st.file_uploader(
        "...or upload a short WAV/FLAC clip instead",
        type=["wav", "flac"],
    )

    audio_bytes = None

    if audio_value is not None:

        audio_bytes = audio_value.getvalue()

    elif uploaded_file is not None:

        audio_bytes = uploaded_file.getvalue()

    run = st.button(
        "Transcribe & Recommend",
        type="primary",
        disabled=audio_bytes is None,
    )

    # -----------------------------------------------------------------------
    # PROCESS AUDIO
    # -----------------------------------------------------------------------

    if run and audio_bytes is not None:

        tmp_path = None

        try:

            # ---------------------------------------------------------------
            # Save temporary input audio
            # ---------------------------------------------------------------

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
            ) as tmp:

                tmp.write(audio_bytes)

                tmp_path = tmp.name

            # ---------------------------------------------------------------
            # ASR
            # ---------------------------------------------------------------

            with st.spinner(
                "Transcribing..."
            ):

                asr_model = get_asr_model()

                transcript = transcribe(
                    asr_model,
                    tmp_path,
                    lang_code,
                    decoding,
                )

            st.subheader(
                "2. What we heard"
            )

            st.info(transcript)

            # ---------------------------------------------------------------
            # TRADE MATCHING
            # ---------------------------------------------------------------

            with st.spinner(
                "Matching to NSQF trades and local demand..."
            ):

                trades_df = get_trades_df()

                matches = match_trades(
                    transcript,
                    district=district_key,
                    trades_df=trades_df,
                    top_n=3,
                )

            st.subheader(
                "3. Recommended pathways"
            )

            import urllib.parse
            for i, m in enumerate(matches, start=1):
                portal_query = urllib.parse.urlencode({
                    "trade": m["trade_name"],
                    "lang": language_label,
                    "district": district,
                })
                render_stitch_trade_card(i, m, portal_query)

            # ---------------------------------------------------------------
            # MULTILINGUAL RECOMMENDATION
            # ---------------------------------------------------------------

            reply_text = build_recommendation_text(
                matches,
                language_label,
            )

            st.subheader(
                "4. Spoken recommendation"
            )

            # Show exactly what will be spoken.
            st.write(reply_text)

            # ---------------------------------------------------------------
            # TTS
            # ---------------------------------------------------------------

            with st.spinner(
                f"Generating spoken reply in {language_label}..."
            ):

                tts_bundle = get_tts_bundle()

                out_path = os.path.join(
                    tempfile.gettempdir(),
                    "voice_livelihood_reply.mp3",
                )

                out_path = synthesize(
                    tts_bundle,
                    reply_text,
                    lang_code,
                    out_path=out_path,
                )

            # ---------------------------------------------------------------
            # PLAY AUDIO
            # ---------------------------------------------------------------

            if out_path and os.path.exists(out_path):
                st.audio(
                    out_path,
                    format="audio/mp3",
                )

                st.success(
                    f"Spoken response generated in {language_label}."
                )
            else:
                st.info(f"Response text prepared in {language_label}.")

        except Exception as e:

            st.error(
                "Something went wrong while processing "
                "the voice response."
            )

            st.exception(e)

        finally:

            if (
                tmp_path is not None
                and os.path.exists(tmp_path)
            ):

                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    elif not audio_bytes:

        st.caption(
            "Record or upload audio, then press "
            "**Transcribe & Recommend**."
        )


# ===========================================================================
# PAGE 2: BENEFICIARY PROFILE (UNIFIED STITCH UI DESIGN - PHASE 4A/4C)
# ===========================================================================

elif page in ["Beneficiary Profile", "👤 Beneficiary Profile"]:

    render_stitch_breadcrumb("Beneficiary Profile")

    render_stitch_header(
        "Beneficiary Profile",
        "Manage personal background, education, and skills to unlock targeted NSQF pathways.",
        demo_mode=True,
    )

    profiles = load_profiles()

    profile_mode = st.radio(
        "Action",
        ["Create New Beneficiary", "Lookup / Edit Existing Beneficiary"],
        horizontal=True,
    )

    selected_profile = None

    if profile_mode == "Lookup / Edit Existing Beneficiary":
        if not profiles:
            st.info("No beneficiary profiles found yet. Please create a new beneficiary.")
        else:
            profile_options = {
                f"{p.get('beneficiary_id', '')} - {p.get('name', 'Unnamed')} ({p.get('district', '')})": p.get("beneficiary_id")
                for p in profiles
            }
            labels = list(profile_options.keys())
            cur_act_id = st.session_state.get("active_beneficiary_id")
            cur_idx = 0
            for idx, l in enumerate(labels):
                if profile_options[l] == cur_act_id:
                    cur_idx = idx
                    break
            selected_label = st.selectbox("Select Beneficiary to View/Edit", labels, index=cur_idx)
            selected_id = profile_options[selected_label]
            if selected_id != st.session_state.get("active_beneficiary_id"):
                st.session_state.active_beneficiary_id = selected_id
                st.session_state.conv_session = ConversationSession(beneficiary_id=selected_id)
            selected_profile = get_profile(selected_id)

    # Determine default values
    if selected_profile:
        current_id = selected_profile.get("beneficiary_id")
        def_name = selected_profile.get("name", "")
        def_age = int(selected_profile.get("age", 25))
        def_gender = selected_profile.get("gender", "Male")
        def_district = selected_profile.get("district", "Nagpur")
        def_edu = selected_profile.get("education_level", "10th Pass")
        def_fam = selected_profile.get("family_occupation", "")
        def_live = selected_profile.get("current_livelihood", "")
        def_prev_exp = selected_profile.get("previous_work_experience", "")
        def_skills = selected_profile.get("skills", "")
        def_interests = selected_profile.get("interests", "")
        def_mobility = selected_profile.get("mobility_constraints", "Local only (within district)")
        def_emp = selected_profile.get("employment_preference", "Wage Employment (Job)")
        def_lang = selected_profile.get("language", "Hindi")
        def_status = selected_profile.get("training_status", "Not Started")
        def_trade = selected_profile.get("recommended_trade", "") or ""
    else:
        current_id = generate_beneficiary_id()
        def_name = ""
        def_age = 24
        def_gender = "Male"
        def_district = "Nagpur"
        def_edu = "10th Pass"
        def_fam = ""
        def_live = ""
        def_prev_exp = ""
        def_skills = ""
        def_interests = ""
        def_mobility = "Local only (within district)"
        def_emp = "Wage Employment (Job)"
        def_lang = "Hindi"
        def_status = "Not Started"
        def_trade = ""

    # Dynamic Profile Completion Card (Calculated from actual data)
    completion_pct = calculate_profile_completion(selected_profile or {
        "name": def_name, "age": def_age, "district": def_district, "education_level": def_edu,
        "current_livelihood": def_live, "previous_work_experience": def_prev_exp,
        "skills": def_skills, "interests": def_interests, "employment_preference": def_emp,
        "mobility_constraints": def_mobility
    })
    render_stitch_completion_card(completion_pct)

    # Stitch Profile Form Card
    with st.form("beneficiary_profile_form"):
        # Section 1: Personal Information
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 6px; border-bottom: 2px solid #C6C5D4; padding-bottom: 6px; margin-bottom: 12px;">
                <span style="font-size: 18px;">📌</span>
                <span style="font-size: 16px; font-weight: 700; color: #000666;">Personal Information</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)

        with col1:
            st.text_input("Beneficiary ID (System Generated)", value=current_id, disabled=True, help="Unique identifier assigned to each citizen.")
            name = st.text_input("Full Legal Name", value=def_name, placeholder="e.g. Ramesh Kumar")
            age = st.number_input("Age", min_value=14, max_value=85, value=def_age)

        with col2:
            gender = st.selectbox(
                "Gender",
                ["Male", "Female", "Other", "Prefer not to say"],
                index=["Male", "Female", "Other", "Prefer not to say"].index(def_gender) if def_gender in ["Male", "Female", "Other", "Prefer not to say"] else 0,
            )
            district = st.selectbox(
                "District / Location",
                DISTRICTS,
                index=DISTRICTS.index(def_district) if def_district in DISTRICTS else 0,
            )
            language = st.selectbox(
                "Preferred Language for Skilling",
                list(LANGUAGES.keys()),
                index=list(LANGUAGES.keys()).index(def_lang) if def_lang in LANGUAGES else 0,
            )

        # Section 2: Education & Experience
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 6px; border-bottom: 2px solid #C6C5D4; padding-bottom: 6px; margin-top: 16px; margin-bottom: 12px;">
                <span style="font-size: 18px;">🎓</span>
                <span style="font-size: 16px; font-weight: 700; color: #000666;">Education &amp; Work Experience</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col3, col4 = st.columns(2)

        with col3:
            education_level = st.selectbox(
                "Highest Education Level",
                ["No formal education", "5th Pass", "8th Pass", "10th Pass", "12th Pass", "ITI / Diploma", "Graduate", "Post Graduate"],
                index=["No formal education", "5th Pass", "8th Pass", "10th Pass", "12th Pass", "ITI / Diploma", "Graduate", "Post Graduate"].index(def_edu) if def_edu in ["No formal education", "5th Pass", "8th Pass", "10th Pass", "12th Pass", "ITI / Diploma", "Graduate", "Post Graduate"] else 3,
            )
            current_livelihood = st.text_input("Current Livelihood / Occupation", value=def_live, placeholder="e.g. Daily wage helper, farm labour")

        with col4:
            family_occupation = st.text_input("Family Background / Occupation", value=def_fam, placeholder="e.g. Traditional weaving, farming")
            previous_work_experience = st.text_input("Previous Work Experience Details", value=def_prev_exp, placeholder="e.g. 2 years electrical wiring assistant")

        # Section 3: Skills & Preferences
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 6px; border-bottom: 2px solid #C6C5D4; padding-bottom: 6px; margin-top: 16px; margin-bottom: 12px;">
                <span style="font-size: 18px;">💡</span>
                <span style="font-size: 16px; font-weight: 700; color: #000666;">Skills &amp; Learning Preferences</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        skills = st.text_area(
            "Current Skills & Practical Abilities",
            value=def_skills,
            placeholder="e.g. electrical wiring, switch repair, plumbing, pipe fitting",
            help="Enter key skills or practical abilities.",
        )
        interests = st.text_area(
            "Areas of Interest for Training",
            value=def_interests,
            placeholder="e.g. solar panel installation, machine maintenance, motor repair",
            help="Enter trades or skills the beneficiary wishes to learn.",
        )

        col5, col6 = st.columns(2)
        with col5:
            mobility_constraints = st.selectbox(
                "Work / Mobility Preference",
                ["Local only (within district)", "Willing to relocate within state", "Willing to relocate anywhere in India"],
                index=["Local only (within district)", "Willing to relocate within state", "Willing to relocate anywhere in India"].index(def_mobility) if def_mobility in ["Local only (within district)", "Willing to relocate within state", "Willing to relocate anywhere in India"] else 0,
            )
            training_status = st.selectbox(
                "Training Status",
                ["Not Started", "In Progress", "Completed"],
                index=["Not Started", "In Progress", "Completed"].index(def_status) if def_status in ["Not Started", "In Progress", "Completed"] else 0,
            )

        with col6:
            employment_preference = st.selectbox(
                "Employment Preference",
                ["Wage Employment (Job)", "Self Employment (Entrepreneurship / Micro-enterprise)", "Either / Any"],
                index=["Wage Employment (Job)", "Self Employment (Entrepreneurship / Micro-enterprise)", "Either / Any"].index(def_emp) if def_emp in ["Wage Employment (Job)", "Self Employment (Entrepreneurship / Micro-enterprise)", "Either / Any"] else 0,
            )
            recommended_trade = st.text_input("Assigned / Recommended Trade (Optional)", value=def_trade)

        submitted = st.form_submit_button("💾 Save / Update Profile", type="primary", use_container_width=True)

        if submitted:
            if not name.strip():
                st.warning("Please enter a valid name for the beneficiary.")
            else:
                profile_payload = {
                    "beneficiary_id": current_id,
                    "name": name.strip(),
                    "age": int(age),
                    "gender": gender,
                    "district": district,
                    "education_level": education_level,
                    "family_occupation": family_occupation.strip(),
                    "current_livelihood": current_livelihood.strip(),
                    "previous_work_experience": previous_work_experience.strip(),
                    "skills": skills.strip(),
                    "interests": interests.strip(),
                    "mobility_constraints": mobility_constraints,
                    "employment_preference": employment_preference,
                    "language": language,
                    "training_status": training_status,
                    "training_start_date": selected_profile.get("training_start_date") if selected_profile else None,
                    "training_completion_date": selected_profile.get("training_completion_date") if selected_profile else None,
                    "recommended_trade": recommended_trade.strip() if recommended_trade else None,
                    "created_at": selected_profile.get("created_at") if selected_profile else None,
                }
                saved = save_profile(profile_payload)
                st.success(f"Profile for {saved['name']} ({saved['beneficiary_id']}) saved successfully to storage!")

    # Display active profile summary card
    active_profile = get_profile(current_id)
    if active_profile:
        st.divider()
        st.subheader(f"Active Profile: {active_profile.get('beneficiary_id')}")
        with st.container(border=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Full Name:** {active_profile.get('name')}")
                st.write(f"**Age / Gender:** {active_profile.get('age')} yrs / {active_profile.get('gender')}")
                st.write(f"**District:** {active_profile.get('district')}")
                st.write(f"**Education:** {active_profile.get('education_level')}")
                st.write(f"**Language:** {active_profile.get('language')}")
            with col_b:
                st.write(f"**Current Livelihood:** {active_profile.get('current_livelihood') or 'None specified'}")
                st.write(f"**Previous Experience:** {active_profile.get('previous_work_experience') or 'None specified'}")
                st.write(f"**Family Background:** {active_profile.get('family_occupation') or 'None specified'}")
                st.write(f"**Mobility:** {active_profile.get('mobility_constraints')}")
                st.write(f"**Employment Pref:** {active_profile.get('employment_preference')}")
                st.write(f"**Training Status:** {active_profile.get('training_status')}")

            st.write(f"**Skills:** {active_profile.get('skills') or 'None entered'}")
            st.write(f"**Interests:** {active_profile.get('interests') or 'None entered'}")
            if active_profile.get("recommended_trade"):
                st.info(f"**Assigned / Recommended Trade:** {active_profile.get('recommended_trade')}")

        # Profile-Based Trade Recommendations
        st.subheader("🎯 Profile-Based Skilling Recommendations")
        st.caption("ℹ️ Notice: Local demand scores and monthly wages shown are prototype/demo values.")
        trades_df = get_trades_df()
        profile_matches = match_profile(
            active_profile,
            district=active_profile.get("district", "Nagpur"),
            trades_df=trades_df,
            top_n=3,
        )

        for i, m in enumerate(profile_matches, start=1):
            with st.container(border=True):
                st.markdown(
                    f"**{i}. {m['trade_name']}** · "
                    f"NSQF Level {m['nsqf_level']} · "
                    f"{m['sector']}"
                )
                cols = st.columns(3)
                cols[0].metric("Local demand score", f"{m['demand_score']:.0f}/10")
                cols[1].metric("Avg monthly wage", f"₹{m['avg_monthly_wage_inr']:,}")
                cols[2].metric("Match score", f"{m['score']:.1f}")

                st.markdown("**Recommended because:**")
                for exp in m["explanations"]:
                    st.write(exp)

    # Display list of all registered beneficiaries
    all_profiles = list_profiles()
    if all_profiles:
        st.divider()
        st.subheader(f"All Registered Beneficiaries ({len(all_profiles)})")
        summary_table = [
            {
                "ID": p.get("beneficiary_id"),
                "Name": p.get("name"),
                "Age": p.get("age"),
                "District": p.get("district"),
                "Education": p.get("education_level"),
                "Current Work": p.get("current_livelihood"),
                "Training Status": p.get("training_status"),
            }
            for p in all_profiles
        ]
        st.dataframe(summary_table, use_container_width=True)


# ===========================================================================
# PAGE 3: RESUME (FEATURE 3)
# ===========================================================================

elif page in ["Resume", "📄 Resume"]:

    render_stitch_breadcrumb("Resume")

    render_stitch_header(
        "Beneficiary Resume Generator",
        "Generate a structured one-page DOCX resume from the saved beneficiary profile and skilling recommendations.",
        demo_mode=True,
    )

    profiles = load_profiles()

    if not profiles:
        st.info("No beneficiary profiles found. Please create a profile in the 'Beneficiary Profile' section first.")
    else:
        profile_options = {
            f"{p.get('beneficiary_id', '')} - {p.get('name', 'Unnamed')} ({p.get('district', '')})": p.get("beneficiary_id")
            for p in profiles
        }
        labels = list(profile_options.keys())
        cur_act_id = st.session_state.get("active_beneficiary_id")
        cur_idx = 0
        for idx, l in enumerate(labels):
            if profile_options[l] == cur_act_id:
                cur_idx = idx
                break
        selected_label = st.selectbox("Select Beneficiary for Resume", labels, index=cur_idx)
        selected_id = profile_options[selected_label]
        if selected_id != st.session_state.get("active_beneficiary_id"):
            st.session_state.active_beneficiary_id = selected_id
            st.session_state.conv_session = ConversationSession(beneficiary_id=selected_id)
        profile = get_profile(selected_id)

        if profile:
            trades_df = get_trades_df()
            recs = match_profile(
                profile,
                trades_df=trades_df,
                district=profile.get("district", "Nagpur"),
                top_n=3,
            )

            # Generate DOCX binary data
            docx_data = generate_resume_docx(profile, recs)
            safe_name = str(profile.get("name", "beneficiary")).replace(" ", "_")
            file_name = f"Resume_{profile.get('beneficiary_id')}_{safe_name}.docx"

            col_btn1, col_btn2 = st.columns([2, 3])
            with col_btn1:
                st.download_button(
                    label="📥 Download Resume (.docx)",
                    data=docx_data,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                )

            st.divider()
            st.subheader("Resume Preview")

            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="position: relative; overflow: hidden; padding-bottom: 8px;">
                        <div style="height: 3px; background: linear-gradient(90deg, #FF9933, #000666, #138808); margin: -1rem -1rem 1rem -1rem;"></div>
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <span style="font-size: 11px; font-weight: 800; color: #E65100; background: #FFF3E0; padding: 2px 8px; border-radius: 6px;">SKILL INDIA BENEFICIARY RESUME</span>
                                <h3 style="font-size: 20px; font-weight: 800; color: #000666; margin: 4px 0 2px 0;">{profile.get('name', 'Beneficiary')}</h3>
                            </div>
                            <span style="background: #E8F5E9; color: #1B5E20; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 9999px;">✓ Verified Citizen Profile</span>
                        </div>
                        <div style="font-size: 12px; color: #454652; margin-top: 6px;">
                            <b>ID:</b> <code>{profile.get('beneficiary_id')}</code> &nbsp;|&nbsp; 
                            <b>District:</b> {profile.get('district')} &nbsp;|&nbsp; 
                            <b>Language:</b> {profile.get('language')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.divider()

                st.markdown("#### 1. Personal & Background Information")
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.write(f"**Full Name:** {profile.get('name')}")
                    st.write(f"**Age / Gender:** {profile.get('age')} / {profile.get('gender')}")
                    st.write(f"**Education Level:** {profile.get('education_level')}")
                with col_r2:
                    st.write(f"**Current Livelihood:** {profile.get('current_livelihood') or 'None specified'}")
                    st.write(f"**Family Occupation:** {profile.get('family_occupation') or 'None specified'}")
                    st.write(f"**Mobility:** {profile.get('mobility_constraints')}")

                st.write(f"**Employment Preference:** {profile.get('employment_preference')}")

                st.divider()
                st.markdown("#### 2. Skills & Aspirations")
                st.write(f"• **Stated Skills & Experience:** {profile.get('skills') or 'None specified'}")
                st.write(f"• **Learning Goals & Interests:** {profile.get('interests') or 'None specified'}")

                st.divider()
                st.markdown("#### 3. Recommended NSQF Skilling Pathways")
                for i, r in enumerate(recs, 1):
                    st.markdown(
                        f"**{i}. {r['trade_name']}** (NSQF Level {r['nsqf_level']} · {r['sector']}) — "
                        f"Avg Wage: ₹{r['avg_monthly_wage_inr']:,} | Demand: {r['demand_score']:.0f}/10"
                    )
                    for exp in r.get("explanations", []):
                        st.caption(f"   {exp}")

                st.divider()
                st.markdown("#### 4. Training Status")
                st.write(f"**Current Status:** {profile.get('training_status', 'Not Started')}")
                if profile.get("recommended_trade"):
                    st.write(f"**Assigned Trade:** {profile.get('recommended_trade')}")


# ===========================================================================
# PAGE 4: TRAINING FOLLOW-UP (FEATURE 4)
# ===========================================================================

elif page in ["Follow-up", "📅 Training Follow-up"]:

    render_stitch_breadcrumb("Follow-up")

    render_stitch_header(
        "Post-Training Livelihood Follow-up",
        "Automated post-training milestone tracking and retention surveys across 30-day, 60-day, and 180-day intervals.",
        demo_mode=True,
    )

    demo_mode = st.toggle(
        "⚡ DEMO MODE (Accelerate timeline: 30s / 60s / 180s instead of days)",
        value=True,
        help="When enabled, milestones become active in seconds rather than months for live judging demonstration.",
    )

    profiles = load_profiles()

    if not profiles:
        st.info("No beneficiary profiles found. Please create a profile in the 'Beneficiary Profile' section first.")
    else:
        profile_options = {
            f"{p.get('beneficiary_id', '')} - {p.get('name', 'Unnamed')} ({p.get('district', '')})": p.get("beneficiary_id")
            for p in profiles
        }
        labels = list(profile_options.keys())
        cur_act_id = st.session_state.get("active_beneficiary_id")
        cur_idx = 0
        for idx, l in enumerate(labels):
            if profile_options[l] == cur_act_id:
                cur_idx = idx
                break
        selected_label = st.selectbox("Select Beneficiary to Monitor", labels, index=cur_idx)
        selected_id = profile_options[selected_label]
        if selected_id != st.session_state.get("active_beneficiary_id"):
            st.session_state.active_beneficiary_id = selected_id
            st.session_state.conv_session = ConversationSession(beneficiary_id=selected_id)
        profile = get_profile(selected_id)

        if profile:
            st.divider()
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.write(f"**Beneficiary:** {profile.get('name')} (`{profile.get('beneficiary_id')}`)")
                st.write(f"**District / Language:** {profile.get('district')} / {profile.get('language')}")
                st.write(f"**Assigned Trade:** {profile.get('recommended_trade') or 'Electrician (Domestic)'}")
            with col_t2:
                status = profile.get("training_status", "Not Started")
                st.write(f"**Current Status:** `{status}`")
                comp_date = profile.get("training_completion_date")
                if comp_date:
                    st.write(f"**Completed On:** {comp_date[:19].replace('T', ' ')}")

            # Action: Mark Training Complete
            if status != "Completed":
                st.warning("Training is currently in progress or not started. Mark training complete to activate follow-up milestones.")
                trade_to_assign = profile.get("recommended_trade") or "Electrician (Domestic)"
                trade_input = st.text_input("Trade Completed", value=trade_to_assign)
                if st.button("✅ Mark Training Complete", type="primary"):
                    mark_training_complete(selected_id, trade_input)
                    st.success(f"Training marked complete for {profile.get('name')}! Milestones generated.")
                    st.rerun()
            else:
                st.subheader("Post-Training Milestones")
                milestones = get_beneficiary_followups(selected_id)

                if not milestones:
                    # Initialize milestones if not present
                    milestones = mark_training_complete(selected_id, profile.get("recommended_trade"))

                for idx, m in enumerate(milestones, 1):
                    timing = get_milestone_timing(m, demo_mode=demo_mode)
                    is_completed = m.get("status") == "Completed"
                    is_due = timing["is_due"]

                    with st.container(border=True):
                        st.markdown(f"### Milestone {idx}: {m.get('milestone')} Check-in")
                        st.caption(f"Status: **{timing['status_label']}**")

                        if is_completed:
                            st.success("✅ Survey response recorded:")
                            resp = m.get("survey_response", {})
                            c1, c2 = st.columns(2)
                            with c1:
                                st.write(f"• **Currently Working:** {resp.get('is_working')}")
                                st.write(f"• **Work Related to Training:** {resp.get('work_related_to_training')}")
                            with c2:
                                st.write(f"• **Monthly Income:** ₹{resp.get('monthly_income_inr', 0):,}")
                                st.write(f"• **Wants New Recommendation:** {resp.get('wants_new_recommendation')}")

                            # Outcome Action: If not working, trigger re-recommendation
                            if resp.get("is_working") == "No" or resp.get("wants_new_recommendation") == "Yes":
                                st.warning("⚠️ **Outcome Alert:** Previous recommendation did not result in employment.")
                                st.markdown("#### Next Best Skilling Pathways:")
                                trades_df = get_trades_df()
                                new_matches = match_profile(
                                    profile,
                                    trades_df=trades_df,
                                    district=profile.get("district", "Nagpur"),
                                    top_n=3,
                                )
                                # Filter out previously trained trade if possible to show alternatives
                                alt_matches = [
                                    nm for nm in new_matches
                                    if nm["trade_name"].lower() != str(m.get("trade_name", "")).lower()
                                ]
                                display_matches = alt_matches if alt_matches else new_matches

                                for r_i, r_m in enumerate(display_matches[:2], 1):
                                    st.info(
                                        f"**Alternative {r_i}: {r_m['trade_name']}** "
                                        f"(NSQF Level {r_m['nsqf_level']} · {r_m['sector']})\n\n"
                                        f"• Local Demand: {r_m['demand_score']:.0f}/10 | Avg Wage: ₹{r_m['avg_monthly_wage_inr']:,}\n\n"
                                        f"• Reason: {r_m['explanation_text'].replace(chr(10), ' | ')}"
                                    )
                        else:
                            st.write("Record the beneficiary's answers to the follow-up questions:")
                            with st.form(f"survey_form_{m.get('followup_id')}"):
                                q1 = st.radio(
                                    "1. Are you currently working?",
                                    ["Yes", "No"],
                                    horizontal=True,
                                    key=f"q1_{m.get('followup_id')}",
                                )
                                q2 = st.radio(
                                    "2. Is your work related to your training?",
                                    ["Yes", "Somewhat", "No"],
                                    horizontal=True,
                                    key=f"q2_{m.get('followup_id')}",
                                )
                                q3 = st.number_input(
                                    "3. What is your approximate monthly income (₹)?",
                                    min_value=0,
                                    max_value=200000,
                                    value=12000 if q1 == "Yes" else 0,
                                    step=500,
                                    key=f"q3_{m.get('followup_id')}",
                                )
                                q4 = st.radio(
                                    "4. Would you like another recommendation?",
                                    ["No", "Yes"],
                                    horizontal=True,
                                    key=f"q4_{m.get('followup_id')}",
                                )

                                submit_survey = st.form_submit_button(
                                    f"Submit {m.get('milestone')} Response",
                                    type="primary",
                                )

                                if submit_survey:
                                    response_data = {
                                        "is_working": q1,
                                        "work_related_to_training": q2,
                                        "monthly_income_inr": int(q3),
                                        "wants_new_recommendation": q4,
                                    }
                                    record_survey_response(m.get("followup_id"), response_data)
                                    st.success("Follow-up survey response saved successfully!")
                                    st.rerun()

                # Table of all follow-ups
                st.divider()
                st.subheader("All Follow-up Tracking Records")
                all_followups = load_followups()
                if all_followups:
                    summary_fol = [
                        {
                            "ID": f.get("followup_id"),
                            "Beneficiary": f.get("beneficiary_id"),
                            "Trade": f.get("trade_name"),
                            "Milestone": f.get("milestone"),
                            "Status": f.get("status"),
                            "Working?": f.get("survey_response", {}).get("is_working", "Pending") if f.get("survey_response") else "Pending",
                            "Income": f"₹{f.get('survey_response', {}).get('monthly_income_inr', 0):,}" if f.get("survey_response") else "-",
                        }
                        for f in all_followups
                    ]
                    st.dataframe(summary_fol, use_container_width=True)


# ===========================================================================
# PAGE 5: ATTENDANCE INTEGRITY (STITCH UI DESIGN - PHASE 4C)
# ===========================================================================

elif page == "Attendance":

    render_stitch_breadcrumb("Attendance")

    render_stitch_header(
        "Training Attendance",
        "Verify beneficiary presence for today's session.",
        demo_mode=True,
    )

    profiles = load_profiles()

    if not profiles:
        st.info("No beneficiary profiles found. Please create a profile in the 'Beneficiary Profile' section first.")
    else:
        profile_options = {
            f"{p.get('beneficiary_id', '')} - {p.get('name', 'Unnamed')} ({p.get('district', '')})": p.get("beneficiary_id")
            for p in profiles
        }
        labels = list(profile_options.keys())
        cur_act_id = st.session_state.get("active_beneficiary_id")
        cur_idx = 0
        for idx, l in enumerate(labels):
            if profile_options[l] == cur_act_id:
                cur_idx = idx
                break
        selected_label = st.selectbox("Select Trainee for Check-in", labels, index=cur_idx)
        selected_id = profile_options[selected_label]
        if selected_id != st.session_state.get("active_beneficiary_id"):
            st.session_state.active_beneficiary_id = selected_id
            st.session_state.conv_session = ConversationSession(beneficiary_id=selected_id)
        profile = get_profile(selected_id)

        # Initialize session state for challenge phrase if needed
        if "current_challenge" not in st.session_state:
            st.session_state.current_challenge = generate_challenge_phrase(4)

        challenge = st.session_state.current_challenge

        # Trainee info for Bento Cards
        t_name = profile.get("name", "Anita Devi") if profile else "Anita Devi"
        t_id = selected_id if profile else "BEN-2026-001"
        t_trade = profile.get("recommended_trade", "Electrician (Domestic)") if profile else "Electrician (Domestic)"
        if not t_trade:
            t_trade = "Electrician (Domestic)"

        # 4 Bento KPI Cards
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.markdown(
                f"""
                <div class="stitch-bento-card">
                    <span style="font-size: 13px; color: #454652; display: flex; align-items: center; gap: 4px;">
                        👤 Beneficiary
                    </span>
                    <span style="font-size: 18px; font-weight: 700; color: #1B1C1C; margin-top: 6px;">{t_name}</span>
                    <span style="font-size: 12px; color: #454652; margin-top: 4px;">ID: {t_id}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with b2:
            st.markdown(
                f"""
                <div class="stitch-bento-card">
                    <span style="font-size: 13px; color: #454652; display: flex; align-items: center; gap: 4px;">
                        🎓 Training Module
                    </span>
                    <span style="font-size: 18px; font-weight: 700; color: #1B1C1C; margin-top: 6px;">{t_trade}</span>
                    <span style="font-size: 12px; color: #454652; margin-top: 4px;">Week 3 · Skill Practice</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with b3:
            st.markdown(
                f"""
                <div class="stitch-bento-card">
                    <span style="font-size: 13px; color: #454652; display: flex; align-items: center; gap: 4px;">
                        📅 Date
                    </span>
                    <span style="font-size: 18px; font-weight: 700; color: #1B1C1C; margin-top: 6px;">Sep 1, 2026</span>
                    <span style="font-size: 12px; color: #454652; margin-top: 4px;">Session: 10:00 AM</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with b4:
            st.markdown(
                f"""
                <div class="stitch-bento-card">
                    <span style="font-size: 13px; color: #454652; display: flex; align-items: center; gap: 4px;">
                        📋 Status
                    </span>
                    <span style="font-size: 18px; font-weight: 700; color: #000666; margin-top: 6px; display: flex; align-items: center; gap: 4px;">
                        ⏳ Pending
                    </span>
                    <span style="font-size: 12px; color: #454652; margin-top: 4px;">Awaiting spoken check</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

        # Voice Challenge Feature Card
        with st.container(border=True):
            st.markdown("<h3 style='font-size: 20px; font-weight: 700; color: #000666; text-align: center; margin-bottom: 4px;'>Today's attendance check</h3>", unsafe_allow_html=True)
            st.markdown("<p style='font-size: 14px; color: #454652; text-align: center; margin-bottom: 12px;'>Please speak the phrase shown below clearly into your device.</p>", unsafe_allow_html=True)

            # The Phrase Box
            render_stitch_phrase_card(challenge["phrase_en"].upper())

            # Pulsing Mic Hero Component
            st.markdown(
                """
                <div class="stitch-mic-hero">
                    <div class="stitch-mic-ring-outer"></div>
                    <div class="stitch-mic-ring-inner"></div>
                    <div class="stitch-mic-button-core">
                        <span class="material-symbols-outlined" style="font-size: 40px; font-variation-settings: 'FILL' 1;">mic</span>
                    </div>
                </div>
                <div style="text-align: center; font-size: 14px; font-weight: 600; color: #454652; margin-bottom: 14px;">
                    <span class="stitch-mic-dot"></span> Tap microphone to record phrase
                </div>
                """,
                unsafe_allow_html=True,
            )

            att_audio_input = st.audio_input("Record challenge phrase", key="att_audio_mic")
            att_file_upload = st.file_uploader("...or upload recorded WAV clip", type=["wav", "flac"], key="att_uploader")

            att_bytes = None
            if att_audio_input is not None:
                att_bytes = att_audio_input.getvalue()
            elif att_file_upload is not None:
                att_bytes = att_file_upload.getvalue()

            c_btn1, c_btn2 = st.columns([2, 1])
            verify_btn = c_btn1.button("🎙️ Transcribe & Verify Attendance", type="primary", disabled=att_bytes is None, use_container_width=True)
            if c_btn2.button("🔄 New Challenge Phrase", type="secondary", use_container_width=True):
                st.session_state.current_challenge = generate_challenge_phrase(4)
                st.rerun()

            if verify_btn and att_bytes is not None:
                tmp_att_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_att:
                        tmp_att.write(att_bytes)
                        tmp_att_path = tmp_att.name

                    with st.spinner("Transcribing spoken challenge with AI4Bharat Indic Conformer ASR..."):
                        asr_model = get_asr_model()
                        lang_code = LANGUAGES.get(profile.get("language", "Hindi"), "hi")
                        att_transcript = transcribe(asr_model, tmp_att_path, lang_code, "ctc")

                    status, flagged, match_score, reason = verify_phrase_match(challenge["digits"], att_transcript)

                    record_data = {
                        "beneficiary_id": selected_id,
                        "expected_phrase": challenge["expected_phrase"],
                        "transcript": att_transcript,
                        "status": status,
                        "flagged": flagged,
                        "match_score": match_score,
                        "reason": reason,
                        "demo_note": "Demo attendance integrity — voice identity verification not implemented",
                    }
                    saved_rec = save_attendance_record(record_data)

                    st.markdown("---")
                    st.markdown(f"**Expected Phrase:** `{challenge['expected_phrase']}`")
                    st.markdown(f"**Transcribed Speech:** `{att_transcript}`")

                    if status == "Pass" and not flagged:
                        st.success(f"✅ **Attendance Verified (PASS)** — {reason} (Score: {match_score:.0%})")
                    elif status == "Pass" and flagged:
                        st.warning(f"⚠️ **Attendance Recorded (FLAGGED FOR REVIEW)** — {reason} (Score: {match_score:.0%})")
                    else:
                        st.error(f"❌ **Attendance Rejected (FAIL)** — {reason} (Score: {match_score:.0%})")

                    # Generate fresh challenge for next check-in
                    st.session_state.current_challenge = generate_challenge_phrase(4)

                except Exception as e:
                    st.error("Error during attendance transcription and verification.")
                    st.exception(e)
                finally:
                    if tmp_att_path is not None and os.path.exists(tmp_att_path):
                        try:
                            os.unlink(tmp_att_path)
                        except OSError:
                            pass

        # Prototype Disclaimer
        render_stitch_disclaimer(
            "DEMO / PROTOTYPE",
            "This demonstrates voice challenge verification. It is not biometric identity verification. In a production environment, this confirms presence and liveness, but does not authenticate the specific individual's voice print.",
        )

        # Attendance Log & Summary
        st.divider()
        st.subheader("Trainee Attendance Records")
        all_att = load_attendance()
        if all_att:
            total_att = len(all_att)
            passed_att = sum(1 for a in all_att if a.get("status") == "Pass")
            failed_att = sum(1 for a in all_att if a.get("status") == "Fail")
            flagged_att = sum(1 for a in all_att if a.get("flagged") is True)

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                render_stitch_kpi_card("Total Check-ins", total_att, "Recorded logs", icon="how_to_reg", badge_text="Total", badge_color="primary")
            with m_col2:
                render_stitch_kpi_card("Verified (Pass)", passed_att, f"{int(passed_att/total_att*100) if total_att else 0}% pass rate", icon="check_circle", badge_text="Valid", badge_color="success")
            with m_col3:
                render_stitch_kpi_card("Rejected (Fail)", failed_att, "Mismatch detected", icon="cancel", badge_text="Mismatch", badge_color="warning")
            with m_col4:
                render_stitch_kpi_card("Flagged for Review", flagged_att, "Supervisory audit", icon="flag", badge_text="Audit", badge_color="warning")

            att_table = [
                {
                    "Record ID": a.get("record_id"),
                    "Trainee": a.get("beneficiary_id"),
                    "Timestamp": a.get("timestamp", "")[:19].replace("T", " "),
                    "Expected": a.get("expected_phrase"),
                    "Transcribed": a.get("transcript"),
                    "Status": a.get("status"),
                    "Flagged": "⚠️ Yes" if a.get("flagged") else "No",
                }
                for a in reversed(all_att)
            ]
            st.dataframe(att_table, use_container_width=True)


# ===========================================================================
# PAGE 6: MONITORING DASHBOARD (STITCH UI DESIGN - PHASE 4C)
# ===========================================================================

elif page == "Dashboard":

    render_stitch_breadcrumb("Dashboard")

    render_stitch_header(
        "Livelihood Monitoring Dashboard",
        "Aggregated program analytics: beneficiary enrollment, training completions, post-training employment retention, and attendance integrity.",
        demo_mode=True,
    )

    profiles = load_profiles()
    followups = load_followups()
    attendance = load_attendance()
    trades_df = get_trades_df()

    # Section 1: Beneficiary & Skilling Overview
    st.subheader("1. Beneficiary Enrollment & Training Progress")
    total_b = len(profiles)
    completed_train = sum(1 for p in profiles if p.get("training_status") == "Completed")
    in_progress_train = sum(1 for p in profiles if p.get("training_status") == "In Progress")
    not_started_train = sum(1 for p in profiles if p.get("training_status") == "Not Started")
    assigned_trades = sum(1 for p in profiles if p.get("recommended_trade"))

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    with b_col1:
        render_stitch_kpi_card("Total Beneficiaries", total_b, "Enrolled citizens", icon="groups", badge_text="Active", badge_color="primary")
    with b_col2:
        render_stitch_kpi_card("Training Completed", completed_train, f"{int(completed_train/total_b*100) if total_b else 0}% completion rate", icon="school", badge_text="Certified", badge_color="success")
    with b_col3:
        render_stitch_kpi_card("In Progress", in_progress_train, "Active batch trainees", icon="hourglass_top", badge_text="Ongoing", badge_color="warning")
    with b_col4:
        render_stitch_kpi_card("Assigned Pathways", assigned_trades, "NSQF trade mapped", icon="route", badge_text="Mapped", badge_color="primary")

    st.divider()

    # Section 2: Post-Training Follow-up & Employment Outcomes
    st.subheader("2. Post-Training Employment & Retention Outcomes")
    total_fol = len(followups)
    completed_fol = sum(1 for f in followups if f.get("status") == "Completed")
    
    working_count = 0
    unemployed_count = 0
    incomes = []

    for f in followups:
        resp = f.get("survey_response")
        if resp:
            if resp.get("is_working") == "Yes":
                working_count += 1
                inc = resp.get("monthly_income_inr", 0)
                if inc > 0:
                    incomes.append(inc)
            elif resp.get("is_working") == "No":
                unemployed_count += 1

    avg_inc = sum(incomes) / len(incomes) if incomes else 0

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        render_stitch_kpi_card("Surveys Completed", completed_fol, f"Out of {total_fol} milestones", icon="assignment_turned_in", badge_text="Verified", badge_color="primary")
    with f_col2:
        render_stitch_kpi_card("Employed Post-Training", working_count, f"{int(working_count/completed_fol*100) if completed_fol else 0}% retention rate", icon="work", badge_text="Employed", badge_color="success")
    with f_col3:
        render_stitch_kpi_card("Seeking Re-skilling", unemployed_count, "Transitioning or open", icon="published_with_changes", badge_text="Support", badge_color="warning")
    with f_col4:
        inc_str = f"₹{avg_inc:,.0f}/mo" if avg_inc > 0 else "N/A"
        render_stitch_kpi_card("Avg Monthly Income", inc_str, "Self-reported wage", icon="payments", badge_text="Income", badge_color="success")

    st.divider()

    # Section 3: Attendance Integrity Metrics
    st.subheader("3. Trainee Attendance Integrity Check Overview")
    total_att = len(attendance)
    passed_att = sum(1 for a in attendance if a.get("status") == "Pass")
    failed_att = sum(1 for a in attendance if a.get("status") == "Fail")
    flagged_att = sum(1 for a in attendance if a.get("flagged") is True)

    a_col1, a_col2, a_col3, a_col4 = st.columns(4)
    with a_col1:
        render_stitch_kpi_card("Attendance Checks", total_att, "Phrase verification logs", icon="how_to_reg", badge_text="Total", badge_color="primary")
    with a_col2:
        render_stitch_kpi_card("Verified (Pass)", passed_att, f"{int(passed_att/total_att*100) if total_att else 0}% integrity rate", icon="verified", badge_text="Valid", badge_color="success")
    with a_col3:
        render_stitch_kpi_card("Rejected (Fail)", failed_att, "Mismatch challenges", icon="cancel", badge_text="Failed", badge_color="warning")
    with a_col4:
        render_stitch_kpi_card("Flagged for Audit", flagged_att, "Supervisor review queue", icon="flag", badge_text="Audit", badge_color="warning")

    st.divider()

    # Section 4: Data Tables
    st.subheader("4. Detailed Records & District Demand")

    tab1, tab2, tab3 = st.tabs(["Beneficiaries", "NSQF Trade Demand", "Follow-up Surveys"])

    with tab1:
        if profiles:
            p_table = [
                {
                    "ID": p.get("beneficiary_id"),
                    "Name": p.get("name"),
                    "District": p.get("district"),
                    "Education": p.get("education_level"),
                    "Preference": p.get("employment_preference"),
                    "Status": p.get("training_status"),
                    "Trade": p.get("recommended_trade") or "General",
                }
                for p in profiles
            ]
            st.dataframe(p_table, use_container_width=True)
        else:
            st.info("No beneficiary records yet.")

    with tab2:
        st.dataframe(trades_df[["trade_name", "sector", "nsqf_level", "demand_nagpur", "demand_default", "avg_monthly_wage_inr"]], use_container_width=True)

    with tab3:
        if followups:
            fol_table = [
                {
                    "Follow-up ID": f.get("followup_id"),
                    "Beneficiary": f.get("beneficiary_id"),
                    "Trade": f.get("trade_name"),
                    "Milestone": f.get("milestone"),
                    "Status": f.get("status"),
                    "Working?": f.get("survey_response", {}).get("is_working", "-") if f.get("survey_response") else "-",
                    "Income": f"₹{f.get('survey_response', {}).get('monthly_income_inr', 0):,}" if f.get("survey_response") else "-",
                }
                for f in followups
            ]
            st.dataframe(fol_table, use_container_width=True)
        else:
            st.info("No follow-up records yet.")


# ===========================================================================
# PAGE 7: TRAINING (STITCH UI DESIGN - PHASE 4C)
# ===========================================================================

elif page == "Training":

    render_stitch_breadcrumb("Training")

    render_stitch_header(
        "Training Modules & NSQF Pathways",
        "Explore accredited training modules and regional skill development courses.",
        demo_mode=True,
    )

    active_b_id = st.session_state.get("active_beneficiary_id")
    active_prof = get_profile(active_b_id) if active_b_id else None
    if active_prof:
        st.markdown(
            f"""
            <div style="background-color: #f0eded; border: 1px solid #c6c5d4; border-radius: 12px; padding: 12px 16px; margin-bottom: 16px;">
                <span style="font-weight: 700; color: #000666;">Active Trainee: {active_prof.get('name', 'Unnamed')} ({active_prof.get('beneficiary_id')})</span> &nbsp;|&nbsp;
                <span><b>Assigned Trade:</b> {active_prof.get('recommended_trade') or 'Not Assigned'}</span> &nbsp;|&nbsp;
                <span><b>District:</b> {active_prof.get('district', 'Nagpur')}</span> &nbsp;|&nbsp;
                <span><b>Status:</b> {active_prof.get('training_status', 'Not Started')}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    trades_df = get_trades_df()
    st.subheader("Accredited NSQF Training Modules")
    st.dataframe(trades_df, use_container_width=True)