import streamlit as st
import json
import os
import base64
from datetime import datetime, time as dt_time, timedelta
import streamlit.components.v1 as components
import time
import razorpay
import config
st.set_page_config(
    page_title="शाला समय-सारणी प्रो...",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# Razorpay पेमेंट लिंक एकीकरण (ऑटो-रीडायरेक्ट एवं ऑटो-अनलॉक सहित)
# -------------------------------------------------------------
RAZORPAY_KEY_ID = config.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = config.RAZORPAY_KEY_ID
ENTRY_FEE_INR = 10
PORTAL_LIVE_URL = "https://shala-timetable-app-by-alok-kumar-singh.streamlit.app"

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

if "is_paid" not in st.session_state:
    st.session_state.is_paid = False
if "plink_id" not in st.session_state:
    st.session_state.plink_id = None
if "plink_url" not in st.session_state:
    st.session_state.plink_url = None

# 1. ऑटो-रीडायरेक्ट से आने वाले URL पैरामीटर्स की स्वचालित जांच
query_params = st.query_params
if not st.session_state.is_paid:
    # यदि यूज़र पेमेंट के बाद Razorpay द्वारा इसी पेज पर ऑटो-रीडायरेक्ट होकर आया है
    if "razorpay_payment_link_status" in query_params:
        pl_status = query_params.get("razorpay_payment_link_status")
        if pl_status == "paid":
            st.session_state.is_paid = True
            st.query_params.clear()
            st.rerun()
    elif "razorpay_payment_id" in query_params:
        st.session_state.is_paid = True
        st.query_params.clear()
        st.rerun()

if not st.session_state.is_paid:
    st.markdown(
        """
        <div style="text-align: center; background: #f8fafc; border: 2px solid #1e3a8a; border-radius: 12px; padding: 25px; max-width: 520px; margin: 30px auto;">
            <h2 style="color: #1e3a8a; margin-bottom: 8px;">🔒 शाला समय-सारणी प्रो पोर्टल</h2>
            <p style="color: #475569; font-size: 15px;">पोर्टल का उपयोग करने के लिए <b>₹10</b> का शुल्क आवश्यक है।</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # नया पेमेंट लिंक बनाना (Callback URL के साथ ताकि अपने आप वापस आ सके)
    if not st.session_state.plink_id:
        try:
            link_payload = {
                "amount": ENTRY_FEE_INR * 100,  # 1000 पैसे = ₹10
                "currency": "INR",
                "description": "Shala TimeTable Pro Access Fee",
                "callback_url": PORTAL_LIVE_URL,
                "callback_method": "get",
                "notify": {"sms": False, "email": False},
                "reminder_enable": False
            }
            plink = client.payment_link.create(link_payload)
            st.session_state.plink_id = plink.get("id")
            st.session_state.plink_url = plink.get("short_url")
        except Exception as e:
            st.error(f"पेमेंट गेटवे से जुड़ने में समस्या: {e}")
            st.stop()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.plink_url:
            st.markdown(
                f"""
                <div style="text-align: center; margin: 15px 0;">
                    <a href="{st.session_state.plink_url}" target="_blank" style="background-color: #2563eb; color: white; padding: 14px 28px; font-size: 16px; font-weight: bold; border-radius: 8px; text-decoration: none; display: inline-block; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                        👉 ₹10 का भुगतान करें (UPI / QR / कार्ड)
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

            status_placeholder = st.empty()
            status_placeholder.info("⚡ भुगतान पूरा होते ही यह पोर्टल अपने आप अनलॉक हो जाएगा...")

            # स्वचालित बैकग्राउंड सत्यापन (यदि यूज़र पुराने टैब पर ही खुला छोड़ दे)
            try:
                check_link = client.payment_link.fetch(st.session_state.plink_id)
                if check_link.get("status") == "paid":
                    st.session_state.is_paid = True
                    status_placeholder.success("✅ भुगतान सफल! पोर्टल खुल रहा है...")
                    time.sleep(1)
                    st.rerun()
            except Exception:
                pass

            # बैकअप बटन (यदि किसी नेटवर्क समस्या से ऑटो-रीडायरेक्ट न चले)
            if st.button("🔄 स्थिति सत्यापित करें (यदि स्वतः न खुले)", use_container_width=True):
                try:
                    check_link = client.payment_link.fetch(st.session_state.plink_id)
                    if check_link.get("status") == "paid":
                        st.session_state.is_paid = True
                        st.success("✅ भुगतान सत्यापित हो गया! पोर्टल अनलॉक हो रहा है...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("⚠️ भुगतान अभी प्राप्त नहीं हुआ है। कृपया भुगतान पूरा करने के बाद पुनः क्लिक करें।")
                except Exception as err:
                    st.error(f"सत्यापन में त्रुटि: {err}")

    # ऑटो-रिफ्रेश पोलर: हर 4 सेकंड में स्थिति चेक करेगा ताकि बिना क्लिक किए भी पेज अनलॉक हो जाए
    time.sleep(4)
    st.rerun()

# -------------------------------------------------------------
# 1. UI एवं तिरंगा स्टाइलिंग
# -------------------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #edf2f7 100%);
        border-top: 8px solid #FF9933 !important;
        border-bottom: 8px solid #138808 !important;
        border-left: 6px solid #0284c7 !important;
        border-right: 6px solid #0284c7 !important;
        box-sizing: border-box;
        min-height: 100vh;
    }
    .stRadio [role="radiogroup"] {
        display: flex;
        gap: 14px;
        justify-content: center;
        flex-wrap: wrap;
    }
    .stRadio [role="radiogroup"] > label {
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: bold !important;
        font-size: 14px !important;
        cursor: pointer;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 0 rgba(0,0,0,0.2), 0 5px 8px rgba(0,0,0,0.15);
        color: #ffffff !important;
    }
    .stRadio [role="radiogroup"] > label:active {
        transform: translateY(3px);
        box-shadow: 0 1px 0 rgba(0,0,0,0.2);
    }
    .stRadio [role="radiogroup"] > label:nth-child(1) {
        background: linear-gradient(180deg, #fb923c 0%, #ea580c 100%) !important;
        border: 1px solid #c2410c !important;
    }
    .stRadio [role="radiogroup"] > label:nth-child(2) {
        background: linear-gradient(180deg, #38bdf8 0%, #0284c7 100%) !important;
        border: 1px solid #0369a1 !important;
    }
    .stRadio [role="radiogroup"] > label:nth-child(3) {
        background: linear-gradient(180deg, #a855f7 0%, #7e22ce 100%) !important;
        border: 1px solid #6b21a8 !important;
    }
    .stRadio [role="radiogroup"] > label:nth-child(4) {
        background: linear-gradient(180deg, #22c55e 0%, #15803d 100%) !important;
        border: 1px solid #166534 !important;
    }
</style>
""", unsafe_allow_html=True)

if "active_main_tab" not in st.session_state:
    st.session_state.active_main_tab = "⚙️ विद्यालय विन्यास एवं समय"

if "active_teacher_subtab" not in st.session_state:
    st.session_state.active_teacher_subtab = "✏️ अध्यापक विवरण संशोधित करें"

def trigger_toast(msg, icon="✅"):
    st.toast(f"{icon} {msg}")

# -------------------------------------------------------------
# 2. समय गणना (शिविरा पंचांग)
# -------------------------------------------------------------
SHIFT_CONFIGS = {
    "एकल पारी - ग्रीष्मकालीन (07:30 AM - 01:00 PM)": {"start": "07:30", "end": "13:00"},
    "एकल पारी - शीतकालीन (10:00 AM - 04:00 PM)": {"start": "10:00", "end": "16:00"},
    "दो पारी - ग्रीष्मकालीन (प्रथम पारी: 07:00 AM - 12:30 PM)": {"start": "07:00", "end": "12:30"},
    "दो पारी - ग्रीष्मकालीन (द्वितीय पारी: 12:30 PM - 06:00 PM)": {"start": "12:30", "end": "18:00"},
    "दो पारी - शीतकालीन (प्रथम पारी: 07:30 AM - 12:30 PM)": {"start": "07:30", "end": "12:30"},
    "दो पारी - शीतकालीन (द्वितीय पारी: 12:30 PM - 05:30 PM)": {"start": "12:30", "end": "17:30"}
}

def calculate_accurate_timings(shift_name, total_periods):
    cfg = SHIFT_CONFIGS.get(shift_name, SHIFT_CONFIGS["एकल पारी - ग्रीष्मकालीन (07:30 AM - 01:00 PM)"])
    start_dt = datetime.strptime(cfg["start"], "%H:%M")
    end_dt = datetime.strptime(cfg["end"], "%H:%M")
    
    total_minutes = int((end_dt - start_dt).total_seconds() / 60)
    teaching_minutes = total_minutes - 60
    
    base_duration = teaching_minutes // total_periods
    remainder = teaching_minutes % total_periods
    
    durations = [base_duration] * total_periods
    for i in range(remainder):
        durations[total_periods - 1 - i] += 1
        
    timings = []
    prayer_time_str = f"{start_dt.strftime('%I:%M %p')} - {(start_dt + timedelta(minutes=30)).strftime('%I:%M %p')}"
    
    curr_time = start_dt + timedelta(minutes=30)
    half_period = total_periods // 2
    recess_time_str = ""
    
    for idx, dur in enumerate(durations):
        if idx == half_period:
            rec_start = curr_time
            rec_end = curr_time + timedelta(minutes=30)
            recess_time_str = f"{rec_start.strftime('%I:%M %p')} - {rec_end.strftime('%I:%M %p')}"
            curr_time = rec_end
            
        p_start_str = curr_time.strftime("%I:%M %p")
        p_end = curr_time + timedelta(minutes=dur)
        p_end_str = p_end.strftime("%I:%M %p")
        timings.append(f"{p_start_str} - {p_end_str}")
        curr_time = p_end
        
    return timings, prayer_time_str, recess_time_str

# -------------------------------------------------------------
# 3. विषय एवं पदनाम डायरेक्टरी
# -------------------------------------------------------------
RAJASTHAN_GEO_DATA = {
    "जयपुर": ["सांभर लेक", "आमेर", "चाकसू", "बस्सी", "झोटवाड़ा", "कोटपुतली", "शाहपुरा", "जमवारामगढ़", "विराटनगर", "जालसू", "गोविंदगढ़", "तुंगा", "आंधी"],
    "जयपुर (ग्रामीण)": ["सांभर लेक", "चाकसू", "बस्सी", "जमवारामगढ़", "विराटनगर", "कोटखावदा", "माधोराजपुरा", "जोबनेर", "किशनगढ़ रेनवाल"],
    "जोधपुर": ["मंडोर", "ओसियां", "बालेसर", "शेरगढ़", "बिलाड़ा", "लूणी", "बावड़ी", "तिंवरी", "केरू", "देचू", "सेखाला"],
    "अजमेर": ["अजमेर ग्रामीण", "किशनगढ़", "श्रीनगर", "पीसांगन", "जवाजा", "अरांई", "सिलोरा"],
    "अलवर": ["अलवर", "उमरैण", "थानागाजी", "राजगढ़", "रैणी", "रामगढ़", "लक्ष्मणगढ़", "मालाखेड़ा"],
    "उदयपुर": ["बड़गांव", "गिर्वा", "कोटड़ा", "झाड़ोल", "गोगुंदा", "मावली", "वल्लभनगर"],
    "बीकानेर": ["बीकानेर", "नोखा", "कोलायत", "लूणकरणसर", "श्रीडूंगरगढ़", "खाजूवाला"],
    "कोटा": ["लाडपुरा", "सांगोद", "इटावा", "सुल्तानपुर", "खैराबाद"]
}

SUBJECT_DIRECTORY = [
    "हिन्दी", "अंग्रेजी", "गणित", "विज्ञान", "सामाजिक विज्ञान", "तृतीय भाषा (संस्कृत)",
    "तृतीय भाषा (उर्दू)", "पर्यावरण अध्ययन", "कला/खेल", "अभ्यास कार्य",
    "कम्प्यूटर शिक्षा", "सूचना प्रौद्योगिकी (IT)",
    "अनिवार्य हिन्दी", "अनिवार्य अंग्रेजी", "हिन्दी साहित्य", "राजनीति विज्ञान",
    "इतिहास", "भूगोल", "भौतिक विज्ञान", "रसायन विज्ञान", "जीव विज्ञान",
    "कृषि विज्ञान", "कृषि जीव विज्ञान", "कृषि रसायन",
    "प्रायोगिक कार्य", "पुस्तकालय / उपचारात्मक"
]

DESIGNATIONS = [
    "प्रधानाचार्य (Principal)",
    "उप-प्रधानाचार्य (Vice Principal)",
    "प्राध्यापक / व्याख्याता (Lecturer)",
    "वरिष्ठ अध्यापक (Sr. Teacher - Gr II)",
    "अध्यापक लेवल-2 (Teacher L-2)",
    "अध्यापक लेवल-1 (Teacher L-1)",
    "पंचायत शिक्षक (Panchayat Shikshak)",
    "वरिष्ठ कम्प्यूटर अनुदेशक (Senior Computer Instructor)",
    "बेसिक कम्प्यूटर अनुदेशक (Basic Computer Instructor)",
    "प्रबोधक (Prabodhak)",
    "शारीरिक शिक्षक (PTI)",
    "पुस्तकालयाध्यक्ष (Librarian)",
    "विद्या संबल योजना कार्मिक (Vidya Sambalan)",
    "प्रतिनियुक्ति पर कार्यरत अध्यापक (Deputation)",
    "इंटर्नशिप शिक्षक (B.Ed. / D.El.Ed. / BSTC Intern)",
    "अन्य शिक्षण योग्य कार्मिक (Other Qualified Staff)"
]

# -------------------------------------------------------------
# 4. अधिकृत 19 शिक्षक
# -------------------------------------------------------------
STANDARD_TEACHERS = [
    {"name": "MANJU JATAV", "desig": "प्रधानाचार्य (Principal)", "subjects": []},
    {"name": "DEEWAN SINGH MEENA", "desig": "उप-प्रधानाचार्य (Vice Principal)", "subjects": ["विज्ञान", "इतिहास"]},
    {"name": "JAYANTI SINGH", "desig": "प्राध्यापक / व्याख्याता (Lecturer)", "subjects": ["हिन्दी", "अनिवार्य हिन्दी", "हिन्दी साहित्य"]},
    {"name": "SHIMBHU SINGH", "desig": "प्राध्यापक / व्याख्याता (Lecturer)", "subjects": ["सामाजिक विज्ञान", "राजनीति विज्ञान"]},
    {"name": "SUNITA", "desig": "प्रतिनियुक्ति पर कार्यरत अध्यापक (Deputation)", "subjects": ["जीव विज्ञान", "कृषि जीव विज्ञान", "प्रायोगिक कार्य"]},
    {"name": "SANDEEP", "desig": "विद्या संबल योजना कार्मिक (Vidya Sambalan)", "subjects": ["भौतिक विज्ञान", "प्रायोगिक कार्य"]},
    {"name": "ALOK KUMAR SINGH", "desig": "वरिष्ठ अध्यापक (Sr. Teacher - Gr II)", "subjects": ["विज्ञान", "रसायन विज्ञान", "कृषि रसायन", "प्रायोगिक कार्य"]},
    {"name": "RAHUL KUMAR", "desig": "प्रतिनियुक्ति पर कार्यरत अध्यापक (Deputation)", "subjects": ["अंग्रेजी", "अनिवार्य अंग्रेजी"]},
    {"name": "BHAGWAN SAHAI JAT", "desig": "वरिष्ठ अध्यापक (Sr. Teacher - Gr II)", "subjects": ["तृतीय भाषा (संस्कृत)"]},
    {"name": "ASHUTOSH SHARMA", "desig": "प्रतिनियुक्ति पर कार्यरत अध्यापक (Deputation)", "subjects": ["गणित"]},
    {"name": "VIJAY PRAKASH SHARMA", "desig": "अध्यापक लेवल-2 (Teacher L-2)", "subjects": ["अंग्रेजी"]},
    {"name": "VIJENDRA KUMAR JAIMINI", "desig": "अध्यापक लेवल-2 (Teacher L-2)", "subjects": ["हिन्दी"]},
    {"name": "KIRAN KUMARI", "desig": "अध्यापक लेवल-2 (Teacher L-2)", "subjects": ["सामाजिक विज्ञान"]},
    {"name": "LADU RAM", "desig": "प्रतिनियुक्ति पर कार्यरत अध्यापक (Deputation)", "subjects": ["गणित", "विज्ञान"]},
    {"name": "RAJESH KUMAR KUMAWAT", "desig": "पंचायत शिक्षक (Panchayat Shikshak)", "subjects": ["गणित", "विज्ञान"]},
    {"name": "MUKESH YADAV", "desig": "बेसिक कम्प्यूटर अनुदेशक (Basic Computer Instructor)", "subjects": ["विज्ञान", "कृषि विज्ञान", "प्रायोगिक कार्य"]},
    {"name": "GANGA RAM DUKYA", "desig": "अध्यापक लेवल-1 (Teacher L-1)", "subjects": ["गणित", "पर्यावरण अध्ययन", "कला/खेल"]},
    {"name": "PRAMILA YADAV", "desig": "अध्यापक लेवल-1 (Teacher L-1)", "subjects": ["हिन्दी", "अंग्रेजी", "कला/खेल"]},
    {"name": "USHA KUMARI", "desig": "पंचायत शिक्षक (Panchayat Shikshak)", "subjects": ["गणित", "अंग्रेजी", "पर्यावरण अध्ययन"]}
]

# -------------------------------------------------------------
# 5. डेटाबेस स्वच्छता एवं ऑटो-पॉलीफ़िल
# -------------------------------------------------------------
MY_SCHOOL_FILE = "saved_timetable_state.json"
UNIVERSAL_FILE = "universal_school_timetable_data.json"

st.sidebar.title("🎛️ कार्यक्षेत्र चयन")
app_mode = st.sidebar.radio(
    "किस टाइम-टेबल पर कार्य करना चाहते हैं?",
    ["🏫 मेरा विद्यालय (रोजड़ी - सेव किया हुआ)", "🌐 सार्वभौमिक मोड (नया विद्यालय बनाएं)"]
)

ACTIVE_FILE = MY_SCHOOL_FILE if app_mode.startswith("🏫") else UNIVERSAL_FILE

def clean_and_sanitize_teachers(t_list):
    seen = set()
    cleaned = []
    for t in t_list:
        clean_name = t.get("name", "").strip().upper()
        if clean_name and clean_name not in seen and ("KUMAWAT" not in clean_name or clean_name == "RAJESH KUMAR KUMAWAT"):
            seen.add(clean_name)
            desig = t.get("desig", DESIGNATIONS[6])
            
            if clean_name in ["RAHUL KUMAR", "ASHUTOSH SHARMA", "LADU RAM", "SUNITA"]:
                desig = "प्रतिनियुक्ति पर कार्यरत अध्यापक (Deputation)"
            elif clean_name in ["RAJESH KUMAR KUMAWAT", "USHA KUMARI"]:
                desig = "पंचायत शिक्षक (Panchayat Shikshak)"
            elif clean_name == "DEEWAN SINGH MEENA":
                desig = "उप-प्रधानाचार्य (Vice Principal)"
            
            cleaned.append({
                "name": clean_name,
                "desig": desig,
                "subjects": t.get("subjects", [])
            })
    return cleaned

def get_data_for_mode(mode):
    target_file = MY_SCHOOL_FILE if mode.startswith("🏫") else UNIVERSAL_FILE
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "school_profile" in loaded:
                    loaded["teachers"] = clean_and_sanitize_teachers(loaded.get("teachers", []))
                    s6 = loaded.setdefault("schedules", {}).setdefault("6", {})
                    
                    # 11वीं कृषि के लिए फ़ाइल स्तर पर 6-कालांश संरचना को शुद्ध करना
                    s6["कक्षा 11 (Agriculture)"] = [
                        ["अनिवार्य हिन्दी", "JAYANTI SINGH"],
                        ["अनिवार्य अंग्रेजी", "RAHUL KUMAR"],
                        ["कृषि विज्ञान", "MUKESH YADAV"],
                        ["प्रायोगिक कार्य", "आवश्यकतानुसार (व्यवस्था)"],
                        ["कृषि रसायन", "ALOK KUMAR SINGH"],
                        ["कृषि जीव विज्ञान", "SUNITA"]
                    ]
                    
                    for c_name, p_list in s6.items():
                        for p in p_list:
                            if "प्रायोगिक" in p[0]:
                                p[0] = "प्रायोगिक कार्य"
                            if p[1] == "SUNITASU":
                                p[1] = "SUNITA"
                                
                    with open(target_file, "w", encoding="utf-8") as f_out:
                        json.dump(loaded, f_out, ensure_ascii=False, indent=2)
                        
                    return loaded
        except Exception:
            pass

    return {
        "school_profile": {
            "name": "राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी",
            "level": "उच्च माध्यमिक विद्यालय (कक्षा 1 से 12)",
            "state": "राजस्थान",
            "district": "जयपुर",
            "block": "सांभर लेक",
            "village": "रोजड़ी",
            "revenue_village": "रोजड़ी",
            "udise": "08121011201",
            "nic_code": "218823",
            "shift_type": "एकल पारी - ग्रीष्मकालीन (07:30 AM - 01:00 PM)",
            "periods_count": 6,
            "combine_primary": True
        },
        "teachers": STANDARD_TEACHERS,
        "schedules": {"6": {}, "8": {}}
    }

def save_active_data(data, mode, success_msg="डेटा सुरक्षित हो गया!"):
    target_file = MY_SCHOOL_FILE if mode.startswith("🏫") else UNIVERSAL_FILE
    try:
        data["teachers"] = clean_and_sanitize_teachers(data.get("teachers", []))
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        trigger_toast(success_msg, "✅")
        return True
    except Exception as e:
        trigger_toast(f"डेटा सेव नहीं हो सका: {str(e)}", "❌")
        return False

state_key = "data_myschool" if app_mode.startswith("🏫") else "data_universal"
if state_key not in st.session_state:
    st.session_state[state_key] = get_data_for_mode(app_mode)

app_data = st.session_state[state_key]
profile = app_data["school_profile"]

active_periods_count = profile.get("periods_count", 6)
periods_key = str(active_periods_count)

period_timings, prayer_time_str, recess_time_str = calculate_accurate_timings(profile["shift_type"], active_periods_count)

def get_active_classes(level, combine_primary):
    p_part = ["कक्षा 1 से 3 (संयुक्त)", "कक्षा 4-5 (संयुक्त)"] if combine_primary else ["कक्षा 1", "कक्षा 2", "कक्षा 3", "कक्षा 4", "कक्षा 5"]
    return p_part + [
        "कक्षा 6", "कक्षा 7", "कक्षा 8", "कक्षा 9", "कक्षा 10",
        "कक्षा 11 (Arts)", "कक्षा 11 (Science)", "कक्षा 11 (Agriculture)",
        "कक्षा 12 (Arts)", "कक्षा 12 (Science)", "कक्षा 12 (Agriculture)"
    ]

active_classes = get_active_classes(profile["level"], profile["combine_primary"])

sched = app_data.setdefault("schedules", {}).setdefault(periods_key, {})

# मेमोरी में भी 11वीं कृषि के 6 कालांशों को शुद्ध रखना
sched["कक्षा 11 (Agriculture)"] = [
    ["अनिवार्य हिन्दी", "JAYANTI SINGH"],
    ["अनिवार्य अंग्रेजी", "RAHUL KUMAR"],
    ["कृषि विज्ञान", "MUKESH YADAV"],
    ["प्रायोगिक कार्य", "आवश्यकतानुसार (व्यवस्था)"],
    ["कृषि रसायन", "ALOK KUMAR SINGH"],
    ["कृषि जीव विज्ञान", "SUNITA"]
]

for cls in active_classes:
    if cls not in sched:
        sched[cls] = [["--", "--"] for _ in range(active_periods_count)]

# -------------------------------------------------------------
# 6. हेडर कॉम्पोनेन्ट
# -------------------------------------------------------------
photo_paths = ["my_photo.jpg", "my_photo.png", "my_photo.jpeg", "developer.jpg", "developer.png"]
found_photo = None
for p in photo_paths:
    if os.path.exists(p):
        found_photo = p
        break

if found_photo:
    try:
        with open(found_photo, "rb") as img_f:
            b64_str = base64.b64encode(img_f.read()).decode("utf-8")
        avatar_img_tag = f'<img src="data:image/jpeg;base64,{b64_str}" style="width: 82px; height: 82px; border-radius: 50%; object-fit: cover; border: 3px solid #FFD700; z-index: 2; position: relative;">'
    except Exception:
        avatar_img_tag = '<div style="width: 82px; height: 82px; border-radius: 50%; background: #1e3a8a; display: flex; justify-content: center; align-items: center; color: #ffffff; font-size: 24px; font-weight: bold; border: 3px solid #FFD700; z-index: 2; position: relative;">AKS</div>'
else:
    avatar_img_tag = '<div style="width: 82px; height: 82px; border-radius: 50%; background: #1e3a8a; display: flex; justify-content: center; align-items: center; color: #ffffff; font-size: 24px; font-weight: bold; border: 3px solid #FFD700; z-index: 2; position: relative;">AKS</div>'

isolated_header_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @keyframes spinRays {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: transparent; }}
    .main-full-card {{ width: 100%; box-sizing: border-box; background: #ffffff; border-radius: 12px; padding: 12px 18px; border-top: 5px solid #FF9933; border-bottom: 5px solid #138808; border-left: 3px solid #0284c7; border-right: 3px solid #0284c7; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08); }}
    .flex-container {{ display: flex; justify-content: space-between; align-items: center; gap: 15px; }}
    .header-badge {{ background-color: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; padding: 3px 8px; border-radius: 5px; font-size: 11px; font-weight: 700; display: inline-block; margin: 2px 2px; }}
    .timing-strip {{ background: linear-gradient(90deg, #fff7ed 0%, #f0fdf4 100%); border: 1px dashed #ca8a04; border-radius: 7px; padding: 6px 10px; text-align: center; font-size: 12px; font-weight: bold; color: #854d0e; margin-top: 8px; box-sizing: border-box; }}
    .developer-ribbon {{ background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%); border: 2px solid #e2e8f0; border-radius: 9px; padding: 8px 12px; color: #f8fafc; min-width: 270px; }}
</style>
</head>
<body>
<div class="main-full-card">
    <div class="flex-container">
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 110px;">
            <div style="position: relative; width: 105px; height: 105px; display: flex; justify-content: center; align-items: center;">
                <div style="position: absolute; width: 102px; height: 102px; border-radius: 50%; background: repeating-conic-gradient(from 0deg, #FF9933 0deg 15deg, transparent 15deg 30deg, #FFD700 30deg 45deg, transparent 45deg 60deg); animation: spinRays 12s linear infinite; z-index: 1;"></div>
                {avatar_img_tag}
            </div>
            <span style="font-size: 9.5px; font-weight: bold; color: #b45309; background: #fef3c7; padding: 2px 6px; border-radius: 8px; border: 1px solid #fde68a; margin-top: 2px; z-index: 2;">☀️ मुख्य डेवलपर</span>
        </div>
        <div style="flex-grow: 1; text-align: center;">
            <h2 style="margin: 0; color: #1e3a8a; font-size: 22px; font-weight: 800;">🏫 {profile['name']}</h2>
            <div style="margin-top: 4px;">
                <span class="header-badge">🏛️ राजस्व ग्राम: {profile.get('revenue_village', profile.get('village', 'रोजड़ी'))}</span>
                <span class="header-badge">📍 ब्लॉक: {profile['block']}</span>
                <span class="header-badge">🗺️ जिला: {profile['district']} ({profile['state']})</span>
                <span class="header-badge" style="background-color: #fef3c7; color: #92400e; border-color: #fde68a;">🔢 U-DISE: {profile.get('udise', '08121011201')}</span>
                <span class="header-badge" style="background-color: #f3e8ff; color: #6b21a8; border-color: #e9d5ff;">🆔 NIC-SD: {profile.get('nic_code', '218823')}</span>
            </div>
        </div>
        <div class="developer-ribbon">
            <div style="font-size: 10px; font-weight: bold; color: #38bdf8;">💻 सॉफ़्टवेयर निर्माण एवं संकल्पना :</div>
            <div style="font-size: 13.5px; font-weight: 800; color: #ffffff;">आलोक कुमार सिंह (ALOK KUMAR SINGH)</div>
            <div style="font-size: 10.5px; color: #cbd5e1;">वरिष्ठ अध्यापक (Senior Teacher), रा.उ.मा.वि. रोजड़ी</div>
            <div style="font-size: 11px; color: #e2e8f0; margin-top: 2px;">📞 <b>+91-9414818991</b> &nbsp;|&nbsp; ✉️ <b>alokjobner@gmail.com</b></div>
        </div>
    </div>
    <div class="timing-strip">
        ⏰ सत्र: <b>{profile['shift_type']}</b> &nbsp;|&nbsp; 🙏 प्रार्थना: <b>{prayer_time_str}</b> &nbsp;|&nbsp; 🥪 मध्यांतर: <b>{recess_time_str}</b> &nbsp;|&nbsp; 📊 सक्रिय प्रारूप: <b>{active_periods_count} कालांश</b>
    </div>
</div>
</body>
</html>
"""

components.html(isolated_header_html, height=195)

# -------------------------------------------------------------
# 7. नेविगेशन मेन्यू
# -------------------------------------------------------------
TAB_OPTIONS = [
    "⚙️ विद्यालय विन्यास एवं समय",
    "👥 शिक्षक एवं विषय प्रोफ़ाइल",
    "📋 समय-सारणी एवं क्लैश निवारण",
    "🖨️ तिरंगा A4 प्रिंट पूर्वावलोकन"
]

def on_main_tab_change():
    st.session_state.active_main_tab = st.session_state.main_tab_selector

current_main_idx = TAB_OPTIONS.index(st.session_state.active_main_tab) if st.session_state.active_main_tab in TAB_OPTIONS else 0
selected_main = st.radio(
    "नेविगेशन मेन्यू:",
    TAB_OPTIONS,
    index=current_main_idx,
    horizontal=True,
    key="main_tab_selector",
    on_change=on_main_tab_change,
    label_visibility="collapsed"
)

st.markdown("---")

# -------------------------------------------------------------
# TAB 1: विद्यालय विन्यास
# -------------------------------------------------------------
if selected_main == "⚙️ विद्यालय विन्यास एवं समय":
    st.subheader("⚙️ विद्यालय विन्यास एवं समय")
    with st.form("school_setup_form"):
        col1, col2 = st.columns(2)
        with col1:
            s_name = st.text_input("विद्यालय का नाम:", value=profile.get("name", ""))
            s_level = st.selectbox("विद्यालय स्तर:", [
                "उच्च माध्यमिक विद्यालय (कक्षा 1 से 12)",
                "उच्च प्राथमिक विद्यालय (कक्षा 1 से 8)",
                "प्राथमिक विद्यालय (कक्षा 1 से 5)"
            ], index=0 if "12" in profile.get("level", "") else 1)
            
            shift_keys = list(SHIFT_CONFIGS.keys())
            curr_sh = profile.get("shift_type", shift_keys[0])
            s_shift = st.selectbox("शिविरा पंचांग पारी:", shift_keys, index=shift_keys.index(curr_sh) if curr_sh in shift_keys else 0)
            s_periods = st.selectbox("दैनिक कालांश प्रारूप:", [6, 8], index=0 if profile.get("periods_count", 6) == 6 else 1)
            s_udise = st.text_input("U-DISE कोड:", value=profile.get("udise", "08121011201"))
            s_nic = st.text_input("शाला दर्पण कोड:", value=profile.get("nic_code", "218823"))

        with col2:
            s_state = st.selectbox("राज्य:", ["राजस्थान"], index=0)
            all_districts = sorted(list(RAJASTHAN_GEO_DATA.keys()))
            s_district = st.selectbox("जिला:", all_districts, index=all_districts.index(profile.get("district", "जयपुर")))
            available_blocks = RAJASTHAN_GEO_DATA.get(s_district, ["सांभर लेक"])
            s_block = st.selectbox("ब्लॉक:", available_blocks, index=available_blocks.index(profile.get("block", "सांभर लेक")) if profile.get("block") in available_blocks else 0)
            s_village = st.text_input("ग्राम:", value=profile.get("village", "रोजड़ी"))
            s_rev_village = st.text_input("राजस्व ग्राम:", value=profile.get("revenue_village", "रोजड़ी"))
            s_combine = st.checkbox("प्राथमिक संयोजन (1-3 व 4-5 संयुक्त)", value=profile.get("combine_primary", True))

        if st.form_submit_button("विन्यास सुरक्षित करें", type="primary"):
            profile.update({
                "name": s_name.strip(), "level": s_level, "state": s_state,
                "district": s_district, "block": s_block.strip(),
                "village": s_village.strip(), "revenue_village": s_rev_village.strip(),
                "udise": s_udise.strip(), "nic_code": s_nic.strip(),
                "combine_primary": s_combine, "shift_type": s_shift, "periods_count": s_periods
            })
            save_active_data(app_data, app_mode, "विन्यास सुरक्षित हो गया!")
            st.rerun()

# -------------------------------------------------------------
# TAB 2: शिक्षक प्रबंधन
# -------------------------------------------------------------
elif selected_main == "👥 शिक्षक एवं विषय प्रोफ़ाइल":
    st.subheader("👥 शिक्षक सूची एवं पदनाम प्रबंधन")
    SUBTAB_OPTIONS = ["✏️ अध्यापक विवरण संशोधित करें", "➕ नया अध्यापक जोड़ें", "🗑️ अध्यापक हटाएं"]
    selected_subtab = st.radio("कार्य चुनें:", SUBTAB_OPTIONS, horizontal=True)

    if selected_subtab == "✏️ अध्यापक विवरण संशोधित करें":
        if app_data.get("teachers"):
            t_names = [t["name"] for t in app_data["teachers"]]
            sel_t = st.selectbox("अध्यापक चुनें:", t_names)
            target_t = next((t for t in app_data["teachers"] if t["name"] == sel_t), None)
            
            if target_t:
                with st.form("edit_t_form"):
                    col_e1, col_e2, col_e3 = st.columns([3, 3, 4])
                    with col_e1: up_name = st.text_input("नाम:", value=target_t.get("name", ""))
                    with col_e2:
                        c_des = target_t.get("desig", DESIGNATIONS[13])
                        up_des = st.selectbox("पदनाम:", DESIGNATIONS, index=DESIGNATIONS.index(c_des) if c_des in DESIGNATIONS else 13)
                    with col_e3:
                        c_subs = [s for s in target_t.get("subjects", []) if s in SUBJECT_DIRECTORY]
                        up_subs = st.multiselect("सक्षम विषय:", SUBJECT_DIRECTORY, default=c_subs)
                    
                    if st.form_submit_button("संशोधन सुरक्षित करें", type="primary"):
                        target_t["name"] = up_name.strip().upper()
                        target_t["desig"] = up_des
                        target_t["subjects"] = up_subs
                        save_active_data(app_data, app_mode, f"अध्यापक '{target_t['name']}' अद्यतन!")
                        st.rerun()

    elif selected_subtab == "➕ नया अध्यापक जोड़ें":
        with st.form("add_t_form"):
            col_a1, col_a2, col_a3 = st.columns([3, 3, 4])
            with col_a1: nt_name = st.text_input("नाम:")
            with col_a2: nt_desig = st.selectbox("पदनाम:", DESIGNATIONS, index=13)
            with col_a3: nt_subs = st.multiselect("विषय:", SUBJECT_DIRECTORY)
            if st.form_submit_button("अध्यापक जोड़ें", type="primary"):
                name_clean = nt_name.strip().upper()
                if name_clean:
                    app_data["teachers"].append({"name": name_clean, "desig": nt_desig, "subjects": nt_subs})
                    save_active_data(app_data, app_mode, f"अध्यापक '{name_clean}' जोड़ दिया गया!")
                    st.rerun()

    elif selected_subtab == "🗑️ अध्यापक हटाएं":
        if app_data.get("teachers"):
            del_target = st.selectbox("हटाने हेतु चुनें:", [t["name"] for t in app_data["teachers"]])
            if st.button("चयनित अध्यापक हटाएं", type="secondary"):
                app_data["teachers"] = [t for t in app_data["teachers"] if t["name"] != del_target]
                save_active_data(app_data, app_mode, f"अध्यापक हटाया गया!")
                st.rerun()

    st.markdown("---")
    if app_data.get("teachers"):
        t_table = [{"क्रमांक": i+1, "नाम": t["name"], "पदनाम": t["desig"], "सक्षम विषय": ", ".join(t.get("subjects", []))} for i, t in enumerate(app_data["teachers"])]
        st.table(t_table)

# -------------------------------------------------------------
# TAB 3: समय-सारणी संपादन
# -------------------------------------------------------------
elif selected_main == "📋 समय-सारणी एवं क्लैश निवारण":
    def analyze_clashes(current_sched, period_limit):
        clashes = []
        exempt = ["-- (रिक्त / कोई नहीं)", "आवश्यकतानुसार (व्यवस्था)", "--", ""]
        for p in range(period_limit):
            alloc = {}
            for cls_name in active_classes:
                if cls_name not in current_sched or len(current_sched[cls_name]) <= p:
                    continue
                sub, teacher = current_sched[cls_name][p]
                if teacher in exempt:
                    continue
                if ("अनिवार्य हिन्दी" in sub or "अनिवार्य अंग्रेजी" in sub) and ("11" in cls_name or "12" in cls_name):
                    grp = f"{'11' if '11' in cls_name else '12'}_COMBINED"
                    alloc.setdefault(teacher, []).append((cls_name, sub, grp))
                else:
                    alloc.setdefault(teacher, []).append((cls_name, sub, cls_name))
            for teacher, entries in alloc.items():
                rooms = set(e[2] for e in entries)
                if len(rooms) > 1:
                    clashes.append({
                        "period": p + 1,
                        "teacher": teacher,
                        "classes": [f"{e[0]} ({e[1]})" for e in entries]
                    })
        return clashes

    st.subheader(f"📋 समय-सारणी संपादन ({profile['shift_type']})")
    live_clashes = analyze_clashes(sched, active_periods_count)

    if live_clashes:
        st.error(f"🚨 कुल {len(live_clashes)} कालांशों में शिक्षक टकराव (Clash) दर्ज है!")
        for idx, cl in enumerate(live_clashes):
            st.warning(f"**चेतावनी #{idx+1} [कालांश {cl['period']} - {period_timings[cl['period']-1]}]:** {cl['teacher']} 👉 {', '.join(cl['classes'])}")
    else:
        st.success("✅ **शून्य टकराव (Zero Clash):** 11वीं एवं 12वीं के सभी संकाय पूर्णतः संतुलित एवं क्लैश-मुक्त हैं।")

    c1, c2 = st.columns(2)
    periods_range = list(range(1, active_periods_count + 1))
    
    with c1:
        st.markdown("##### 👨‍🏫 अध्यापक / विषय बदलें")
        if active_classes and sched:
            ec = st.selectbox("कक्षा:", active_classes, key="tb_ec")
            ep = st.selectbox("कालांश:", periods_range, format_func=lambda x: f"कालांश {x} ({period_timings[x-1]})", key="tb_ep")
            curr_s, curr_t = sched.get(ec, [["--", "--"]]*active_periods_count)[ep - 1]

            t_opts = ["-- (रिक्त / कोई नहीं)", "आवश्यकतानुसार (व्यवस्था)"] + [t["name"] for t in app_data["teachers"]]
            t_idx = t_opts.index(curr_t) if curr_t in t_opts else 0
            new_t = st.selectbox("नया अध्यापक:", t_opts, index=t_idx, key="tb_nt")
            new_s = st.selectbox("विषय:", SUBJECT_DIRECTORY, index=SUBJECT_DIRECTORY.index(curr_s) if curr_s in SUBJECT_DIRECTORY else 0, key="tb_ns")

            if st.button("बदलाव सेव करें", type="primary", use_container_width=True):
                sched[ec][ep - 1] = [new_s, new_t]
                save_active_data(app_data, app_mode, f"{ec} कालांश {ep} में '{new_s} ({new_t})' अपडेट!")
                st.rerun()

    with c2:
        st.markdown("##### 🔄 कालांश आपस में स्वैप करें")
        if active_classes and sched:
            sc = st.selectbox("कक्षा (स्वैप):", active_classes, key="tb_sc")
            sp1 = st.selectbox("पहला कालांश:", periods_range, format_func=lambda x: f"कालांश {x} ({period_timings[x-1]})", key="tb_sp1")
            sp2 = st.selectbox("दूसरा कालांश:", periods_range, format_func=lambda x: f"कालांश {x} ({period_timings[x-1]})", index=1, key="tb_sp2")
            if st.button("कालांश स्वैप करें", use_container_width=True):
                i1, i2 = sp1 - 1, sp2 - 1
                sched[sc][i1], sched[sc][i2] = sched[sc][i2], sched[sc][i1]
                save_active_data(app_data, app_mode, f"{sc} में कालांश बदले गए!")
                st.rerun()

# -------------------------------------------------------------
# TAB 4: तिरंगा A4 प्रिंट (संरेखण लॉक)
# -------------------------------------------------------------
elif selected_main == "🖨️ तिरंगा A4 प्रिंट पूर्वावलोकन":
    st.subheader("🖨️ शासकीय तिरंगा A4 प्रिंटिंग केंद्र (Single-Page Strict Lock)")

    col_p_type, col_p_btn = st.columns([7, 3])
    with col_p_type:
        print_target = st.radio(
            "प्रिंट प्रारूप:",
            [
                "📄 केवल कक्षा-वार समय-सारणी (Class-wise Timetable)",
                "👨‍🏫 केवल अध्यापक-वार समय-सारणी (Teacher-wise Timetable)",
                "📑 दोनों समय-सारणियाँ (2-पृष्ठ संयुक्त प्रिंट)"
            ],
            horizontal=True
        )

    current_date = datetime.now().strftime("%d/%m/%Y")

    def render_cell(sub, tchr, is_ct=False):
        ct = "<br><span class='ct-badge'>कक्षा अध्यापक</span>" if is_ct else ""
        if tchr in ["-- (रिक्त / कोई नहीं)", "--"]:
            t_str = "<span class='dash-tchr'>--</span>"
        elif tchr == "आवश्यकतानुसार (व्यवस्था)":
            t_str = "<span class='arr-tchr'>आवश्यकतानुसार</span>"
        else:
            t_str = f"<span class='tchr-name'>({tchr})</span>"
        return f"<td><span class='sub-name'>{sub}</span>{t_str}{ct}</td>"

    col_width = f"{85.0 / active_periods_count:.2f}%"
    thead_cols_html = f'<th style="width: 15%;">कक्षा / संयुक्त वर्ग</th>'
    for idx, t_str in enumerate(period_timings):
        ct_lbl = "<br><small style='color:#1e40af;'>(कक्षा अध्यापक)</small>" if idx == 0 else ""
        thead_cols_html += f'<th style="width: {col_width};">कालांश {idx + 1}{ct_lbl}<br><span class="time-header">[{t_str}]</span></th>'

    rows_class_html = ""
    normal_classes = [c for c in active_classes if not ("11" in c or "12" in c)]
    for c in normal_classes:
        if c in sched:
            rows_class_html += f"<tr><td class='cls-header'>{c}</td>"
            for idx in range(active_periods_count):
                sub, tchr = sched[c][idx] if idx < len(sched[c]) else ("--", "--")
                rows_class_html += render_cell(sub, tchr, is_ct=(idx == 0))
            rows_class_html += "</tr>"

    # कक्षा 11 (Arts, Science, Agriculture) का अलाइनमेंट
    if "कक्षा 11 (Arts)" in active_classes and "कक्षा 11 (Arts)" in sched:
        c11_a = sched["कक्षा 11 (Arts)"]
        c11_s = sched.get("कक्षा 11 (Science)", c11_a)
        
        # 11वीं कृषि के लिए कालांश 3 से 6 की सही मैपिंग
        c11_g_periods = [
            ["कृषि विज्ञान", "MUKESH YADAV"],
            ["प्रायोगिक कार्य", "आवश्यकतानुसार (व्यवस्था)"],
            ["कृषि रसायन", "ALOK KUMAR SINGH"],
            ["कृषि जीव विज्ञान", "SUNITA"]
        ]
        
        tds_11_a = "".join([render_cell(c11_a[p][0], c11_a[p][1]) for p in range(2, active_periods_count)])
        tds_11_s = "".join([render_cell(c11_s[p][0], c11_s[p][1]) for p in range(2, active_periods_count)])
        tds_11_g = "".join([render_cell(p[0], p[1]) for p in c11_g_periods])
        
        rows_class_html += f"""
        <tr>
            <td class='cls-header'>कक्षा 11 (Arts)</td>
            <td rowspan="3" class="merged-box">
                <span class="sub-name">{c11_a[0][0]}</span><span class="tchr-name">({c11_a[0][1]})</span>
                <span class="merged-lbl">[तीनों संकाय संयुक्त]</span>
                <span class='ct-badge'>कक्षा अध्यापक</span>
            </td>
            <td rowspan="3" class="merged-box">
                <span class="sub-name">{c11_a[1][0]}</span><span class="tchr-name">({c11_a[1][1]})</span>
                <span class="merged-lbl">[तीनों संकाय संयुक्त]</span>
            </td>
            {tds_11_a}
        </tr>
        <tr>
            <td class='cls-header'>कक्षा 11 (Science)</td>
            {tds_11_s}
        </tr>
        <tr>
            <td class='cls-header'>कक्षा 11 (Agriculture)</td>
            {tds_11_g}
        </tr>
        """

    # कक्षा 12 (Arts, Science, Agriculture) का अलाइनमेंट
    if "कक्षा 12 (Arts)" in active_classes and "कक्षा 12 (Arts)" in sched:
        c12_a = sched["कक्षा 12 (Arts)"]
        c12_s = sched.get("कक्षा 12 (Science)", c12_a)
        c12_g = sched.get("कक्षा 12 (Agriculture)", c12_a)
        
        tds_12_a = "".join([render_cell(c12_a[p][0], c12_a[p][1]) for p in range(2, active_periods_count)])
        tds_12_s = "".join([render_cell(c12_s[p][0], c12_s[p][1]) for p in range(2, active_periods_count)])
        tds_12_g = "".join([render_cell(c12_g[p][0], c12_g[p][1]) for p in range(2, active_periods_count)])
        
        rows_class_html += f"""
        <tr>
            <td class='cls-header'>कक्षा 12 (Arts)</td>
            <td rowspan="3" class="merged-box">
                <span class="sub-name">{c12_a[0][0]}</span><span class="tchr-name">({c12_a[0][1]})</span>
                <span class="merged-lbl">[तीनों संकाय संयुक्त]</span>
                <span class='ct-badge'>कक्षा अध्यापक</span>
            </td>
            <td rowspan="3" class="merged-box">
                <span class="sub-name">{c12_a[1][0]}</span><span class="tchr-name">({c12_a[1][1]})</span>
                <span class="merged-lbl">[तीनों संकाय संयुक्त]</span>
            </td>
            {tds_12_a}
        </tr>
        <tr>
            <td class='cls-header'>कक्षा 12 (Science)</td>
            {tds_12_s}
        </tr>
        <tr>
            <td class='cls-header'>कक्षा 12 (Agriculture)</td>
            {tds_12_g}
        </tr>
        """

    t_col_width = f"{76.0 / active_periods_count:.2f}%"
    t_thead_cols_html = f'<th style="width: 16%;">अध्यापक का नाम एवं पद</th>'
    for idx, t_str in enumerate(period_timings):
        t_thead_cols_html += f'<th style="width: {t_col_width};">कालांश {idx + 1}<br><span class="time-header">[{t_str}]</span></th>'
    t_thead_cols_html += f'<th style="width: 8%;">कुल भार</th>'

    rows_teacher_html = ""
    registered_teachers = app_data.get("teachers", [])

    for t_obj in registered_teachers:
        t_name = t_obj["name"]
        t_desig = t_obj.get("desig", "")
        t_periods = []
        total_load = 0

        for p_idx in range(active_periods_count):
            all_classes_in_p = []
            for cls_name in active_classes:
                if cls_name in sched and p_idx < len(sched[cls_name]):
                    sub, tch = sched[cls_name][p_idx]
                    if tch == t_name:
                        short_c = cls_name.replace("कक्षा ", "").replace(" (संयुक्त)", "")
                        all_classes_in_p.append(f"{short_c} ({sub})")

            if all_classes_in_p:
                if any("11" in c for c in all_classes_in_p) and any("अनिवार्य" in c for c in all_classes_in_p):
                    display_text = f"<span class='sub-name'>कक्षा 11 संयुक्त</span><span class='tchr-name'>{all_classes_in_p[0].split('(')[-1].replace(')', '')}</span>"
                elif any("12" in c for c in all_classes_in_p) and any("अनिवार्य" in c for c in all_classes_in_p):
                    display_text = f"<span class='sub-name'>कक्षा 12 संयुक्त</span><span class='tchr-name'>{all_classes_in_p[0].split('(')[-1].replace(')', '')}</span>"
                else:
                    display_text = "<br>".join([f"<span class='sub-name'>{item}</span>" for item in all_classes_in_p])
                t_periods.append(f"<td>{display_text}</td>")
                total_load += 1
            else:
                t_periods.append("<td><span class='dash-tchr'>-- (रिक्त)</span></td>")

        periods_td_str = "".join(t_periods)
        rows_teacher_html += f"""
        <tr>
            <td class='cls-header'>
                <span class='sub-name'>{t_name}</span>
                <small style='color:#475569; font-size: 7.2px;'>{t_desig}</small>
            </td>
            {periods_td_str}
            <td style='font-weight: bold; color: #1e3a8a; font-size: 10px;'>{total_load}</td>
        </tr>
        """

    developer_print_footer = """
    <div class="developer-footer">
        <div><b>सॉफ्टवेयर विकास एवं संकल्पना:</b> आलोक कुमार सिंह (ALOK KUMAR SINGH), वरिष्ठ अध्यापक, रा.उ.मा.वि. रोजड़ी (जयपुर)</div>
        <div>📞 <b>9414818991</b> &nbsp;|&nbsp; ✉️ <b>alokjobner@gmail.com</b></div>
    </div>
    """

    page_class_html = f"""
    <div class="outer-page-border">
        <div class="inner-page-border">
            <div class="header-box">
                <h2>{profile['name']}</h2>
                <p>
                    राजस्व ग्राम: <b>{profile.get('revenue_village', profile.get('village', 'रोजड़ी'))}</b> | ब्लॉक: <b>{profile['block']}</b> | जिला: <b>{profile['district']}</b> | 
                    <b>U-DISE:</b> {profile.get('udise', '08121011201')} | <b>NIC-SD:</b> {profile.get('nic_code', '218823')}<br>
                    <b>सत्र:</b> {profile['shift_type']} | <b>प्रार्थना:</b> {prayer_time_str} | <b>मध्यांतर:</b> {recess_time_str} | <b>कक्षा-वार समय-सारणी</b>
                </p>
            </div>
            <table class="tt-table class-table">
                <thead>
                    <tr>{thead_cols_html}</tr>
                </thead>
                <tbody>{rows_class_html}</tbody>
            </table>
            <div class="footer-bar">
                <div>दिनांक: {current_date}<br>क्रमांक: राउमावि/समय-सारणी/कक्षा/2026-27/</div>
                <div style="text-align: right;">हस्ताक्षर संस्था प्रधान / प्रधानाचार्य<br>(मय सील / मोहर)</div>
            </div>
            {developer_print_footer}
        </div>
    </div>
    """

    page_teacher_html = f"""
    <div class="outer-page-border" style="page-break-before: always;">
        <div class="inner-page-border">
            <div class="header-box">
                <h2>{profile['name']}</h2>
                <p>
                    राजस्व ग्राम: <b>{profile.get('revenue_village', profile.get('village', 'रोजड़ी'))}</b> | ब्लॉक: <b>{profile['block']}</b> | जिला: <b>{profile['district']}</b> | 
                    <b>U-DISE:</b> {profile.get('udise', '08121011201')} | <b>NIC-SD:</b> {profile.get('nic_code', '218823')}<br>
                    <b>सत्र:</b> {profile['shift_type']} | <b>प्रार्थना:</b> {prayer_time_str} | <b>मध्यांतर:</b> {recess_time_str} | <b>अध्यापक-वार समय-सारणी</b>
                </p>
            </div>
            <table class="tt-table teacher-table">
                <thead>
                    <tr>{t_thead_cols_html}</tr>
                </thead>
                <tbody>{rows_teacher_html}</tbody>
            </table>
            <div class="footer-bar">
                <div>दिनांक: {current_date}<br>क्रमांक: राउमावि/समय-सारणी/अध्यापक/2026-27/</div>
                <div style="text-align: right;">हस्ताक्षर संस्था प्रधान / प्रधानाचार्य<br>(मय सील / मोहर)</div>
            </div>
            {developer_print_footer}
        </div>
    </div>
    """

    if "केवल कक्षा-वार" in print_target:
        active_print_body = page_class_html
    elif "केवल अध्यापक-वार" in print_target:
        active_print_body = page_teacher_html.replace('style="page-break-before: always;"', '')
    else:
        active_print_body = page_class_html + page_teacher_html

    full_printable_document = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>{profile['name']} - समय सारणी</title>
    <style>
    @page {{
        size: A4 landscape;
        margin: 5mm;
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #ffffff; }}
    .outer-page-border {{
        border: 3.5px solid #138808;
        padding: 2.5px;
        background-color: #ffffff;
        box-sizing: border-box;
        max-height: 190mm;
        height: 190mm;
        display: flex;
        flex-direction: column;
        page-break-inside: avoid;
    }}
    .inner-page-border {{
        border: 3.5px solid #FF9933;
        padding: 4px 6px 3px 6px;
        background-color: #ffffff;
        box-sizing: border-box;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .header-box {{ text-align: center; margin-bottom: 2px; }}
    .header-box h2 {{ margin: 0; font-size: 16px; font-weight: 800; color: #1e3a8a; }}
    .header-box p {{ margin: 1px 0 0 0; font-size: 9px; color: #334155; font-weight: bold; line-height: 1.2; }}
    .tt-table {{ width: 100%; border-collapse: collapse; border: 1.5px solid #000; text-align: center; table-layout: fixed; }}
    .class-table {{ font-size: 9px; }}
    .class-table th, .class-table td {{ border: 1px solid #000; padding: 2px 1px; vertical-align: middle; line-height: 1.15; }}
    .teacher-table {{ font-size: 8px; }}
    .teacher-table th, .teacher-table td {{ border: 1px solid #000; padding: 1.1px 0.5px; vertical-align: middle; line-height: 1.08; }}
    .tt-table th {{ background-color: #f1f5f9; font-weight: bold; font-size: 9px; border-bottom: 1.5px solid #000; }}
    .time-header {{ font-size: 7.2px; color: #475569; font-weight: bold; display: block; }}
    .cls-header {{ background-color: #f8fafc; font-weight: bold; text-align: left; padding-left: 3px !important; font-size: 8.5px; }}
    .sub-name {{ font-weight: bold; color: #000; display: block; font-size: 9px; }}
    .tchr-name {{ font-size: 7.8px; color: #1e3a8a; font-weight: 600; display: block; }}
    .dash-tchr {{ font-size: 8px; font-weight: normal; color: #64748b; display: block; }}
    .arr-tchr {{ font-size: 7.2px; color: #b45309; font-weight: bold; display: block; }}
    .ct-badge {{ background-color: #e0e7ff; color: #3730a3; font-size: 6.8px; padding: 0.5px 2px; border-radius: 2px; display: inline-block; border: 0.5px solid #a5b4fc; font-weight: bold; }}
    .merged-box {{ background-color: #f0fdf4 !important; border: 1.5px solid #166534 !important; }}
    .merged-lbl {{ font-size: 6.8px; color: #15803d; font-weight: bold; display: block; }}
    .footer-bar {{ width: 100%; margin-top: 2px; display: flex; justify-content: space-between; font-size: 8px; font-weight: bold; }}
    .developer-footer {{ margin-top: 2px; padding: 1.5px 3px; border-top: 1px dashed #cbd5e1; display: flex; justify-content: space-between; align-items: center; font-size: 7.5px; color: #334155; }}
    </style>
    </head>
    <body>
        {active_print_body}
    </body>
    </html>
    """

    with col_p_btn:
        print_action_js = f"""
        <script>
        function doTricolorPrint() {{
            var docContent = `{full_printable_document}`;
            var pWin = window.open('', '_blank', 'width=1150,height=750');
            pWin.document.open();
            pWin.document.write(docContent);
            pWin.document.close();
            pWin.focus();
            setTimeout(function() {{ pWin.print(); pWin.close(); }}, 400);
        }}
        </script>
        <button onclick="doTricolorPrint()" style="width: 100%; background: linear-gradient(90deg, #FF9933 0%, #ffffff 50%, #138808 100%); color: #000; border: 2px solid #000; padding: 9px 12px; font-size: 13.5px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-top: 10px;">🖨️ चयनित प्रारूप प्रिंट करें</button>
        """
        components.html(print_action_js, height=55)

    components.html(full_printable_document, height=650, scrolling=True)
