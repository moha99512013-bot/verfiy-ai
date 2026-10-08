import os
import math
import html
import json

import requests
import streamlit as st
import folium

from streamlit_folium import st_folium


# =========================================================
# OPTIONAL OPENAI
# =========================================================
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# =========================================================
# PAGE
# =========================================================
st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# CONSTANTS
# =========================================================
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OSRM_URL = "https://router.project-osrm.org/route/v1/foot"

DEFAULT_CENTER = (21.5433, 39.1728)

HEADERS = {
    "User-Agent": "VerifyAI-Access/14.0"
}

# OpenAI
MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-6-luna"
)

# حفاظًا على رصيد API
MAX_AI_CALLS_PER_SESSION = 10

# يبحث AI تلقائيًا عند نقص البيانات
AUTO_AI_SEARCH = True


# =========================================================
# SECRETS
# =========================================================
def get_secret(name):
    value = os.getenv(name, "")

    if value:
        return value

    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


OPENAI_KEY = get_secret(
    "OPENAI_API_KEY"
)


# =========================================================
# OPENAI CLIENT
# =========================================================
openai_client = None

if OPENAI_AVAILABLE and OPENAI_KEY:

    try:
        openai_client = OpenAI(
            api_key=OPENAI_KEY
        )
    except Exception:
        openai_client = None


# =========================================================
# CSS
# =========================================================
st.markdown(
    """
<style>

@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', sans-serif;
}

.stApp {
    background: #f5f3ff;
}

.block-container {
    padding-top: 1.25rem;
    padding-bottom: 3rem;
}

.main-title {
    font-size: 38px;
    font-weight: 800;
    color: #21184d;
    margin-bottom: 2px;
}

.subtitle {
    color: #716c82;
    font-size: 15px;
    margin-bottom: 18px;
}

.card {
    background: white;
    border-radius: 20px;
    padding: 20px;
    box-shadow: 0 5px 25px rgba(60,40,120,.08);
    border: 1px solid #ebe7ff;
    margin-bottom: 16px;
}

.ai-card {
    background: linear-gradient(
        135deg,
        #ffffff 0%,
        #f8f5ff 100%
    );
    border: 2px solid #ddd4ff;
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 5px 25px rgba(80,60,150,.08);
}

.ai-header {
    font-size: 22px;
    font-weight: 800;
    color: #392477;
}

.ai-answer {
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid #e8e2ff;
    padding: 18px;
    margin-top: 14px;
    color: #302a3d;
    line-height: 2;
}

.score-card {
    background: white;
    border-radius: 22px;
    padding: 22px;
    margin-bottom: 16px;
    border: 1px solid #e5defd;
    box-shadow: 0 7px 28px rgba(80,60,150,.08);
}

.score-number {
    font-size: 54px;
    line-height: 1;
    font-weight: 800;
    color: #7657ff;
}

.score-label {
    color: #6b6478;
    font-size: 14px;
    margin-top: 5px;
}

.score-good {
    background: #eaf9f0;
    border: 1px solid #bde8ca;
    color: #137a43;
    border-radius: 14px;
    padding: 10px 13px;
    margin-bottom: 9px;
}

.score-unknown {
    background: #fff8e7;
    border: 1px solid #f1dda2;
    color: #8a6500;
    border-radius: 14px;
    padding: 10px 13px;
    margin-bottom: 9px;
}

.score-bad {
    background: #fff0f0;
    border: 1px solid #f0c6c6;
    color: #a63333;
    border-radius: 14px;
    padding: 10px 13px;
    margin-bottom: 9px;
}

.parking-card {
    background: white;
    border: 2px solid #cfe4ff;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 12px;
    box-shadow: 0 5px 20px rgba(25,95,170,.07);
}

.badge-purple {
    display: inline-block;
    background: #7657ff;
    color: white;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}

.badge-blue {
    display: inline-block;
    background: #087cff;
    color: white;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}

.badge-green {
    display: inline-block;
    background: #16a05c;
    color: white;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}

.hint {
    background: #f7f4ff;
    border: 1px solid #ded5ff;
    border-radius: 14px;
    padding: 12px 15px;
    color: #44356e;
    margin-top: 10px;
}

.small-muted {
    color: #777;
    font-size: 13px;
}

.footer {
    text-align: center;
    color: #888;
    font-size: 12px;
    margin-top: 30px;
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# SESSION
# =========================================================
DEFAULTS = {
    "page": "🗺️ الخريطة",

    "search_query": "",
    "search_results": [],
    "search_index": 0,
    "manual_mode": False,

    "center": DEFAULT_CENTER,

    "building_details": None,

    "service": "overview",

    "selection_mode": None,
    "start_point": None,
    "destination_point": None,
    "route_result": None,

    "parking_query": "",
    "parking_results_search": [],
    "parking_search_index": 0,
    "parking_manual_mode": False,
    "parking_center": DEFAULT_CENTER,
    "parking_radius": 2500,
    "parking_results": [],
    "parking_key": None,

    "map_key": 0,

    # AI
    "ai_calls": 0,
    "ai_question": "",
    "ai_answer": "",
    "auto_ai_checked": False,
    "auto_ai_answer": "",
    "ai_history": [],

    # Score
    "score_details": None,
}

for key, value in DEFAULTS.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# BASIC HELPERS
# =========================================================
def safe_float(
    value,
    default=None
):

    try:
        return float(value)
    except Exception:
        return default


def distance_m(
    lat1,
    lon1,
    lat2,
    lon2
):

    R = 6371000.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(
        lat2 - lat1
    )

    dl = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dp / 2) ** 2

        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return (
        2
        * R
        * math.asin(
            math.sqrt(a)
        )
    )


def element_center(element):

    center = element.get(
        "center"
    )

    if center:

        lat = safe_float(
            center.get("lat")
        )

        lon = safe_float(
            center.get("lon")
        )

        if (
            lat is not None
            and lon is not None
        ):
            return lat, lon

    geometry = element.get(
        "geometry",
        []
    )

    if geometry:

        lats = [
            point["lat"]
            for point in geometry
            if "lat" in point
        ]

        lons = [
            point["lon"]
            for point in geometry
            if "lon" in point
        ]

        if lats and lons:

            return (
                sum(lats) / len(lats),
                sum(lons) / len(lons)
            )

    lat = safe_float(
        element.get("lat")
    )

    lon = safe_float(
        element.get("lon")
    )

    if (
        lat is not None
        and lon is not None
    ):
        return lat, lon

    return None


def point_in_polygon(
    lat,
    lon,
    polygon
):

    if (
        not polygon
        or len(polygon) < 3
    ):
        return False

    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):

        yi, xi = polygon[i]
        yj, xj = polygon[j]

        if (
            (xi > lon)
            !=
            (xj > lon)
        ):

            cross = (
                (yj - yi)
                * (lon - xi)
                / ((xj - xi) or 1e-12)
                + yi
            )

            if lat < cross:
                inside = not inside

        j = i

    return inside


def feature_level(tags):

    for key in (
        "level",
        "level:ref",
        "floor",
        "addr:floor",
    ):

        if tags.get(key) is not None:
            return str(
                tags.get(key)
            )

    return None


def floor_label(value):

    if value is None:
        return "الطابق غير محدد"

    mapping = {
        "-3": "القبو الثالث",
        "-2": "القبو الثاني",
        "-1": "القبو الأول",
        "0": "الدور الأرضي",
        "1": "الدور الأول",
        "2": "الدور الثاني",
        "3": "الدور الثالث",
        "4": "الدور الرابع",
        "5": "الدور الخامس",
        "6": "الدور السادس",
        "7": "الدور السابع",
        "8": "الدور الثامن",
        "9": "الدور التاسع",
        "10": "الدور العاشر",
    }

    return mapping.get(
        str(value),
        f"الطابق {value}"
    )


def get_name(
    tags,
    fallback="بدون اسم"
):

    for key in (
        "name:ar",
        "name",
        "official_name",
        "brand",
        "operator",
    ):

        if tags.get(key):
            return tags[key]

    return fallback


def accessible_tag(tags):

    values = {
        str(
            tags.get(
                "wheelchair",
                ""
            )
        ).lower(),

        str(
            tags.get(
                "toilets:wheelchair",
                ""
            )
        ).lower(),
    }

    return bool(
        {
            "yes",
            "designated",
            "accessible",
        }
        &
        values
    )


def ai_available():

    return (
        openai_client is not None
        and bool(OPENAI_KEY)
    )


def ai_remaining():

    return max(
        0,
        MAX_AI_CALLS_PER_SESSION
        - st.session_state.ai_calls
    )


def set_center(
    lat,
    lon
):

    st.session_state.center = (
        lat,
        lon
    )

    st.session_state.building_details = None
    st.session_state.service = "overview"

    st.session_state.ai_question = ""
    st.session_state.ai_answer = ""
    st.session_state.auto_ai_answer = ""
    st.session_state.auto_ai_checked = False
    st.session_state.score_details = None

    st.session_state.map_key += 1


# =========================================================
# REVERSE GEOCODE
# =========================================================
@st.cache_data(
    ttl=120,
    show_spinner=False
)
def reverse_geocode(
    lat,
    lon
):

    try:

        response = requests.get(
            f"{NOMINATIM_URL}/reverse",

            params={
                "lat": lat,
                "lon": lon,
                "format": "json",
                "accept-language": "ar,en",
            },

            headers=HEADERS,
            timeout=15,
        )

        if response.ok:

            return response.json().get(
                "display_name",
                "موقع محدد"
            )

    except Exception:
        pass

    return "موقع محدد"


# =========================================================
# SEARCH
# =========================================================
@st.cache_data(
    ttl=120,
    show_spinner=False
)
def search_osm_places(
    query
):

    if (
        not query
        or not query.strip()
    ):
        return []

    try:

        response = requests.get(
            f"{NOMINATIM_URL}/search",

            params={
                "q": query,
                "format": "json",
                "limit": 8,
                "addressdetails": 1,
                "accept-language": "ar,en",
            },

            headers=HEADERS,
            timeout=15,
        )

        if response.ok:
            return response.json()

    except Exception:
        pass

    return []


# =========================================================
# BUILDING DETAILS
# =========================================================
@st.cache_data(
    ttl=300,
    show_spinner=False
)
def get_building_details(
    lat,
    lon,
    radius=500
):

    query = f"""
    [out:json][timeout:90];

    (
      way["building"](around:{radius},{lat},{lon});
      relation["building"](around:{radius},{lat},{lon});

      nwr["amenity"="toilets"](around:{radius},{lat},{lon});
      nwr["elevator"](around:{radius},{lat},{lon});
      nwr["entrance"](around:{radius},{lat},{lon});

      nwr["highway"="steps"](around:{radius},{lat},{lon});

      nwr["room"](around:{radius},{lat},{lon});
      nwr["indoor"](around:{radius},{lat},{lon});
      nwr["level"](around:{radius},{lat},{lon});

      nwr["wheelchair"](around:{radius},{lat},{lon});

      nwr["ramp"](around:{radius},{lat},{lon});
    );

    out body geom center;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=120,
        )

        if not response.ok:
            return None

        elements = response.json().get(
            "elements",
            []
        )

    except Exception:
        return None

    buildings = []
    features = []

    for element in elements:

        tags = element.get(
            "tags",
            {}
        )

        center = element_center(
            element
        )

        if not center:
            continue

        if (
            tags.get("building")
            or tags.get("building:part")
        ):

            polygon = [
                (
                    float(point["lat"]),
                    float(point["lon"])
                )

                for point in element.get(
                    "geometry",
                    []
                )

                if (
                    "lat" in point
                    and
                    "lon" in point
                )
            ]

            buildings.append(
                {
                    "type":
                        element.get("type"),

                    "id":
                        element.get("id"),

                    "tags":
                        tags,

                    "center":
                        center,

                    "polygon":
                        polygon,
                }
            )

        else:

            if any(
                [
                    tags.get("amenity")
                    == "toilets",

                    tags.get("elevator"),

                    tags.get("entrance"),

                    tags.get("highway")
                    == "steps",

                    tags.get("room"),

                    tags.get("indoor"),

                    tags.get("level")
                    is not None,

                    tags.get("wheelchair"),

                    tags.get("ramp"),
                ]
            ):

                features.append(
                    {
                        "type":
                            element.get("type"),

                        "id":
                            element.get("id"),

                        "tags":
                            tags,

                        "center":
                            center,
                    }
                )

    if not buildings:
        return None

    selected = min(
        buildings,

        key=lambda building:

            0

            if (
                building["polygon"]
                and
                point_in_polygon(
                    lat,
                    lon,
                    building["polygon"]
                )
            )

            else distance_m(
                lat,
                lon,
                *building["center"]
            )
    )

    selected_distance = (
        0

        if (
            selected["polygon"]
            and
            point_in_polygon(
                lat,
                lon,
                selected["polygon"]
            )
        )

        else distance_m(
            lat,
            lon,
            *selected["center"]
        )
    )

    if selected_distance > 400:
        return None

    result = {

        "building":
            selected,

        "distance":
            selected_distance,

        "toilets": [],

        "accessible_toilets": [],

        "elevators": [],

        "entrances": [],

        "accessible_entrances": [],

        "stairs": [],

        "ramps": [],

        "rooms": [],

        "wheelchair_features": [],

        "levels": set(),
    }

    for feature in features:

        inside = (
            selected["polygon"]
            and
            point_in_polygon(
                feature["center"][0],
                feature["center"][1],
                selected["polygon"]
            )
        )

        nearby = (
            distance_m(
                *feature["center"],
                *selected["center"]
            ) <= 180
        )

        if not (
            inside
            or nearby
        ):
            continue

        tags = feature["tags"]

        level = feature_level(
            tags
        )

        if level is not None:
            result["levels"].add(
                level
            )

        if (
            tags.get("amenity")
            == "toilets"
        ):

            result["toilets"].append(
                feature
            )

            if accessible_tag(
                tags
            ):

                result[
                    "accessible_toilets"
                ].append(
                    feature
                )

        if (
            tags.get("elevator")
            or
            tags.get("indoor")
            == "elevator"
        ):

            result["elevators"].append(
                feature
            )

        if tags.get("entrance"):

            result["entrances"].append(
                feature
            )

            if (
                str(
                    tags.get(
                        "wheelchair",
                        ""
                    )
                ).lower()
                in {
                    "yes",
                    "designated",
                    "accessible"
                }
            ):

                result[
                    "accessible_entrances"
                ].append(
                    feature
                )

        if (
            tags.get("highway")
            == "steps"
        ):

            result["stairs"].append(
                feature
            )

        if tags.get("ramp"):

            result["ramps"].append(
                feature
            )

        if (
            tags.get("room")
            or
            tags.get("indoor")
            == "room"
        ):

            result["rooms"].append(
                feature
            )

        if tags.get("wheelchair"):

            result[
                "wheelchair_features"
            ].append(
                feature
            )

    result["levels"] = sorted(
        result["levels"],

        key=lambda value: (
            safe_float(
                value,
                999
            ),
            value
        )
    )

    return result


# =========================================================
# ACCESSIBLE PARKING
# =========================================================
@st.cache_data(
    ttl=300,
    show_spinner=False
)
def get_accessible_parking(
    lat,
    lon,
    radius=2500
):

    query = f"""
    [out:json][timeout:90];

    (
      nwr["amenity"="parking"]["capacity:disabled"]
        (around:{radius},{lat},{lon});

      nwr["amenity"="parking"]["wheelchair"="yes"]
        (around:{radius},{lat},{lon});

      nwr["amenity"="parking_space"]
        ["parking_space"="disabled"]
        (around:{radius},{lat},{lon});

      nwr["amenity"="parking_space"]
        ["disabled"="designated"]
        (around:{radius},{lat},{lon});

      nwr["amenity"="parking_space"]
        ["wheelchair"="yes"]
        (around:{radius},{lat},{lon});

      nwr["amenity"="parking_space"]
        ["capacity:disabled"]
        (around:{radius},{lat},{lon});
    );

    out body geom center;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=120,
        )

        if not response.ok:
            return []

        elements = response.json().get(
            "elements",
            []
        )

    except Exception:
        return []

    results = []
    seen = set()

    for element in elements:

        center = element_center(
            element
        )

        if not center:
            continue

        tags = element.get(
            "tags",
            {}
        )

        key = (
            round(center[0], 5),
            round(center[1], 5)
        )

        if key in seen:
            continue

        seen.add(key)

        if (
            tags.get("parking_space")
            == "disabled"
            or
            tags.get("disabled")
            == "designated"
        ):

            kind = (
                "موقف مخصص لذوي الهمم"
            )

        elif tags.get(
            "capacity:disabled"
        ):

            kind = (
                f"يحتوي على "
                f"{tags['capacity:disabled']} "
                f"موقف مخصص"
            )

        else:

            kind = (
                "موقف مهيأ حسب "
                "بيانات OpenStreetMap"
            )

        results.append(
            {
                "center":
                    center,

                "tags":
                    tags,

                "name":
                    get_name(
                        tags,
                        "موقف ذوي الهمم"
                    ),

                "kind":
                    kind,

                "distance":
                    distance_m(
                        lat,
                        lon,
                        *center
                    ),
            }
        )

    results.sort(
        key=lambda item:
            item["distance"]
    )

    return results[:100]


# =========================================================
# ACCESSIBILITY SCORE
# =========================================================
def calculate_accessibility_score(
    details,
    parking_results
):
    """
    هذا ليس اعتمادًا رسميًا للمبنى.
    هو مؤشر لمدى وجود أدلة مسجلة عن
    عناصر الوصول الشامل.
    """

    items = []

    # -----------------------------------------------------
    # 1. Accessible Entrance
    # -----------------------------------------------------
    if (
        details
        and
        details[
            "accessible_entrances"
        ]
    ):

        items.append(
            {
                "name":
                    "🚪 مدخل مهيأ",

                "points":
                    20,

                "status":
                    "confirmed",

                "reason":
                    "يوجد مدخل موسوم كمهيأ في بيانات الخريطة.",
            }
        )

    elif (
        details
        and
        details["entrances"]
    ):

        items.append(
            {
                "name":
                    "🚪 مدخل مهيأ",

                "points":
                    0,

                "status":
                    "unknown",

                "reason":
                    "يوجد مدخل، لكن لا توجد علامة وصول كافية لتأكيد أنه مهيأ.",
            }
        )

    else:

        items.append(
            {
                "name":
                    "🚪 مدخل مهيأ",

                "points":
                    0,

                "status":
                    "unknown",

                "reason":
                    "لا توجد بيانات كافية عن المدخل.",
            }
        )

    # -----------------------------------------------------
    # 2. Elevator
    # -----------------------------------------------------
    if (
        details
        and
        details["elevators"]
    ):

        items.append(
            {
                "name":
                    "🛗 مصعد",

                "points":
                    15,

                "status":
                    "confirmed",

                "reason":
                    "تم العثور على عنصر مصعد في بيانات الخريطة.",
            }
        )

    else:

        items.append(
            {
                "name":
                    "🛗 مصعد",

                "points":
                    0,

                "status":
                    "unknown",

                "reason":
                    "لا توجد بيانات مؤكدة عن المصعد.",
            }
        )

    # -----------------------------------------------------
    # 3. Accessible Toilet
    # -----------------------------------------------------
    if (
        details
        and
        details[
            "accessible_toilets"
        ]
    ):

        items.append(
            {
                "name":
                    "🚻 حمام مهيأ",

                "points":
                    15,

                "status":
                    "confirmed",

                "reason":
                    "تم العثور على حمام موسوم بإمكانية الوصول.",
            }
        )

    elif (
        details
        and
        details["toilets"]
    ):

        items.append(
            {
                "name":
                    "🚻 حمام مهيأ",

                "points":
                    0,

                "status":
                    "unknown",

                "reason":
                    "يوجد حمام، لكن لم يتم تأكيد تهيئته.",
            }
        )

    else:

        items.append(
            {
                "name":
                    "🚻 حمام مهيأ",

                "points":
                    0,

                "status":
                    "unknown",

                "reason":
                    "لا توجد بيانات كافية عن الحمام.",
            }
        )

    # -----------------------------------------------------
    # 4. Accessible Parking
    # -----------------------------------------------------
    if parking_results:

        items.append(
            {
                "name":
                    "🅿️ موقف ذوي الهمم",

                "points":
                    15,

                "status":
                    "confirmed",

                "reason":
                    f"تم العثور على {len(parking_results)} موقف مسجل قريبًا.",
            }
        )

    else:

        items.append(
            {
                "name":
                    "🅿️ موقف ذوي الهمم",

                "points":
                    0,

                "status":
                    "unknown",

                "reason":
                    "لم يتم العثور على إحداثيات مواقف مهيأة.",
            }
        )

    # -----------------------------------------------------
    # 5. Ramp
    # -----------------------------------------------------
    if (
        details
        and
        details["ramps"]
    ):

        items.append(
            {
                "name":
                    "♿ منحدر",

                "points":
                    15,

                "status":
                    "confirmed",

                "reason":
                    "تم العثور على عنصر منحدر في الخريطة.",
            }
        )

    else:

        items.append(
            {
                "name":
                    "♿ منحدر",

                "points":
                    0,

                "status":
                    "unknown",

                "reason":
                    "لا توجد بيانات كافية عن المنحدرات.",
            }
        )

    # -----------------------------------------------------
    # 6. Indoor Data
    # -----------------------------------------------------
    if (
        details
        and
        (
            details["rooms"]
            or
            details["levels"]
        )
    ):

        items.append(
            {
                "name":
                    "🏢 معلومات داخلية",

                "points":
                    10,

                "status":
                    "confirmed",

                "reason":
                    "هناك عناصر داخلية أو طوابق مسجلة.",
            }
        )

    else:

        items.append(
            {
                "name":
                    "🏢 معلومات داخلية",

                "points":
                    0,

                "status":
                    "unknown",

                "reason":
                    "لا توجد خريطة داخلية كافية.",
            }
        )

    # -----------------------------------------------------
    # 7. Wheelchair Accessibility Tags
    # -----------------------------------------------------
    if (
        details
        and
        details[
            "wheelchair_features"
        ]
    ):

        items.append(
            {
                "name":
                    "♿ بيانات وصول إضافية",

                "points":
                    10,

                "status":
                    "confirmed",

                "reason":
                    "وجدت عناصر موسومة بإمكانية الوصول.",
            }
        )

    else:

        items.append(
            {
                "name":
                    "♿ بيانات وصول إضافية",

                "points":
                    0,

                "status":
                    "unknown",

                "reason":
                    "لا توجد وسوم وصول إضافية كافية.",
            }
        )

    score = sum(
        item["points"]
        for item in items
    )

    confirmed = sum(
        1
        for item in items
        if item["status"]
        == "confirmed"
    )

    unknown = sum(
        1
        for item in items
        if item["status"]
        == "unknown"
    )

    # -----------------------------------------------------
    # INTERPRETATION
    # -----------------------------------------------------
    if confirmed == 0:

        level = (
            "لا توجد أدلة كافية"
        )

    elif score >= 80:

        level = (
            "أدلة وصول قوية"
        )

    elif score >= 60:

        level = (
            "أدلة وصول جيدة"
        )

    elif score >= 40:

        level = (
            "أدلة وصول جزئية"
        )

    else:

        level = (
            "بيانات محدودة"
        )

    return {
        "score":
            score,

        "level":
            level,

        "confirmed":
            confirmed,

        "unknown":
            unknown,

        "items":
            items,
    }


# =========================================================
# AI CONTEXT
# =========================================================
def build_place_context(
    lat,
    lon,
    details,
    parking_results
):

    context = {

        "location":
            reverse_geocode(
                lat,
                lon
            ),

        "coordinates": {
            "latitude":
                lat,

            "longitude":
                lon,
        },
    }

    if details:

        building = details[
            "building"
        ]

        context[
            "openstreetmap"
        ] = {

            "building_name":
                get_name(
                    building["tags"],
                    "غير محدد"
                ),

            "tags":
                building["tags"],

            "distance_from_point_m":
                round(
                    details["distance"]
                ),

            "accessible_toilets":
                len(
                    details[
                        "accessible_toilets"
                    ]
                ),

            "elevators":
                len(
                    details[
                        "elevators"
                    ]
                ),

            "entrances":
                len(
                    details[
                        "entrances"
                    ]
                ),

            "accessible_entrances":
                len(
                    details[
                        "accessible_entrances"
                    ]
                ),

            "stairs":
                len(
                    details["stairs"]
                ),

            "ramps":
                len(
                    details["ramps"]
                ),

            "rooms":
                len(
                    details["rooms"]
                ),

            "levels":
                details["levels"],

            "wheelchair_features":
                len(
                    details[
                        "wheelchair_features"
                    ]
                ),
        }

    else:

        context[
            "openstreetmap"
        ] = (
            "لم يتم العثور على مبنى واضح "
            "في النقطة المحددة."
        )

    context[
        "nearby_accessible_parking"
    ] = [

        {
            "name":
                item["name"],

            "kind":
                item["kind"],

            "distance_m":
                round(
                    item["distance"]
                ),
        }

        for item
        in parking_results[:15]
    ]

    return context


# =========================================================
# AI
# =========================================================
def ask_verifyai(
    question,
    context,
    use_web=True
):

    if not ai_available():

        return (
            "الذكاء الاصطناعي غير متصل.\n\n"
            "أضف OPENAI_API_KEY في "
            "Streamlit Secrets."
        )

    if ai_remaining() <= 0:

        return (
            "وصلت إلى الحد الأقصى لطلبات "
            "الذكاء الاصطناعي في هذه الجلسة."
        )

    instructions = """
أنت VerifyAI Access.

أنت مساعد متخصص في:
- إمكانية الوصول
- التنقل لذوي الهمم
- الوصول داخل المباني
- المداخل المهيأة
- المصاعد
- الحمامات المهيأة
- مواقف ذوي الهمم
- المنحدرات

قواعدك:

1. لا تخترع معلومات.
2. لا تعتبر عدم وجود بيانات دليلًا على عدم وجود الخدمة.
3. OpenStreetMap قد يكون ناقصًا أو غير محدث.
4. إذا كانت البيانات ناقصة، استخدم Web Search عند توفره.
5. عند استخدام الويب، اعتمد على مصادر موثوقة.
6. اذكر مصدر المعلومة عندما يكون متاحًا.
7. فرّق بين:
   - مؤكد
   - مرجح
   - غير مؤكد
8. لا تعطِ شهادة رسمية للمبنى.
9. لا تدّعي أن المكان آمن أو مطابق للمعايير إلا بدليل رسمي.
10. الهدف هو مساعدة المستخدم على اتخاذ قرار أفضل.
11. أجب بالعربية.
12. اجعل الجواب واضحًا ومباشرًا.
"""

    prompt = f"""
بيانات المكان:

{json.dumps(
    context,
    ensure_ascii=False,
    indent=2
)}

سؤال المستخدم:

{question}

حلل البيانات الموجودة أولًا.

إذا كانت غير كافية وكان البحث على الويب متاحًا،
ابحث عن معلومات إضافية تخص المكان.

أجب بهذا الشكل:

الإجابة:
...

الثقة:
مؤكدة / مرجحة / غير مؤكدة

المصدر:
...

التحقق:
اذكر إذا كانت هناك حاجة للتحقق الميداني.
"""

    try:

        tools = []

        if use_web:

            tools = [
                {
                    "type":
                        "web_search",

                    "search_context_size":
                        "low",
                }
            ]

        response = (
            openai_client
            .responses
            .create(

                model=MODEL,

                instructions=instructions,

                input=[
                    {
                        "role":
                            "user",

                        "content":
                            prompt,
                    }
                ],

                tools=tools,

                max_output_tokens=900,
            )
        )

        st.session_state.ai_calls += 1

        text = getattr(
            response,
            "output_text",
            ""
        )

        if text:
            return text

        return (
            "لم أستطع الحصول على إجابة."
        )

    except Exception as error:

        st.session_state.ai_calls += 1

        return (
            "حدث خطأ أثناء تشغيل VerifyAI.\n\n"
            f"{str(error)[:500]}"
        )


# =========================================================
# AUTO AI
# =========================================================
def needs_ai(
    details,
    parking_results
):

    if not details:
        return True

    useful = any(
        [
            details["accessible_toilets"],
            details["elevators"],
            details["accessible_entrances"],
            details["ramps"],
            details["rooms"],
            details["levels"],
            details["wheelchair_features"],
            parking_results,
        ]
    )

    return not useful


def run_auto_ai(
    lat,
    lon,
    details,
    parking_results
):

    if st.session_state.auto_ai_checked:
        return

    st.session_state.auto_ai_checked = True

    if not AUTO_AI_SEARCH:
        return

    if not ai_available():
        return

    if ai_remaining() <= 0:
        return

    if not needs_ai(
        details,
        parking_results
    ):
        return

    context = build_place_context(
        lat,
        lon,
        details,
        parking_results
    )

    question = f"""
المعلومات المحلية عن هذا المكان ناقصة:

{context.get("location", "موقع غير معروف")}

ابحث على الويب عن معلومات موثوقة
حول إمكانية الوصول، وخصوصًا:

• المدخل المهيأ
• المصعد
• الحمام المهيأ
• موقف ذوي الهمم
• المنحدرات
• الوصول الداخلي

لا تخترع أي معلومة.
إذا لم تجد معلومة مناسبة، قل إنها غير مؤكدة.
"""

    st.session_state.auto_ai_answer = ask_verifyai(
        question,
        context,
        use_web=True
    )


# =========================================================
# MAP MARKERS
# =========================================================
def building_marker(
    map_object,
    details
):

    building = details[
        "building"
    ]

    lat, lon = building[
        "center"
    ]

    name = get_name(
        building["tags"],
        "المبنى"
    )

    icon = """
    <div style="
        width:50px;
        height:50px;
        background:#7657ff;
        border:5px solid white;
        border-radius:50%;
        box-shadow:0 4px 16px rgba(0,0,0,.35);
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:26px;
    ">
        🏢
    </div>
    """

    popup = f"""
    <div style="
        direction:rtl;
        font-family:Arial;
    ">

        <b>
            🏢 {html.escape(name)}
        </b>

        <hr>

        🚪 مداخل مهيأة:
        {len(details["accessible_entrances"])}

        <br>

        🛗 مصاعد:
        {len(details["elevators"])}

        <br>

        🚻 حمامات مهيأة:
        {len(details["accessible_toilets"])}

        <br>

        ♿ منحدرات:
        {len(details["ramps"])}

    </div>
    """

    folium.Marker(
        [lat, lon],

        tooltip=
            "🏢 "
            + name,

        popup=folium.Popup(
            popup,
            max_width=320
        ),

        icon=folium.DivIcon(
            html=icon
        ),
    ).add_to(
        map_object
    )


def parking_marker(
    map_object,
    parking,
    large=True
):

    lat, lon = parking[
        "center"
    ]

    size = (
        62
        if large
        else 48
    )

    font = (
        31
        if large
        else 24
    )

    icon = f"""
    <div style="
        width:{size}px;
        height:{size}px;
        background:#087cff;
        border:5px solid white;
        border-radius:50%;
        box-shadow:
            0 0 0 7px rgba(8,124,255,.28),
            0 5px 16px rgba(0,0,0,.35);
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:{font}px;
        color:white;
    ">
        ♿
    </div>
    """

    popup = f"""
    <div style="
        direction:rtl;
        font-family:Arial;
        min-width:220px;
    ">

        <b>
            🅿️ {html.escape(parking["name"])}
        </b>

        <hr>

        ♿ {html.escape(parking["kind"])}

        <br><br>

        📏 {int(parking["distance"])} متر

    </div>
    """

    folium.Marker(
        [lat, lon],

        tooltip=
            "🅿️ ♿ "
            + parking["name"],

        popup=folium.Popup(
            popup,
            max_width=320
        ),

        icon=folium.DivIcon(
            html=icon
        ),
    ).add_to(
        map_object
    )


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:

    st.markdown(
        """
        <div style="
            font-size:26px;
            font-weight:800;
            color:#7657ff;
            margin-bottom:20px;
        ">
            ♿ VerifyAI Access
        </div>
        """,
        unsafe_allow_html=True
    )

    st.session_state.page = st.radio(
        "التنقل",

        [
            "🗺️ الخريطة",
            "🅿️ مواقف ذوي الهمم"
        ],

        index=(
            0
            if st.session_state.page
            == "🗺️ الخريطة"
            else 1
        )
    )

    if ai_available():

        st.success(
            "🤖 VerifyAI متصل"
        )

        st.caption(
            f"طلبات AI المتبقية: "
            f"{ai_remaining()}"
        )

    else:

        st.warning(
            "🤖 VerifyAI غير متصل"
        )

    st.caption(
        "المصدر الأساسي: OpenStreetMap"
    )


# =========================================================
# MAIN MAP PAGE
# =========================================================
if st.session_state.page == "🗺️ الخريطة":

    st.markdown(
        '<div class="main-title">♿ VerifyAI Access</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="subtitle">
        خريطة وصول ذكية تساعدك على معرفة جاهزية
        المكان بالأدلة المتوفرة، مع AI للبحث
        عندما تكون البيانات ناقصة.
        </div>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # SEARCH
    # =====================================================
    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    query = st.text_input(
        "🔎 اسم المكان أو البناية",

        value=
            st.session_state.search_query,

        placeholder=
            "مثال: Red Sea Mall Jeddah",

        key="place_search"
    )

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "🔎 ابحث بالاسم",
            use_container_width=True,
        ):

            st.session_state.search_query = query

            st.session_state.search_results = (
                search_osm_places(
                    query
                )
            )

            st.session_state.search_index = 0

            if not st.session_state.search_results:

                st.warning(
                    "ما لقيت المكان."
                )

    with c2:

        if st.button(
            "📍 اختر الموقع يدويًا",
            use_container_width=True,
        ):

            st.session_state.manual_mode = True

    st.markdown(
        """
        <div class="hint">
        ♿ حمام • 🛗 مصعد • 🚪 مدخل •
        🅿️ موقف • ♿ منحدر •
        🤖 ذكاء اصطناعي • 📊 مؤشر وصول
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # SEARCH RESULTS
    # =====================================================
    if st.session_state.search_results:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        labels = [
            item.get(
                "display_name",
                "موقع"
            )

            for item
            in st.session_state.search_results
        ]

        index = min(
            st.session_state.search_index,
            len(labels) - 1
        )

        index = st.selectbox(
            "اختر النتيجة",
            range(len(labels)),

            index=index,

            format_func=lambda i:
                labels[i],

            key="place_result"
        )

        st.session_state.search_index = index

        chosen = (
            st.session_state
            .search_results[index]
        )

        chosen_lat = safe_float(
            chosen.get("lat")
        )

        chosen_lon = safe_float(
            chosen.get("lon")
        )

        if (
            chosen_lat is not None
            and
            chosen_lon is not None
            and
            st.button(
                "📍 استخدام هذا المكان",
                use_container_width=True,
            )
        ):

            set_center(
                chosen_lat,
                chosen_lon
            )

            st.session_state.manual_mode = False

            st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # MANUAL LOCATION
    # =====================================================
    lat, lon = (
        st.session_state.center
    )

    if st.session_state.manual_mode:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.info(
            "📍 اضغط على الخريطة لتحديد المكان."
        )

        manual_map = folium.Map(
            [lat, lon],
            zoom_start=15,
            control_scale=True
        )

        manual_result = st_folium(
            manual_map,
            width=None,
            height=500,

            key=(
                "manual_"
                + str(
                    st.session_state.map_key
                )
            )
        )

        manual_result = (
            manual_result
            or {}
        )

        clicked = manual_result.get(
            "last_clicked"
        )

        if clicked:

            set_center(
                clicked["lat"],
                clicked["lng"]
            )

            st.session_state.manual_mode = False

            st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # BUILDING
    # =====================================================
    if (
        st.session_state.building_details
        is None
    ):

        with st.spinner(
            "🔎 أحلل المكان..."
        ):

            st.session_state.building_details = (
                get_building_details(
                    lat,
                    lon,
                    500
                )
            )

    details = (
        st.session_state.building_details
    )


    # =====================================================
    # PARKING
    # =====================================================
    nearby_parking = get_accessible_parking(
        lat,
        lon,
        1800
    )


    # =====================================================
    # SCORE
    # =====================================================
    score_data = calculate_accessibility_score(
        details,
        nearby_parking
    )

    st.session_state.score_details = score_data


    # =====================================================
    # AUTO AI
    # =====================================================
    if (
        not st.session_state.auto_ai_checked
        and AUTO_AI_SEARCH
        and ai_available()
    ):

        with st.spinner(
            "🤖 البيانات ناقصة — VerifyAI يبحث عن أدلة إضافية..."
        ):

            run_auto_ai(
                lat,
                lon,
                details,
                nearby_parking
            )


    # =====================================================
    # SERVICES
    # =====================================================
    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### ♿ ماذا تريد أن تعرف؟"
    )

    options = [
        (
            "overview",
            "📊 المؤشر"
        ),

        (
            "toilet",
            "🚻 الحمام"
        ),

        (
            "elevator",
            "🛗 المصعد"
        ),

        (
            "entrance",
            "🚪 المدخل"
        ),

        (
            "parking",
            "🅿️ المواقف"
        ),

        (
            "ai",
            "🤖 اسأل AI"
        ),
    ]

    cols = st.columns(
        len(options)
    )

    for col, (key, label) in zip(
        cols,
        options
    ):

        with col:

            if st.button(
                label,
                use_container_width=True,
                key=f"service_{key}"
            ):

                st.session_state.service = key

                st.rerun()

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # MAP
    # =====================================================
    main_map = folium.Map(
        [lat, lon],
        zoom_start=16,
        control_scale=True
    )

    folium.Marker(
        [lat, lon],
        tooltip="📍 المكان المحدد",
        icon=folium.Icon(
            color="blue",
            icon="search"
        )
    ).add_to(
        main_map
    )

    if details:

        building_marker(
            main_map,
            details
        )

        polygon = (
            details[
                "building"
            ].get(
                "polygon"
            )
        )

        if polygon:

            folium.Polygon(
                polygon,

                color="#7657ff",

                fill=True,

                fill_color="#7657ff",

                fill_opacity=.10,

                weight=4
            ).add_to(
                main_map
            )


    # service markers
    if (
        details
        and
        st.session_state.service
        == "toilet"
    ):

        for item in details[
            "accessible_toilets"
        ]:

            folium.CircleMarker(
                item["center"],
                radius=11,
                color="#16a05c",
                fill=True,
                fill_color="#16a05c",
                fill_opacity=.95,

                tooltip=(
                    "🚻 حمام مهيأ — "
                    +
                    floor_label(
                        feature_level(
                            item["tags"]
                        )
                    )
                ),
            ).add_to(
                main_map
            )


    elif (
        details
        and
        st.session_state.service
        == "elevator"
    ):

        for item in details[
            "elevators"
        ]:

            folium.CircleMarker(
                item["center"],
                radius=11,
                color="#1677ff",
                fill=True,
                fill_color="#1677ff",
                fill_opacity=.95,

                tooltip=(
                    "🛗 مصعد — "
                    +
                    floor_label(
                        feature_level(
                            item["tags"]
                        )
                    )
                ),
            ).add_to(
                main_map
            )


    elif (
        details
        and
        st.session_state.service
        == "entrance"
    ):

        for item in details[
            "accessible_entrances"
        ]:

            folium.CircleMarker(
                item["center"],
                radius=10,
                color="#7657ff",
                fill=True,
                fill_color="#7657ff",
                fill_opacity=.95,

                tooltip="🚪 مدخل مهيأ",
            ).add_to(
                main_map
            )


    elif (
        details
        and
        st.session_state.service
        == "parking"
    ):

        for parking in nearby_parking[:30]:

            parking_marker(
                main_map,
                parking,
                True
            )


    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st_folium(
        main_map,
        width=None,
        height=620,

        key=(
            "main_map_"
            + str(
                st.session_state.map_key
            )
        )
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # ACCESSIBILITY SCORE
    # =====================================================
    if st.session_state.service == "overview":

        st.markdown(
            '<div class="score-card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### ♿ مؤشر الوصول الموثّق"
        )

        left, right = st.columns(
            [1, 3]
        )

        with left:

            st.markdown(
                f"""
                <div class="score-number">
                {score_data["score"]}
                </div>

                <div class="score-label">
                من 100
                </div>
                """,
                unsafe_allow_html=True
            )

        with right:

            st.markdown(
                f"""
                <span class="badge-purple">
                {html.escape(score_data["level"])}
                </span>
                """,
                unsafe_allow_html=True
            )

            st.write(
                f"✅ عناصر مؤكدة: "
                f"{score_data['confirmed']}"
            )

            st.write(
                f"❓ عناصر غير مؤكدة: "
                f"{score_data['unknown']}"
            )

        st.markdown(
            """
            <div class="hint">
            هذا المؤشر يقيس كمية الأدلة المسجلة عن
            الوصول الشامل، وليس شهادة رسمية بأن
            المبنى مطابق لجميع المعايير.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            "### 🔎 كيف حصل المكان على الدرجة؟"
        )

        for item in score_data["items"]:

            if item["status"] == "confirmed":

                st.markdown(
                    f"""
                    <div class="score-good">
                    <b>{item["name"]}</b>
                    <br>
                    +{item["points"]} نقطة
                    <br>
                    {html.escape(item["reason"])}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    f"""
                    <div class="score-unknown">
                    <b>{item["name"]}</b>
                    <br>
                    غير مؤكد
                    <br>
                    {html.escape(item["reason"])}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # TOILET
    # =====================================================
    elif st.session_state.service == "toilet":

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 🚻 حمامات ذوي الهمم"
        )

        if (
            details
            and
            details[
                "accessible_toilets"
            ]
        ):

            for item in details[
                "accessible_toilets"
            ]:

                st.success(
                    "🚻 حمام مهيأ — "
                    +
                    floor_label(
                        feature_level(
                            item["tags"]
                        )
                    )
                )

        else:

            st.warning(
                "لا توجد بيانات مؤكدة حاليًا "
                "عن حمام مهيأ."
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # ELEVATOR
    # =====================================================
    elif st.session_state.service == "elevator":

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 🛗 المصاعد"
        )

        if (
            details
            and
            details["elevators"]
        ):

            for item in details[
                "elevators"
            ]:

                st.success(
                    "🛗 مصعد — "
                    +
                    floor_label(
                        feature_level(
                            item["tags"]
                        )
                    )
                )

        else:

            st.info(
                "لا توجد بيانات مصعد مؤكدة."
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # ENTRANCE
    # =====================================================
    elif st.session_state.service == "entrance":

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 🚪 المداخل المهيأة"
        )

        if (
            details
            and
            details[
                "accessible_entrances"
            ]
        ):

            for item in details[
                "accessible_entrances"
            ]:

                st.success(
                    "🚪 مدخل مهيأ لذوي الهمم"
                )

        else:

            st.info(
                "لا توجد بيانات مؤكدة "
                "عن مدخل مهيأ."
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # PARKING
    # =====================================================
    elif st.session_state.service == "parking":

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 🅿️ مواقف ذوي الهمم"
        )

        if nearby_parking:

            for parking in nearby_parking[:30]:

                st.markdown(
                    f"""
                    <div class="parking-card">

                    <span class="badge-blue">
                    ♿ موقف مسجل
                    </span>

                    <div style="
                        font-size:18px;
                        font-weight:800;
                        color:#126ed8;
                        margin-top:10px;
                    ">
                    🅿️
                    {html.escape(parking["name"])}
                    </div>

                    <div style="
                        margin-top:8px;
                        color:#555;
                    ">
                    {html.escape(parking["kind"])}
                    <br>
                    📏 {int(parking["distance"])} متر
                    </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

        else:

            st.info(
                "لا توجد إحداثيات لمواقف مهيأة "
                "مسجلة حاليًا."
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # AI
    # =====================================================
    elif st.session_state.service == "ai":

        st.markdown(
            '<div class="ai-card">',
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="ai-header">
            🤖 اسأل VerifyAI
            </div>

            <div class="small-muted">
            إذا لم يجد الموقع بيانات كافية، يستطيع
            VerifyAI البحث عن معلومات إضافية من الويب.
            </div>
            """,
            unsafe_allow_html=True
        )

        if not ai_available():

            st.warning(
                "الـAI غير متصل."
            )

        else:

            st.caption(
                f"طلبات AI المتبقية: "
                f"{ai_remaining()}"
            )

            question = st.text_area(
                "💬 سؤالك",

                value=
                    st.session_state.ai_question,

                placeholder=
                    "مثال: هل يوجد مصعد في المكان؟",

                height=120,

                key="ai_question_box"
            )

            if st.button(
                "🤖 اسأل VerifyAI",
                use_container_width=True
            ):

                if not question.strip():

                    st.warning(
                        "اكتب سؤالك أولًا."
                    )

                else:

                    context = build_place_context(
                        lat,
                        lon,
                        details,
                        nearby_parking
                    )

                    with st.spinner(
                        "🤖 VerifyAI يبحث ويحلل..."
                    ):

                        answer = ask_verifyai(
                            question,
                            context,
                            use_web=True
                        )

                    st.session_state.ai_question = (
                        question
                    )

                    st.session_state.ai_answer = (
                        answer
                    )

            if st.session_state.ai_answer:

                st.markdown(
                    '<div class="ai-answer">',
                    unsafe_allow_html=True
                )

                st.markdown(
                    st.session_state.ai_answer
                )

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # AUTO AI RESULT
    # =====================================================
    if st.session_state.auto_ai_answer:

        st.markdown(
            '<div class="ai-card">',
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="ai-header">
            🤖 معلومات إضافية من VerifyAI
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="ai-answer">',
            unsafe_allow_html=True
        )

        st.markdown(
            st.session_state.auto_ai_answer
        )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

        st.caption(
            "هذه المعلومات المساعدة لا تغيّر المؤشر "
            "إلا عندما توجد بيانات خريطة موثقة."
        )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # ROUTING
    # =====================================================
    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 🧭 التنقل"
    )

    a, b, c = st.columns(3)

    with a:

        if st.button(
            "🟢 اختر البداية",
            use_container_width=True
        ):

            st.session_state.selection_mode = (
                "start"
            )

    with b:

        if st.button(
            "🔴 اختر الوجهة",
            use_container_width=True
        ):

            st.session_state.selection_mode = (
                "destination"
            )

    with c:

        if st.button(
            "🗑️ مسح المسار",
            use_container_width=True
        ):

            st.session_state.start_point = None
            st.session_state.destination_point = None
            st.session_state.route_result = None
            st.session_state.selection_mode = None

            st.rerun()


    # =====================================================
    # ROUTE SELECTION MAP
    # =====================================================
    if st.session_state.selection_mode:

        if (
            st.session_state.selection_mode
            == "start"
        ):

            st.info(
                "🟢 اضغط على الخريطة لتحديد البداية."
            )

        else:

            st.info(
                "🔴 اضغط على الخريطة لتحديد الوجهة."
            )

        route_map = folium.Map(
            [lat, lon],
            zoom_start=15,
            control_scale=True
        )

        if st.session_state.start_point:

            folium.Marker(
                st.session_state.start_point,
                tooltip="🟢 البداية",
                icon=folium.Icon(
                    color="green",
                    icon="play"
                )
            ).add_to(
                route_map
            )

        if st.session_state.destination_point:

            folium.Marker(
                st.session_state.destination_point,
                tooltip="🔴 الوجهة",
                icon=folium.Icon(
                    color="red",
                    icon="flag"
                )
            ).add_to(
                route_map
            )

        click_result = st_folium(
            route_map,
            width=None,
            height=450,

            key=(
                "route_map_"
                + str(
                    st.session_state.map_key
                )
                + "_"
                + str(
                    st.session_state.selection_mode
                )
            )
        )

        click_result = (
            click_result
            or {}
        )

        clicked = click_result.get(
            "last_clicked"
        )

        if clicked:

            point = (
                clicked["lat"],
                clicked["lng"]
            )

            if (
                st.session_state.selection_mode
                == "start"
            ):

                st.session_state.start_point = (
                    point
                )

            else:

                st.session_state.destination_point = (
                    point
                )

            st.session_state.selection_mode = None

            st.rerun()


    # =====================================================
    # ROUTE CALCULATION
    # =====================================================
    if (
        st.session_state.start_point
        and
        st.session_state.destination_point
    ):

        if st.button(
            "🚶 حساب المسار",
            use_container_width=True
        ):

            start = (
                st.session_state.start_point
            )

            destination = (
                st.session_state.destination_point
            )

            try:

                response = requests.get(
                    f"{OSRM_URL}/"
                    f"{start[1]},{start[0]};"
                    f"{destination[1]},{destination[0]}",

                    params={
                        "overview":
                            "full",

                        "geometries":
                            "geojson",

                        "steps":
                            "true",
                    },

                    headers=HEADERS,

                    timeout=30,
                )

                if response.ok:

                    routes = response.json().get(
                        "routes",
                        []
                    )

                    if routes:

                        st.session_state.route_result = (
                            routes[0]
                        )

                    else:

                        st.session_state.route_result = None

            except Exception:

                st.session_state.route_result = None


        if st.session_state.route_result:

            route = (
                st.session_state.route_result
            )

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "📏 المسافة",
                    (
                        f"{route.get('distance', 0) / 1000:.2f}"
                        " كم"
                    )
                )

            with col2:

                st.metric(
                    "⏱️ الوقت",
                    (
                        f"{route.get('duration', 0) / 60:.0f}"
                        " دقيقة"
                    )
                )

            geometry = (
                route.get(
                    "geometry",
                    {}
                )
            )

            coordinates = (
                geometry.get(
                    "coordinates",
                    []
                )
            )

            if coordinates:

                route_points = [
                    (
                        coordinate[1],
                        coordinate[0]
                    )

                    for coordinate
                    in coordinates
                ]

                route_display = folium.Map(
                    [lat, lon],
                    zoom_start=15,
                    control_scale=True
                )

                folium.PolyLine(
                    route_points,
                    weight=7,
                    opacity=.8,
                    color="#7657ff"
                ).add_to(
                    route_display
                )

                folium.Marker(
                    st.session_state.start_point,
                    tooltip="🟢 البداية",
                    icon=folium.Icon(
                        color="green",
                        icon="play"
                    )
                ).add_to(
                    route_display
                )

                folium.Marker(
                    st.session_state.destination_point,
                    tooltip="🔴 الوجهة",
                    icon=folium.Icon(
                        color="red",
                        icon="flag"
                    )
                ).add_to(
                    route_display
                )

                st_folium(
                    route_display,
                    width=None,
                    height=500,

                    key=(
                        "route_display_"
                        + str(
                            st.session_state.map_key
                        )
                    )
                )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


# =========================================================
# PARKING PAGE
# =========================================================
else:

    st.markdown(
        '<div class="main-title">🅿️ مواقف ذوي الهمم</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="subtitle">
        اعثر على المواقف المخصصة لذوي الهمم
        المسجلة على الخريطة.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    parking_query = st.text_input(
        "🔎 اسم المكان",

        value=
            st.session_state.parking_query,

        placeholder=
            "مثال: Red Sea Mall Jeddah",

        key="parking_search"
    )

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "🔎 بحث بالاسم",
            use_container_width=True
        ):

            st.session_state.parking_query = (
                parking_query
            )

            st.session_state.parking_results_search = (
                search_osm_places(
                    parking_query
                )
            )

            st.session_state.parking_search_index = 0

    with c2:

        if st.button(
            "📍 اختر الموقع يدويًا",
            use_container_width=True
        ):

            st.session_state.parking_manual_mode = True

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    if st.session_state.parking_results_search:

        labels = [
            item.get(
                "display_name",
                "موقع"
            )

            for item
            in st.session_state.parking_results_search
        ]

        index = min(
            st.session_state.parking_search_index,
            len(labels) - 1
        )

        index = st.selectbox(
            "اختر النتيجة",

            range(len(labels)),

            index=index,

            format_func=lambda i:
                labels[i],

            key="parking_result"
        )

        st.session_state.parking_search_index = index

        selected = (
            st.session_state
            .parking_results_search[index]
        )

        selected_lat = safe_float(
            selected.get("lat")
        )

        selected_lon = safe_float(
            selected.get("lon")
        )

        if (
            selected_lat is not None
            and
            selected_lon is not None
            and
            st.button(
                "📍 استخدام هذا المكان",
                use_container_width=True
            )
        ):

            st.session_state.parking_center = (
                selected_lat,
                selected_lon
            )

            st.session_state.parking_key = None

            st.rerun()


    plat, plon = (
        st.session_state.parking_center
    )


    radius_options = [
        500,
        1000,
        1800,
        2500,
        5000
    ]

    radius = st.selectbox(
        "📏 نطاق البحث",

        radius_options,

        index=radius_options.index(
            st.session_state.parking_radius
        ),

        format_func=lambda x:
            f"{x:,} متر"
    )

    if radius != st.session_state.parking_radius:

        st.session_state.parking_radius = radius
        st.session_state.parking_key = None


    parking_key = (
        round(plat, 5),
        round(plon, 5),
        radius
    )


    if (
        st.session_state.parking_key
        != parking_key
    ):

        with st.spinner(
            "🅿️ أبحث عن المواقف..."
        ):

            st.session_state.parking_results = (
                get_accessible_parking(
                    plat,
                    plon,
                    radius
                )
            )

        st.session_state.parking_key = parking_key


    spots = (
        st.session_state.parking_results
    )


    parking_map = folium.Map(
        [plat, plon],
        zoom_start=14,
        control_scale=True
    )

    folium.Marker(
        [plat, plon],
        tooltip="📍 مركز البحث",
        icon=folium.Icon(
            color="blue",
            icon="search"
        )
    ).add_to(
        parking_map
    )

    folium.Circle(
        [plat, plon],
        radius=radius,
        color="#087cff",
        fill=True,
        fill_opacity=.04
    ).add_to(
        parking_map
    )

    for parking in spots:

        parking_marker(
            parking_map,
            parking,
            True
        )


    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st_folium(
        parking_map,
        width=None,
        height=650,

        key=(
            "parking_map_"
            + str(
                st.session_state.map_key
            )
        )
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    st.markdown(
        f"### 🅿️ تم العثور على {len(spots)} موقفًا مسجلًا"
    )


    if spots:

        for i, parking in enumerate(
            spots
        ):

            st.markdown(
                f"""
                <div class="parking-card">

                <span class="badge-blue">
                ♿ موقف مسجل
                </span>

                <div style="
                    font-size:19px;
                    font-weight:800;
                    color:#126ed8;
                    margin-top:10px;
                ">
                🅿️
                {html.escape(parking["name"])}
                </div>

                <div style="
                    margin-top:8px;
                    color:#555;
                ">
                {html.escape(parking["kind"])}
                <br>
                📏 {int(parking["distance"])} متر
                </div>

                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(
                "📍 استخدم هذا الموقف كوجهة",
                key=f"parking_use_{i}",
                use_container_width=True
            ):

                st.session_state.destination_point = (
                    parking["center"]
                )

                st.session_state.center = (
                    parking["center"]
                )

                st.session_state.page = (
                    "🗺️ الخريطة"
                )

                st.rerun()

    else:

        st.info(
            "لا توجد إحداثيات لمواقف مهيأة "
            "ضمن نطاق البحث."
        )


# =========================================================
# FOOTER
# =========================================================
st.markdown(
    """
    <div class="footer">
    VerifyAI Access • Inclusive AI Navigation • Evidence-Based Accessibility
    </div>
    """,
    unsafe_allow_html=True
)
