import os
import io
import base64
import hashlib
from datetime import datetime

import streamlit as st
from PIL import Image, ImageChops, ImageEnhance
from openai import OpenAI


# =========================================================
# إعدادات
# =========================================================

st.set_page_config(
    page_title="VerifyAI Terminal",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

# حماية بسيطة من استهلاك الرصيد بشكل كبير داخل جلسة واحدة
MAX_AI_CALLS_PER_SESSION = 15


# =========================================================
# OpenAI
# =========================================================

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = None

client = OpenAI(api_key=api_key) if api_key else None


# =========================================================
# Session State
# =========================================================

defaults = {
    "page": "الرئيسية",
    "messages": [],
    "uploaded_image_bytes": None,
    "uploaded_image_mime": None,
    "uploaded_filename": None,
    "analysis_result": None,
    "ela_bytes": None,
    "sha256": None,
    "ai_calls": 0,
    "files_analyzed": 0,
    "show_evidence": False,
    "operation_log": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    /* ---------- الصفحة ---------- */

    .stApp {
        background:
            radial-gradient(circle at 70% 10%, rgba(30, 80, 130, 0.12), transparent 30%),
            #070b12;
        color: #eef3f8;
    }

    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* ---------- العناوين ---------- */

    .main-title {
        font-size: 27px;
        font-weight: 800;
        letter-spacing: .2px;
        margin-bottom: 2px;
    }

    .sub-title {
        color: #7f8b9b;
        font-size: 13px;
        margin-bottom: 20px;
    }

    .section-title {
        font-size: 18px;
        font-weight: 750;
        margin-bottom: 8px;
    }

    .muted {
        color: #7f8b9b;
        font-size: 13px;
    }

    /* ---------- الكروت ---------- */

    .card {
        background: rgba(13, 19, 29, .88);
        border: 1px solid #1c2735;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,.15);
    }

    .upload-card {
        min-height: 330px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .assistant-card {
        min-height: 330px;
    }

    /* ---------- شعار ---------- */

    .brand-logo {
        width: 46px;
        height: 46px;
        border-radius: 50%;
        border: 1px solid #314152;
        background: #101824;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        margin-bottom: 10px;
    }

    /* ---------- Sidebar ---------- */

    section[data-testid="stSidebar"] {
        background: #090e16;
        border-right: 1px solid #182230;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.3rem;
    }

    .side-brand {
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 2px;
    }

    .side-sub {
        color: #697789;
        font-size: 11px;
        margin-bottom: 25px;
    }

    /* ---------- أزرار ---------- */

    .stButton > button {
        border-radius: 10px;
        border: 1px solid #253243;
        background: #0d141e;
        color: #dbe4ed;
        min-height: 42px;
        transition: .15s;
    }

    .stButton > button:hover {
        border-color: #42617f;
        background: #121c28;
    }

    /* ---------- رفع الملفات ---------- */

    [data-testid="stFileUploader"] {
        background: #0b111a;
        border: 1px dashed #34465b;
        border-radius: 13px;
        padding: 8px;
    }

    /* ---------- Chat ---------- */

    [data-testid="stChatMessage"] {
        background: #0c131d;
        border: 1px solid #1b2836;
        border-radius: 12px;
        margin-bottom: 8px;
    }

    [data-testid="stChatInput"] {
        margin-top: 8px;
    }

    /* ---------- Metrics ---------- */

    .metric-box {
        background: #0d141e;
        border: 1px solid #1c2735;
        border-radius: 13px;
        padding: 15px;
        text-align: center;
    }

    .metric-number {
        font-size: 23px;
        font-weight: 800;
    }

    .metric-label {
        color: #718095;
        font-size: 11px;
        margin-top: 3px;
    }

    /* ---------- Status ---------- */

    .status {
        display: inline-block;
        padding: 5px 9px;
        border-radius: 20px;
        background: #0d1c18;
        border: 1px solid #214337;
        color: #69d5ad;
        font-size: 11px;
    }

    .warning {
        display: inline-block;
        padding: 5px 9px;
        border-radius: 20px;
        background: #21190d;
        border: 1px solid #4c391c;
        color: #dcb36a;
        font-size: 11px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# وظائف الصور
# =========================================================

def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_ela(image_bytes: bytes, quality: int = 90):
    """
    Error Level Analysis.
    مهم: ELA مؤشر مساعد فقط وليس إثباتاً قاطعاً للتلاعب.
    """

    original = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    buffer = io.BytesIO()
    original.save(buffer, "JPEG", quality=quality)

    recompressed = Image.open(io.BytesIO(buffer.getvalue())).convert("RGB")

    diff = ImageChops.difference(original, recompressed)

    extrema = diff.getextrema()

    max_diff = max(
        channel_max
        for channel_min, channel_max in extrema
    )

    if max_diff == 0:
        max_diff = 1

    scale = 255 / max_diff

    ela = ImageEnhance.Brightness(diff).enhance(scale)

    output = io.BytesIO()
    ela.save(output, "PNG")

    return output.getvalue()


def prepare_image_for_ai(image_bytes: bytes):
    """
    تصغير الصورة قبل إرسالها للـAI لتقليل وقت الإرسال والتكلفة.
    الصورة الأصلية تبقى محفوظة للعرض.
    """

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    max_size = 1600
    image.thumbnail((max_size, max_size))

    output = io.BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=85,
        optimize=True
    )

    return output.getvalue(), "image/jpeg"


def image_to_data_url(image_bytes: bytes, mime: str):
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


# =========================================================
# AI
# =========================================================

FORENSIC_INSTRUCTIONS = """
أنت مساعد ذكاء اصطناعي للتحليل الجنائي الرقمي.

مهمتك تحليل الصور التي يرفعها المستخدم بطريقة واضحة ومختصرة.

عند تحليل صورة:
1. صف ما يظهر في الصورة.
2. اذكر أي مؤشرات بصرية قد تكون مهمة للتحقق من الصورة.
3. إذا لاحظت مناطق تبدو مختلفة في الضغط أو الإضاءة أو الحواف، اذكرها كمؤشرات فقط.
4. لا تقل إن الصورة مزورة بشكل قطعي اعتماداً على الصورة وحدها.
5. لا تعتبر ELA دليلاً قاطعاً؛ هو مؤشر مساعد فقط.
6. إذا لم توجد أدلة واضحة، قل ذلك بوضوح.
7. لا تخترع معلومات غير موجودة في الصورة.
8. إذا كانت الصورة تحتوي على شخص، لا تحاول تحديد هوية الشخص.
9. اجعل الإجابة منظمة وسهلة القراءة باللغة العربية.
"""


def analyze_image_with_ai(question: str):
    if client is None:
        return (
            "⚠️ مفتاح OpenAI غير موجود.\n\n"
            "ضع OPENAI_API_KEY في متغيرات البيئة أو Streamlit Secrets."
        )

    if st.session_state.uploaded_image_bytes is None:
        return "لم يتم رفع أي صورة حتى الآن."

    if st.session_state.ai_calls >= MAX_AI_CALLS_PER_SESSION:
        return (
            "تم الوصول إلى الحد المسموح لطلبات الذكاء الاصطناعي "
            "في هذه الجلسة."
        )

    original_bytes = st.session_state.uploaded_image_bytes

    ai_bytes, ai_mime = prepare_image_for_ai(original_bytes)

    data_url = image_to_data_url(ai_bytes, ai_mime)

    try:
        response = client.responses.create(
            model=MODEL,
            instructions=FORENSIC_INSTRUCTIONS,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": question,
                        },
                        {
                            "type": "input_image",
                            "image_url": data_url,
                        },
                    ],
                }
            ],
        )

        result = response.output_text.strip()

        st.session_state.ai_calls += 1
        st.session_state.analysis_result = result
        st.session_state.files_analyzed += 1

        st.session_state.operation_log.append(
            {
                "time": datetime.now().strftime("%H:%M:%S"),
                "operation": "تحليل صورة بالذكاء الاصطناعي",
                "file": st.session_state.uploaded_filename,
            }
        )

        return result

    except Exception as e:
        return (
            "حدث خطأ أثناء الاتصال بالذكاء الاصطناعي.\n\n"
            f"التفاصيل: {str(e)}"
        )


# =========================================================
# رفع صورة
# =========================================================

def handle_upload(uploaded_file):

    if uploaded_file is None:
        return

    data = uploaded_file.getvalue()

    st.session_state.uploaded_image_bytes = data
    st.session_state.uploaded_image_mime = uploaded_file.type
    st.session_state.uploaded_filename = uploaded_file.name

    st.session_state.sha256 = calculate_sha256(data)

    try:
        st.session_state.ela_bytes = create_ela(data)
    except Exception:
        st.session_state.ela_bytes = None

    st.session_state.analysis_result = None
    st.session_state.show_evidence = False

    st.session_state.operation_log.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "operation": "رفع صورة",
            "file": uploaded_file.name,
        }
    )


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div class="brand-logo">⌕</div>
        <div class="side-brand">VerifyAI Terminal</div>
        <div class="side-sub">
            المنصة الوطنية للاستخبارات الجنائية الرقمية
        </div>
        """,
        unsafe_allow_html=True,
    )

    pages = [
        ("⌂", "الرئيسية"),
        ("◉", "تحليل المستندات"),
        ("✦", "المحادثة الذكية"),
        ("▤", "التقارير"),
        ("◌", "التحقق من الهوية"),
        ("◇", "التشفير والأمان"),
        ("◷", "سجل العمليات"),
        ("⚙", "الإعدادات"),
    ]

    for icon, name in pages:

        if st.button(
            f"{icon}   {name}",
            key=f"nav_{name}",
            use_container_width=True,
        ):
            st.session_state.page = name
            st.rerun()

    st.markdown("---")

    if client:
        st.markdown(
            '<span class="status">● AI متصل</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="warning">● API غير متصل</span>',
            unsafe_allow_html=True,
        )


# =========================================================
# Header
# =========================================================

st.markdown(
    """
    <div class="main-title">
        VerifyAI Terminal
    </div>
    <div class="sub-title">
        المنصة الوطنية للاستخبارات الجنائية الرقمية
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# الصفحة الرئيسية
# =========================================================

if st.session_state.page == "الرئيسية":

    left, right = st.columns([1.55, 1], gap="large")

    with left:

        st.markdown(
            '<div class="section-title">تحليل الأدلة الرقمية</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="muted">
            ارفع صورة للتحليل الجنائي الرقمي بواسطة الذكاء الاصطناعي.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        uploaded_file = st.file_uploader(
            "ارفع الصورة هنا",
            type=["png", "jpg", "jpeg", "webp"],
            key="main_uploader",
            label_visibility="visible",
        )

        if uploaded_file is not None:
            handle_upload(uploaded_file)

        if st.session_state.uploaded_image_bytes:

            st.markdown("### الصورة المرفوعة")

            st.image(
                st.session_state.uploaded_image_bytes,
                use_container_width=True,
            )

            st.caption(
                f"الملف: {st.session_state.uploaded_filename}"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "🔎 تحليل الصورة بالـAI",
                    use_container_width=True,
                ):

                    with st.spinner("جاري تحليل الصورة..."):
                        result = analyze_image_with_ai(
                            """
                            حلل الصورة المرفوعة تحليلاً جنائياً رقمياً.
                            أعطني:
                            - وصفاً لما يظهر.
                            - المؤشرات البصرية المهمة.
                            - المناطق التي تستحق الفحص.
                            - خلاصة واضحة مع درجة اليقين المناسبة.
                            """
                        )

                    st.rerun()

            with col2:
                if st.button(
                    "🧾 وريني الدليل",
                    use_container_width=True,
                ):
                    st.session_state.show_evidence = True
                    st.rerun()

            if st.session_state.analysis_result:

                st.markdown("### نتيجة تحليل الـAI")

                st.markdown(
                    f"""
                    <div class="card">
                    {st.session_state.analysis_result.replace(chr(10), "<br>")}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.session_state.show_evidence:

                st.markdown("### الدليل المرئي")

                st.image(
                    st.session_state.uploaded_image_bytes,
                    caption="الصورة الأصلية المرفوعة",
                    use_container_width=True,
                )

                if st.session_state.ela_bytes:

                    st.markdown("### ELA")

                    st.image(
                        st.session_state.ela_bytes,
                        caption=(
                            "تحليل ELA — مؤشر مساعد فقط "
                            "وليس إثباتاً قاطعاً للتلاعب"
                        ),
                        use_container_width=True,
                    )

        else:

            st.info(
                "ارفع صورة أولاً حتى تستطيع المنصة تحليلها."
            )

    # -----------------------------------------------------

    with right:

        st.markdown(
            '<div class="section-title">المساعد الجنائي الذكي</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="muted">اسأل عن الصورة المرفوعة أو اطلب تحليلها.</div>',
            unsafe_allow_html=True,
        )

        if not st.session_state.messages:

            st.markdown(
                """
                <div class="card">
                    <b>جاهز للتحليل</b>
                    <br><br>
                    ارفع صورة ثم اكتب طلبك هنا.
                    <br><br>
                    أمثلة:
                    <br>
                    • حلل الصورة
                    <br>
                    • ما الأشياء المشبوهة؟
                    <br>
                    • وريني الدليل
                </div>
                """,
                unsafe_allow_html=True,
            )

        for message in st.session_state.messages:

            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                if (
                    message.get("show_evidence")
                    and st.session_state.uploaded_image_bytes
                ):
                    st.image(
                        st.session_state.uploaded_image_bytes,
                        caption="الدليل — الصورة المرفوعة",
                        use_container_width=True,
                    )

                    if st.session_state.ela_bytes:
                        st.image(
                            st.session_state.ela_bytes,
                            caption="ELA — مؤشر مساعد",
                            use_container_width=True,
                        )

        prompt = st.chat_input(
            "اكتب طلبك هنا..."
        )

        if prompt:

            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": prompt,
                }
            )

            evidence_words = [
                "وريني الدليل",
                "أرني الدليل",
                "وريني الصورة",
                "أرني الصورة",
                "show evidence",
                "show me the evidence",
            ]

            is_evidence_request = any(
                word.lower() in prompt.lower()
                for word in evidence_words
            )

            if is_evidence_request:

                answer = (
                    "هذا هو الدليل المرئي من الصورة التي رفعتها."
                    if st.session_state.uploaded_image_bytes
                    else "ارفع صورة أولاً حتى أستطيع عرض الدليل."
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "show_evidence": True,
                    }
                )

                st.rerun()

            elif st.session_state.uploaded_image_bytes:

                with st.spinner("جاري التحليل..."):

                    answer = analyze_image_with_ai(prompt)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
