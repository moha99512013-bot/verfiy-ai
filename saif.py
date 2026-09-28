import os
import io
import base64
import hashlib
from datetime import datetime

import streamlit as st
from PIL import Image, ImageChops, ImageEnhance
from openai import OpenAI


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="VerifyAI Terminal",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# OPENAI API
# =========================================================

API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    try:
        API_KEY = st.secrets["OPENAI_API_KEY"]
    except Exception:
        API_KEY = None

client = None

if API_KEY:
    try:
        client = OpenAI(api_key=API_KEY)
    except Exception:
        client = None


# =========================================================
# DARK UI / WHITE TEXT
# =========================================================

st.markdown(
    """
    <style>

    /* =========================
       MAIN BACKGROUND
       ========================= */

    .stApp {
        background-color: #000000 !important;
        color: #ffffff !important;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #000000 !important;
    }

    [data-testid="stHeader"] {
        background-color: #000000 !important;
    }


    /* =========================
       TEXT
       ========================= */

    .stApp p,
    .stApp span,
    .stApp label,
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp h5,
    .stApp h6 {
        color: #ffffff !important;
    }


    /* =========================
       SIDEBAR
       ========================= */

    [data-testid="stSidebar"] {
        background-color: #050505 !important;
    }

    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }


    /* =========================
       BUTTONS
       ========================= */

    .stButton > button {
        background-color: #111111 !important;
        color: #ffffff !important;
        border: 1px solid #444444 !important;
        border-radius: 8px !important;
    }

    .stButton > button:hover {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border-color: #777777 !important;
    }


    /* =========================
       FILE UPLOADER
       ========================= */

    [data-testid="stFileUploader"] {
        background-color: #080808 !important;
        border: 1px dashed #555555 !important;
        border-radius: 12px !important;
    }

    [data-testid="stFileUploader"] section {
        background-color: #080808 !important;
    }

    [data-testid="stFileUploader"] div {
        color: #ffffff !important;
    }

    [data-testid="stFileUploader"] button {
        background-color: #151515 !important;
        color: #ffffff !important;
        border: 1px solid #555555 !important;
    }


    /* =========================
       TEXT INPUT
       ========================= */

    .stTextInput input,
    .stTextArea textarea {
        background-color: #080808 !important;
        color: #ffffff !important;
        border: 1px solid #444444 !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #888888 !important;
    }


    /* =========================
       CHAT
       ========================= */

    [data-testid="stChatMessage"] {
        background-color: #080808 !important;
        color: #ffffff !important;
        border: 1px solid #222222 !important;
    }

    [data-testid="stChatInput"] {
        background-color: #080808 !important;
    }

    [data-testid="stChatInput"] textarea {
        background-color: #111111 !important;
        color: #ffffff !important;
        border: 1px solid #444444 !important;
    }


    /* =========================
       ALERTS
       ========================= */

    [data-testid="stAlert"] {
        background-color: #101010 !important;
        border: 1px solid #333333 !important;
    }

    [data-testid="stAlert"] * {
        color: #ffffff !important;
    }


    /* =========================
       METRICS
       ========================= */

    [data-testid="stMetric"] {
        background-color: #080808 !important;
        color: #ffffff !important;
        border: 1px solid #222222 !important;
        border-radius: 10px !important;
    }

    [data-testid="stMetric"] * {
        color: #ffffff !important;
    }


    /* =========================
       SELECT BOXES
       ========================= */

    [data-baseweb="select"] > div {
        background-color: #080808 !important;
        color: #ffffff !important;
        border-color: #444444 !important;
    }


    /* =========================
       DIVIDERS
       ========================= */

    hr {
        border-color: #222222 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_bytes" not in st.session_state:
    st.session_state.uploaded_bytes = None

if "uploaded_name" not in st.session_state:
    st.session_state.uploaded_name = None

if "uploaded_mime" not in st.session_state:
    st.session_state.uploaded_mime = None

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "ela_image" not in st.session_state:
    st.session_state.ela_image = None

if "ela_for_hash" not in st.session_state:
    st.session_state.ela_for_hash = None

if "sha256" not in st.session_state:
    st.session_state.sha256 = None

if "operations" not in st.session_state:
    st.session_state.operations = []


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def add_operation(text):
    st.session_state.operations.insert(
        0,
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": text,
        },
    )


def calculate_sha256(data):
    return hashlib.sha256(data).hexdigest()


def create_ela(image, quality=90):
    """
    Creates ELA from the exact image uploaded by the user.

    ELA is an auxiliary visual indicator,
    not conclusive proof of manipulation.
    """

    image = image.convert("RGB")

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=quality,
    )

    buffer.seek(0)

    compressed = Image.open(
        buffer
    ).convert("RGB")

    diff = ImageChops.difference(
        image,
        compressed,
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

    return ela


def image_to_data_url(
    data,
    mime_type,
):
    encoded = base64.b64encode(
        data
    ).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def analyze_image_with_ai(
    image_bytes,
    mime_type,
):

    if not client:
        return (
            "⚠️ OpenAI API غير متصل.\n\n"
            "تأكد من إضافة OPENAI_API_KEY "
            "في Streamlit Cloud → Settings → Secrets."
        )

    image_url = image_to_data_url(
        image_bytes,
        mime_type,
    )

    instructions = """
أنت مساعد جنائي رقمي لمنصة VerifyAI.

حلل الصورة المرفوعة نفسها.

قدم التحليل باللغة العربية.

ركز على:

1. وصف ما يظهر في الصورة.
2. الملاحظات البصرية.
3. مؤشرات التعديل أو التركيب المحتملة.
4. اتساق الإضاءة والظلال والمنظور.
5. النصوص والعناصر غير المعتادة.
6. مستوى الثقة.
7. حدود التحليل.

مهم:
لا تعتبر ملاحظة واحدة دليلًا قاطعًا على أن الصورة معدلة.
ELA مؤشر مساعد فقط وليس إثباتًا نهائيًا.
إذا لم توجد أدلة كافية، وضح أن النتيجة غير مؤكدة.
"""

    try:

        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=instructions,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "حلل هذه الصورة "
                                "المرفوعة."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": image_url,
                        },
                    ],
                }
            ],
        )

        return response.output_text

    except Exception as e:

        return (
            "حدث خطأ أثناء الاتصال بـ OpenAI.\n\n"
            f"تفاصيل الخطأ: {str(e)}"
        )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        # 🔎 VerifyAI

        ### المنصة الوطنية للاستخبارات الجنائية الرقمية
        """
    )

    st.divider()

    pages = [
        ("🏠", "الرئيسية"),
        ("📄", "تحليل المستندات"),
        ("💬", "المحادثة الذكية"),
        ("📊", "التقارير"),
        ("🪪", "التحقق من الهوية"),
        ("🔐", "التشفير والأمان"),
        ("🕘", "سجل العمليات"),
        ("⚙️", "الإعدادات"),
    ]

    for icon, page_name in pages:

        if st.button(
            f"{icon}  {page_name}",
            use_container_width=True,
            key=f"nav_{page_name}",
        ):

            st.session_state.page = page_name

            st.rerun()


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div style="
        padding: 10px 0 25px 0;
        border-bottom: 1px solid #222;
        margin-bottom: 25px;
    ">

        <div style="
            font-size: 30px;
            font-weight: 700;
            color: #ffffff;
        ">
            🔎 VerifyAI Terminal
        </div>

        <div style="
            font-size: 15px;
            color: #aaaaaa;
            margin-top: 6px;
        ">
            المنصة الوطنية للاستخبارات الجنائية الرقمية
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# API STATUS
# =========================================================

if client:

    st.success(
        "✓ OpenAI API متصل"
    )

else:

    st.warning(
        "⚠️ OpenAI API غير متصل. "
        "تأكد من OPENAI_API_KEY في Secrets."
    )


# =========================================================
# HOME
# =========================================================

if st.session_state.page == "الرئيسية":

    st.header(
        "تحليل الأدلة الرقمية"
    )

    st.write(
        "ارفع صورة لتحليلها باستخدام الذكاء الاصطناعي."
    )

    uploaded_file = st.file_uploader(
        "ارفع صورة",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
        ],
    )


    # =====================================================
    # NEW IMAGE
    # =====================================================

    if uploaded_file:

        image_bytes = uploaded_file.getvalue()

        current_hash = calculate_sha256(
            image_bytes
        )


        # -------------------------------------------------
        # إذا تغيرت الصورة:
        # امسح التحليل و ELA القديم
        # -------------------------------------------------

        if current_hash != st.session_state.sha256:

            st.session_state.analysis = None

            st.session_state.ela_image = None

            st.session_state.ela_for_hash = None


        st.session_state.uploaded_bytes = image_bytes

        st.session_state.uploaded_name = (
            uploaded_file.name
        )

        st.session_state.uploaded_mime = (
            uploaded_file.type
        )

        st.session_state.sha256 = current_hash


        image = Image.open(
            io.BytesIO(image_bytes)
        )


        # =================================================
        # ORIGINAL IMAGE
        # =================================================

        st.subheader(
            "الصورة المرفوعة"
        )

        st.image(
            image,
            caption=uploaded_file.name,
            use_container_width=True,
        )

        st.write(
            f"SHA-256: `{current_hash}`"
        )


        col1, col2 = st.columns(2)


        # =================================================
        # AI ANALYSIS
        # =================================================

        with col1:

            if st.button(
                "🔍 تحليل الصورة بالذكاء الاصطناعي",
                use_container_width=True,
            ):

                with st.spinner(
                    "جاري تحليل الصورة..."
                ):

                    result = analyze_image_with_ai(
                        image_bytes,
                        uploaded_file.type,
                    )

                st.session_state.analysis = result

                add_operation(
                    "تحليل الصورة: "
                    + uploaded_file.name
                )


        # =================================================
        # ELA
        # =================================================

        with col2:

            if st.button(
                "🔬 المؤشر البصري ELA",
                use_container_width=True,
            ):

                with st.spinner(
                    "جاري إنشاء مؤشر ELA..."
                ):

                    ela = create_ela(
                        image
                    )

                st.session_state.ela_image = ela

                st.session_state.ela_for_hash = (
                    current_hash
                )

                add_operation(
                    "إنشاء ELA للصورة: "
                    + uploaded_file.name
                )


        # =================================================
        # AI RESULT
        # =================================================

        if st.session_state.analysis:

            st.divider()

            st.subheader(
                "نتيجة تحليل الذكاء الاصطناعي"
            )

            st.write(
                st.session_state.analysis
            )


        # =================================================
        # ELA RESULT
        # =================================================

        if (
            st.session_state.ela_image
            and
            st.session_state.ela_for_hash
            == current_hash
        ):

            st.divider()

            st.subheader(
                "المؤشر البصري ELA"
            )

            st.caption(
                "هذه الصورة مولدة من الصورة التي رفعتها "
                "أنت، وليست صورة اختبار."
            )

            st.image(
                st.session_state.ela_image,
                caption=(
                    "ELA — مؤشر بصري مساعد "
                    "وليس دليلًا قاطعًا."
                ),
                use_container_width=True,
            )


# =========================================================
# SMART CHAT
# =========================================================

elif st.session_state.page == "المحادثة الذكية":

    st.header(
        "💬 المحادثة الذكية"
    )

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )


    prompt = st.chat_input(
        "اكتب سؤالك هنا..."
    )


    if prompt:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )


        with st.chat_message(
            "user"
        ):

            st.markdown(
                prompt
            )


        if client:

            try:

                response = client.responses.create(
                    model="gpt-5.6-luna",
                    instructions="""
أنت مساعد VerifyAI للذكاء الجنائي الرقمي.
أجب بالعربية بوضوح.
لا تعتبر أي مؤشر واحد دليلًا قاطعًا.
""",
                    input=prompt,
                )

                answer = response.output_text

            except Exception as e:

                answer = (
                    "حدث خطأ في OpenAI:\n"
                    + str(e)
                )

        else:

            answer = (
                "⚠️ OpenAI API غير متصل. "
                "تحقق من Secrets."
            )


        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        st.rerun()


# =========================================================
# REPORTS
# =========================================================

elif st.session_state.page == "التقارير":

    st.header(
        "📊 التقارير"
    )

    if st.session_state.analysis:

        st.subheader(
            "آخر تحليل"
        )

        st.write(
            st.session_state.analysis
        )

    else:

        st.info(
            "لم يتم إنشاء تقرير بعد."
        )


# =========================================================
# OPERATION LOG
# =========================================================

elif st.session_state.page == "سجل العمليات":

    st.header(
        "🕘 سجل العمليات"
    )

    if not st.session_state.operations:

        st.info(
            "لا توجد عمليات حتى الآن."
        )

    else:

        for operation in (
            st.session_state.operations
        ):

            st.write(
                f"**{operation['time']}** — "
                f"{operation['text']}"
            )


# =========================================================
# OTHER PAGES
# =========================================================

elif st.session_state.page == "تحليل المستندات":

    st.header(
        "📄 تحليل المستندات"
    )

    st.info(
        "قسم تحليل المستندات جاهز للإضافة."
    )


elif st.session_state.page == "التحقق من الهوية":

    st.header(
        "🪪 التحقق من الهوية"
    )

    st.info(
        "قسم التحقق من الهوية جاهز للإضافة."
    )


elif st.session_state.page == "التشفير والأمان":

    st.header(
        "🔐 التشفير والأمان"
    )

    st.info(
        "قسم التشفير والأمان جاهز للإضافة."
    )


elif st.session_state.page == "الإعدادات":

    st.header(
        "⚙️ الإعدادات"
    )

    st.write(
        "إعدادات VerifyAI Terminal"
    )


# =========================================================
# FOOTER METRICS
# =========================================================

st.divider()

col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "حالة الذكاء الاصطناعي",
        "متصل" if client else "غير متصل",
    )


with col2:

    st.metric(
        "العمليات",
        len(
            st.session_state.operations
        ),
    )


with col3:

    st.metric(
        "الصورة الحالية",
        "مرفوعة"
        if st.session_state.uploaded_bytes
        else "لا توجد",
    )
