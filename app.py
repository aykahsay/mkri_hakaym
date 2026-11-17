"""
Mkri Hakaym (ምኽሪ ሓካይም) - Interactive Medical AI & Phone Simulator Dashboard
Built with Streamlit for testing Tigrinya voice interactions, clinical triage,
and knowledge library exploration.
"""
import pandas as pd
import streamlit as st

from brain.rag_engine import MedicalRAGEngine
from brain.triage_rules import RED_FLAGS
from collector.build_qa_csv import CSV_DATASET_PATH, DatasetBuilder

# Page Configuration
st.set_page_config(
    page_title="ምኽሪ ሓካይም - Mkri Hakaym",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_resource
def get_engine():
    return MedicalRAGEngine()

engine = get_engine()
builder = DatasetBuilder()

# Custom Header
st.title("🩺 ምኽሪ ሓካይም (Mkri Hakaym)")
st.caption("Voice-First Medical AI for 2G / Basic Phones in Tigrinya • Grounded on Tigrai TV 'ማዕዳ ሓካይም'")

# Sidebar
with st.sidebar:
    st.header("⚙️ System Status")
    st.success(f"🟢 Medical Brain Online ({len(engine.knowledge_entries)} verified entries)")
    st.info("Language: ትግርኛ (Tigrinya)")
    st.info("Telephony: 2G / G.711 / PSTN Ready")

    st.divider()
    st.subheader("📚 Broadcast Topics")
    topics = set(e.get("topic", "") for e in engine.knowledge_entries)
    for t in sorted(topics):
        st.write(f"• {t}")

    st.divider()
    st.markdown("**Emergency Protocol (ቀያሕቲ ምልክታት)**")
    st.warning("Any call mentioning severe bleeding, pre-eclampsia, or respiratory distress triggers immediate hospital triage.")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📞 2G Phone Simulator", 
    "📖 Knowledge Explorer", 
    "🚨 Triage Rules", 
    "📊 Medical Q&A Dataset (CSV)"
])

# Tab 1: 2G Phone Simulator
with tab1:
    st.subheader("Interactive Telephony Call Simulation")
    st.write("Simulate what a caller on a basic button phone (dumbphone/small phone) experiences:")

    col_phone, col_response = st.columns([1, 1.4])

    with col_phone:
        st.markdown("### 📱 Basic Phone Keypad")
        dial_options = {
            "Select or Type a Query": "",
            "1. Maternal Health: ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?": "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?",
            "2. Nutrition: ጥንስቲ እንታይ ዓይነት ምግቢ ክትበልዕ ኣለዋ?": "ጥንስቲ እንታይ ዓይነት ምግቢ ክትበልዕ ኣለዋ?",
            "3. Emergency: ደም ፈሲሱኒ እንታይ ክገብር?": "ደም ፈሲሱኒ እንታይ ክገብር?",
            "4. Pediatrics: ህጻን ውጽኣትን ተምላስን እንተኣጋጢምዎ እንታይ ክንገብር?": "ህጻን ውጽኣትን ተምላስን እንተኣጋጢምዎ እንታይ ክንገብር?",
            "5. Respiratory: ህጻን ሰዓልን ምሕጻር እስትንፋስን እንተሃልይዎ?": "ህጻን ሰዓልን ምሕጻር እስትንፋስን እንተሃልይዎ?",
            "6. Chronic: ኩላሊትና ጥዕናኡ ንኽሕሉ እንታይ ክንገብር ኣለና?": "ኩላሊትና ጥዕናኡ ንኽሕሉ እንታይ ክንገብር ኣለና?",
            "7. Diabetes: ምልክታት ሕማም ሽኮር እንታይ እዮም?": "ምልክታት ሕማም ሽኮር እንታይ እዮም?",
        }
        selected_preset = st.selectbox("Quick Voice Presets (Spoken Tigrinya):", list(dial_options.keys()))
        
        custom_input = st.text_input(
            "Or Type Spoken Tigrinya Input:",
            value=dial_options[selected_preset] if dial_options[selected_preset] else ""
        )

        call_button = st.button("📞 Place Call / Speak Question", type="primary", use_container_width=True)

    with col_response:
        st.markdown("### 🔊 In-Call Audio Playback")
        if call_button and custom_input.strip():
            result = engine.answer_caller_query(custom_input)

            if result["is_emergency"]:
                st.error(f"🚨 **EMERGENCY DETECTED! ({result['urgency_level']})**")
                st.markdown(f"**Clinical Action:** {result['action']}")
            else:
                st.success(f"✅ **Routine Health Guidance ({result['urgency_level']})**")
                st.markdown(f"**Verified Source:** {result['source_used']}")

            st.chat_message("assistant").write(result["spoken_response_ti"])

            if result.get("bullet_points_ti"):
                st.markdown("**Key Medical Points (for SMS/Follow-up):**")
                for bullet in result["bullet_points_ti"]:
                    st.markdown(f"- {bullet}")
        else:
            st.info("Pick a voice preset on the left or type a health question to simulate the live call response.")

# Tab 2: Knowledge Base Explorer
with tab2:
    st.subheader(f"Verified Clinical Guidance ({len(engine.knowledge_entries)} Episodes)")
    search_term = st.text_input("🔍 Search Knowledge Base in Tigrinya or English:")

    entries_to_show = engine.knowledge_entries
    if search_term.strip():
        entries_to_show = engine.search(search_term, top_k=10)

    for entry in entries_to_show:
        with st.expander(f"📌 [{entry.get('id')}] {entry.get('topic')}"):
            st.markdown(f"**ሕቶ (Question):** {entry.get('question_ti')}")
            st.markdown(f"**ምላሽ ዶክተር (Doctor Answer):** {entry.get('answer_ti')}")
            st.markdown(f"**ምንጪ (Source):** {entry.get('source_title', 'ማዕዳ ሓካይም')}")
            if entry.get("key_advice_bullets_ti"):
                st.markdown("**ቀንድታት ነጥብታት:**")
                for b in entry["key_advice_bullets_ti"]:
                    st.markdown(f"- {b}")
            if entry.get("warning_signs_ti"):
                st.markdown("**ቀያሕቲ ምልክታት (Warning Signs):**")
                for w in entry["warning_signs_ti"]:
                    st.markdown(f"- ⚠️ {w}")

# Tab 3: Triage Rules Explorer
with tab3:
    st.subheader("Clinical Red-Flag Directory (ቀያሕቲ ምልክታት)")
    for cond_key, rule in RED_FLAGS.items():
        with st.container():
            st.markdown(f"#### ⚠️ {rule['title']}")
            st.markdown(f"- **Urgency Level:** `{rule['level']}`")
            trigger_list = rule.get("terms") or rule.get("regex_patterns", [])
            st.markdown(f"- **Trigger Keywords:** `{', '.join(trigger_list)}`")
            st.markdown(f"- **Spoken Tigrinya Alert:** *\"{rule['msg_ti']}\"*")
            st.markdown(f"- **Action Protocol:** {rule['action']}")
            st.divider()

# Tab 4: CSV Dataset Manager
with tab4:
    st.subheader("📊 Structured Clinical Q&A Dataset (CSV / Excel)")
    st.write(f"This dataset is stored at `{CSV_DATASET_PATH}` and powers both the 2G Phone Gateway and Fine-Tuning.")

    if CSV_DATASET_PATH.exists():
        df = pd.read_csv(CSV_DATASET_PATH, encoding="utf-8-sig")
        
        # Action Bar
        col_down, col_count = st.columns([1, 3])
        with col_down:
            csv_data = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label="⬇️ Download Dataset CSV",
                data=csv_data,
                file_name="medical_qa_dataset.csv",
                mime="text/csv",
                type="primary",
            )
        with col_count:
            st.info(f"Total Rows: **{len(df)}** Clinical Q&A records collected.")

        st.dataframe(df, use_container_width=True)

    st.divider()
    st.markdown("### ➕ Add New Q&A Record from Video Broadcast")
    with st.form("add_qa_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_id = st.text_input("Record ID (e.g. QA-ANC-005):", value=f"QA-NEW-{len(builder.records)+1:03d}")
            new_topic_ti = st.text_input("Topic in Tigrinya (ዛዕባ):", placeholder="ክትትል ጥንሲ")
            new_topic_en = st.text_input("Topic in English:", placeholder="Antenatal Care")
            new_vid_url = st.text_input("Video URL:", value="https://www.youtube.com/watch?v=2FHD7FWWYNc")
            new_vid_title = st.text_input("Video Title:", value="ማዕዳ ሓካይም ፡ ዛዕባ፦ክትትል ጥንሲ - ቴሌቪዥን ትግራይ")
            new_triage = st.selectbox("Triage Urgency Level:", ["ROUTINE", "HIGH", "CRITICAL"])

        with col2:
            new_q_ti = st.text_area("Caller Question in Tigrinya (ሕቶ ብትግርኛ):")
            new_a_ti = st.text_area("Doctor Answer in Tigrinya (ምላሽ ሓኪም ብትግርኛ):")
            new_takeaways = st.text_input("Key Takeaways (semicolon separated):", placeholder="ቀዳማይ ክትትል ምግባር; ብዙሕ ማይ ምስታይ")
            new_dangers = st.text_input("Danger Signs (semicolon separated):", placeholder="ምፍሳስ ደም; ዓይኒ ምፍዛዝ")

        submit_new = st.form_submit_button("💾 Save Record to CSV Dataset")
        if submit_new:
            if not new_q_ti.strip() or not new_a_ti.strip():
                st.error("Please provide both the Question and the Answer in Tigrinya.")
            else:
                new_record = {
                    "id": new_id,
                    "topic_ti": new_topic_ti or "ሓፈሻዊ ጥዕና",
                    "topic_en": new_topic_en or "General Health",
                    "video_id": "2FHD7FWWYNc",
                    "video_title": new_vid_title,
                    "video_url": new_vid_url,
                    "caller_question_ti": new_q_ti,
                    "caller_question_en": "",
                    "doctor_answer_ti": new_a_ti,
                    "doctor_answer_en": "",
                    "key_clinical_takeaways_ti": new_takeaways,
                    "danger_signs_ti": new_dangers,
                    "triage_level": new_triage,
                    "tags": "ማዕዳ ሓካይም, ጥዕና",
                }
                builder.add_qa_record(new_record)
                st.success(f"Saved {new_id} to CSV! Refresh to view updated table.")
                st.rerun()
