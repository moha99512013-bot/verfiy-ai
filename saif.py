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

    /* =========================
       الصفحة الرئيسية
       ========================= */

    .stApp {
        background: #000000 !important;
        color: #ffffff !important;
    }

    [data-testid="stAppViewContainer"] {
        background: #000000 !important;
    }

    [data-testid="stMain"] {
        background: #000000 !important;
    }

    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* =========================
       كل النصوص
       ========================= */

    html,
    body,
    p,
    span,
    div,
    label,
    small,
    strong,
    b,
    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        color: #ffffff;
    }

    [data-testid="stMarkdownContainer"] {
        color: #ffffff !important;
    }

    [data-testid="stCaptionContainer"] {
        color: #ffffff !important;
        opacity: 0.8;
    }

    .main-title {
        color: #ffffff !important;
        font-size: 27px;
        font-weight: 800;
        letter-spacing: 0.2px;
        margin-bottom: 2px;
    }

    .sub-title {
        color: #ffffff !important;
        opacity: 0.75;
        font-size: 13px;
        margin-bottom: 20px;
    }

    .section-title {
        color: #ffffff !important;
        font-size: 18px;
        font-weight: 750;
        margin-bottom: 8px;
    }

    .muted {
        color: #ffffff !important;
        opacity: 0.75;
        font-size: 13px;
    }

    /* =========================
       الكروت
       ========================= */

    .card {
        background: #050505 !important;
        border: 1px solid #333333 !important;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,.35);
        color: #ffffff !important;
    }

    /* =========================
       Sidebar
       ========================= */

    section[data-testid="stSidebar"] {
        background: #000000 !important;
        border-right: 1px solid #292929 !important;
    }

    section[data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.3rem;
    }

    .brand-logo {
        width: 46px;
        height: 46px;
        border-radius: 50%;
        border: 1px solid #444444;
        background: #050505;
        color: #ffffff !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        margin-bottom: 10px;
    }

    .side-brand {
        color: #ffffff !important;
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 2px;
    }

    .side-sub {
        color: #ffffff !important;
        opacity: 0.7;
        font-size: 11px;
        margin-bottom: 25px;
    }

    /* =========================
       الأزرار
       ========================= */

    .stButton > button {
        border-radius: 10px !important;
        border: 1px solid #3a3a3a !important;
        background: #050505 !important;
        color: #ffffff !important;
        min-height: 42px;
    }

    .stButton > button:hover {
        background: #111111 !important;
        border-color: #777777 !important;
        color: #ffffff !important;
    }

    .stButton > button * {
        color: #ffffff !important;
    }

    /* =========================
       رفع الملفات
       ========================= */

    [data-testid="stFileUploader"] {
        background: #050505 !important;
        border: 1px dashed #555555 !important;
        border-radius: 13px;
        padding: 8px;
    }

    [data-testid="stFileUploader"] * {
        color: #ffffff !important;
    }

    /* =========================
       Chat
       ========================= */

    [data-testid="stChatMessage"] {
        background: #050505 !important;
        border: 1px solid #333333 !important;
        border-radius: 12px;
        margin-bottom: 8px;
    }

    [data-testid="stChatMessage"] * {
        color: #ffffff !important;
    }

    [data-testid="stChatInput"] textarea {
        background: #050505 !important;
        color: #ffffff !important;
        border: 1px solid #444444 !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #cccccc !important;
        opacity: 1 !important;
    }

    /* =========================
       الحقول
       ========================= */

    input,
    textarea,
    select {
        background: #050505 !important;
        color: #ffffff !important;
        border-color: #444444 !important;
    }

    input::placeholder,
    textarea::placeholder {
        color: #cccccc !important;
        opacity: 1 !important;
    }

    /* =========================
       التنبيهات
       ========================= */

    [data-testid="stAlert"] {
        background: #050505 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    [data-testid="stAlert"] * {
        color: #ffffff !important;
    }

    /* =========================
       Metrics
       ========================= */

    [data-testid="stMetric"] {
        background: #050505 !important;
        border: 1px solid #333333 !important;
        border-radius: 13px;
        padding: 12px;
    }

    [data-testid="stMetric"] * {
        color: #ffffff !important;
    }

    /* =========================
       Status
       ========================= */

    .status {
        display: inline-block;
        padding: 5px 9px;
        border-radius: 20px;
        background: #071007;
        border: 1px solid #3c693c;
        color: #ffffff !important;
        font-size: 11px;
    }

    .warning {
        display: inline-block;
        padding: 5px 9px;
        border-radius: 20px;
        background: #101010;
        border: 1px solid #666666;
        color: #ffffff !important;
        font-size: 11px;
    }

    /* =========================
       Code
       ========================= */

    code,
    pre {
        background: #050505 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    /* =========================
       خط فاصل
       ========================= */

    hr {
        border-color: #2a2a2a !important;
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
    ELA مؤشر مساعد فقط وليس إثباتاً قاطعاً للتلاعب.
    """

    original = Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    buffer = io.BytesIO()

    original.save(
        buffer,
        "JPEG",
        quality=quality
    )

    recompressed = Image.open(
        io.BytesIO(buffer.getvalue())
    ).convert("RGB")

    diff = ImageChops.difference(
        original,
        recompressed
    )

    extrema = diff.getextrema()

    max_diff = max(
        channel_max
        for channel_min, channel_max in extrema
    )

    if max_diff == 0:
        max_diff = 1

    scale = 255 / max_diff

    ela = ImageEnhance.Brightness(
        diff
    ).enhance(scale)

    output = io.BytesIO()

    ela.save(
        output,
        "PNG"
    )

    return output.getvalue()


def prepare_image_for_ai(image_bytes: bytes):

    image = Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    max_size = 1600

    image.thumbnail(
        (max_size, max_size)
    )

    output = io.BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=85,
        optimize=True
    )

    return output.getvalue(), "image/jpeg"


def image_to_data_url(
    image_bytes: bytes,
    mime: str
):
    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

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
            "ضع OPENAI_API_KEY في متغيرات البيئة "
            "أو Streamlit Secrets."
        )

    if (
        st.session_state.uploaded_image_bytes
        is None
    ):
        return "لم يتم رفع أي صورة حتى الآن."

    if (
        st.session_state.ai_calls
        >= MAX_AI_CALLS_PER_SESSION
    ):
        return (
            "تم الوصول إلى الحد المسموح لطلبات "
            "الذكاء الاصطناعي في هذه الجلسة."
        )

    original_bytes = (
        st.session_state.uploaded_image_bytes
    )

    ai_bytes, ai_mime = (
        prepare_image_for_ai(
            original_bytes
        )
    )

    data_url = image_to_data_url(
        ai_bytes,
        ai_mime
    )

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

        result = (
            response.output_text
            .strip()
        )

        st.session_state.ai_calls += 1

        st.session_state.analysis_result = (
            result
        )

        st.session_state.files_analyzed += 1

        st.session_state.operation_log.append(
            {
                "time": datetime.now().strftime(
                    "%H:%M:%S"
                ),
                "operation": (
                    "تحليل صورة بالذكاء الاصطناعي"
                ),
                "file": (
                    st.session_state.uploaded_filename
                ),
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

    st.session_state.uploaded_image_mime = (
        uploaded_file.type
    )

    st.session_state.uploaded_filename = (
        uploaded_file.name
    )

    st.session_state.sha256 = (
        calculate_sha256(data)
    )

    try:
        st.session_state.ela_bytes = (
            create_ela(data)
        )
    except Exception:
        st.session_state.ela_bytes = None

    st.session_state.analysis_result = None

    st.session_state.show_evidence = False

    st.session_state.operation_log.append(
        {
            "time": datetime.now().strftime(
                "%H:%M:%S"
            ),
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

        <div class="side-brand">
            VerifyAI Terminal
        </div>

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

    left, right = st.columns(
        [1.55, 1],
        gap="large"
    )

    # -----------------------------------------------------
    # اليسار
    # -----------------------------------------------------

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
            type=[
                "png",
                "jpg",
                "jpeg",
                "webp"
            ],
            key="main_uploader",
            label_visibility="visible",
        )

        if uploaded_file is not None:

            handle_upload(
                uploaded_file
            )

        if st.session_state.uploaded_image_bytes:

            st.markdown(
                "### الصورة المرفوعة"
            )

            st.image(
                st.session_state.uploaded_image_bytes,
                use_container_width=True,
            )

            st.caption(
                f"الملف: {st.session_state.uploaded_filename}"
            )

            col1, col2 = st.columns(2)

            # -------------------------
            # تحليل
            # -------------------------

            with col1:

                if st.button(
                    "🔎 تحليل الصورة بالـAI",
                    use_container_width=True,
                ):

                    with st.spinner(
                        "جاري تحليل الصورة..."
                    ):

                        analyze_image_with_ai(
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

            # -------------------------
            # الدليل
            # -------------------------

            with col2:

                if st.button(
                    "🧾 وريني الدليل",
                    use_container_width=True,
                ):

                    st.session_state.show_evidence = True

                    st.rerun()

            # -------------------------
            # النتيجة
            # -------------------------

            if st.session_state.analysis_result:

                st.markdown(
                    "### نتيجة تحليل الـAI"
                )

                result_html = (
                    st.session_state
                    .analysis_result
                    .replace(
                        "\n",
                        "<br>"
                    )
                )

                st.markdown(
                    f"""
                    <div class="card">
                        {result_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # -------------------------
            # الدليل المرئي
            # -------------------------

            if st.session_state.show_evidence:

                st.markdown(
                    "### الدليل المرئي"
                )

                st.image(
                    st.session_state.uploaded_image_bytes,
                    caption="الصورة الأصلية المرفوعة",
                    use_container_width=True,
                )

                if st.session_state.ela_bytes:

                    st.markdown(
                        "### ELA"
                    )

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
    # اليمين
    # -----------------------------------------------------

    with right:

        st.markdown(
            '<div class="section-title">المساعد الجنائي الذكي</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="muted">
                اسأل عن الصورة المرفوعة أو اطلب تحليلها.
            </div>
            """,
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

            with st.chat_message(
                message["role"]
            ):

                st.markdown(
                    message["content"]
                )

                if (
                    message.get("show_evidence")
                    and
                    st.session_state.uploaded_image_bytes
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

            # -------------------------
            # طلب الدليل
            # -------------------------

            if is_evidence_request:

                if (
                    st.session_state
                    .uploaded_image_bytes
                ):

                    answer = (
                        "هذا هو الدليل المرئي "
                        "من الصورة التي رفعتها."
                    )

                    show_evidence = True

                else:

                    answer = (
                        "ارفع صورة أولاً "
                        "حتى أستطيع عرض الدليل."
                    )

                    show_evidence = False

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "show_evidence": show_evidence,
                    }
                )

                st.rerun()

            # -------------------------
            # تحليل AI
            # -------------------------

            elif (
                st.session_state
                .uploaded_image_bytes
            ):

                with st.spinner(
                    "جاري التحليل..."
                ):

                    answer = (
                        analyze_image_with_ai(
                            prompt
                        )
                    )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

                st.rerun()

            # -------------------------
            # بدون صورة
            # -------------------------

            else:

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": "ارفع صورة أولاً.",
                    }
                )

                st.rerun()


# =========================================================
# تحليل المستندات
# =========================================================

elif st.session_state.page == "تحليل المستندات":

    st.markdown(
        '<div class="section-title">تحليل المستندات والصور</div>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "ارفع صورة",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp"
        ],
        key="documents_uploader",
    )

    if uploaded_file is not None:

        handle_upload(
            uploaded_file
        )

    if st.session_state.uploaded_image_bytes:

        a, b = st.columns(2)

        with a:

            st.image(
                st.session_state.uploaded_image_bytes,
                use_container_width=True,
            )

        with b:

            if st.session_state.ela_bytes:

                st.image(
                    st.session_state.ela_bytes,
                    caption="ELA — مؤشر مساعد فقط",
                    use_container_width=True,
                )

        if st.button(
            "🔎 تحليل بالذكاء الاصطناعي",
            use_container_width=True,
        ):

            with st.spinner(
                "جاري التحليل..."
            ):

                analyze_image_with_ai(
                    "حلل الصورة كدليل رقمي، واذكر المؤشرات المهمة فقط."
                )

            st.rerun()

        if st.session_state.analysis_result:

            st.markdown(
                "### النتيجة"
            )

            st.markdown(
                st.session_state.analysis_result
            )

        st.markdown(
            "### SHA-256"
        )

        st.code(
            st.session_state.sha256
        )

    else:

        st.info(
            "ارفع صورة أولاً."
        )


# =========================================================
# المحادثة الذكية
# =========================================================

elif st.session_state.page == "المحادثة الذكية":

    st.markdown(
        '<div class="section-title">المحادثة الذكية</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.uploaded_image_bytes:

        st.image(
            st.session_state.uploaded_image_bytes,
            width=400,
        )

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

            if (
                message.get("show_evidence")
                and
                st.session_state.uploaded_image_bytes
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
        "اسأل عن الصورة..."
    )

    if prompt:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        if (
            "وريني الدليل" in prompt
            or
            "أرني الدليل" in prompt
        ):

            answer = (
                "هذا هو الدليل المرئي "
                "من الصورة التي رفعتها."
                if st.session_state.uploaded_image_bytes
                else
                "ارفع صورة أولاً."
            )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "show_evidence": bool(
                        st.session_state.uploaded_image_bytes
                    ),
                }
            )

            st.rerun()

        elif st.session_state.uploaded_image_bytes:

            with st.spinner(
                "جاري التحليل..."
            ):

                answer = (
                    analyze_image_with_ai(
                        prompt
                    )
                )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            st.rerun()

        else:

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": "ارفع صورة أولاً.",
                }
            )

            st.rerun()


# =========================================================
# التقارير
# =========================================================

elif st.session_state.page == "التقارير":

    st.markdown(
        '<div class="section-title">التقارير</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.analysis_result:

        report = (
            "VerifyAI Terminal\n\n"
            f"الملف: {st.session_state.uploaded_filename}\n\n"
            f"SHA-256: {st.session_state.sha256}\n\n"
            "نتيجة التحليل:\n"
            f"{st.session_state.analysis_result}"
        )

        st.text_area(
            "التقرير",
            report,
            height=350,
        )

        st.download_button(
            "⬇️ تحميل التقرير",
            report,
            "verifyai_report.txt",
            "text/plain",
        )

    else:

        st.info(
            "لا يوجد تحليل حتى الآن."
        )


# =========================================================
# التحقق من الهوية
# =========================================================

elif st.session_state.page == "التحقق من الهوية":

    st.markdown(
        '<div class="section-title">التحقق من الهوية</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "هذه الصفحة جاهزة للتوسعة لاحقاً. "
        "لا يتم تحديد هوية الأشخاص من الصور."
    )


# =========================================================
# التشفير والأمان
# =========================================================

elif st.session_state.page == "التشفير والأمان":

    st.markdown(
        '<div class="section-title">التشفير والأمان</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.sha256:

        st.write(
            "SHA-256"
        )

        st.code(
            st.session_state.sha256
        )

    else:

        st.info(
            "ارفع صورة أولاً."
        )


# =========================================================
# سجل العمليات
# =========================================================

elif st.session_state.page == "سجل العمليات":

    st.markdown(
        '<div class="section-title">سجل العمليات</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.operation_log:

        st.info(
            "لا توجد عمليات حتى الآن."
        )

    else:

        for item in reversed(
            st.session_state.operation_log
        ):

            st.markdown(
                f"""
                <div class="card">

                    <b>{item.get("operation", "")}</b>

                    <br>

                    الوقت:
                    {item.get("time", "")}

                    <br>

                    الملف:
                    {item.get("file", "")}

                </div>
                """,
                unsafe_allow_html=True,
            )


# =========================================================
# الإعدادات
# =========================================================

elif st.session_state.page == "الإعدادات":

    st.markdown(
        '<div class="section-title">الإعدادات</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "Model:",
        MODEL
    )

    st.write(
        "OpenAI API:",
        "متصل" if client else "غير متصل"
    )

    st.write(
        "طلبات AI:",
        f"{st.session_state.ai_calls} / {MAX_AI_CALLS_PER_SESSION}"
    )


# =========================================================
# المقاييس السفلية
# =========================================================

st.markdown("---")

m1, m2, m3 = st.columns(3)

with m1:

    st.metric(
        "طلبات AI",
        st.session_state.ai_calls
    )

with m2:

    st.metric(
        "صورة مرفوعة",
        "نعم"
        if st.session_state.uploaded_image_bytes
        else "لا"
    )

with m3:

    st.metric(
        "API",
        "متصل"
        if client
        else "غير متصل"
    )
