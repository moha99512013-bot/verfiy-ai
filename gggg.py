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
# PAGE CONFIG
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
    "User-Agent": "VerifyAI-Access/13.0"
}

# يمكنك تغييره من Secrets
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")

# حد أقصى لطلبات AI داخل جلسة واحدة
MAX_AI_CALLS_PER_SESSION = 10

# البحث التلقائي على الويب فقط عندما تكون البيانات ناقصة
AUTO_AI_WEB_SEARCH = True


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


OPENAI_KEY = get_secret("OPENAI_API_KEY")


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

.footer {
    text-align: center;
    color: #888;
    font-size: 12px;
    margin-top: 30px;
}

.small-muted {
    color: #777;
    font-size: 13px;
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE
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

    "ai_calls": 0,
    "ai_answer": "",
    "ai_question": "",
    "ai_history": [],

    "auto_ai_checked": False,
    "auto_ai_answer": "",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# HELPERS
# =========================================================
def safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return 2 * R * math.asin(
        math.sqrt(a)
    )


def element_center(element):
    center = element.get("center")

    if center:
        lat = safe_float(center.get("lat"))
        lon = safe_float(center.get("lon"))

        if lat is not None and lon is not None:
            return lat, lon

    geometry = element.get(
        "geometry",
        []
    )

    if geometry:
        lats = [
            p["lat"]
            for p in geometry
            if "lat" in p
        ]

        lons = [
            p["lon"]
            for p in geometry
            if "lon" in p
        ]

        if lats and lons:
            return (
                sum(lats) / len(lats),
                sum(lons) / len(lons),
            )

    lat = safe_float(
        element.get("lat")
    )

    lon = safe_float(
        element.get("lon")
    )

    if lat is not None and lon is not None:
        return lat, lon

    return None


def point_in_polygon(lat, lon, poly):
    if not poly or len(poly) < 3:
        return False

    inside = False
    j = len(poly) - 1

    for i in range(len(poly)):
        yi, xi = poly[i]
        yj, xj = poly[j]

        if (xi > lon) != (xj > lon):

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
            return str(tags[key])

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


def get_name(tags, fallback="بدون اسم"):
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
        } & values
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


def set_center(lat, lon):
    st.session_state.center = (
        lat,
        lon
    )

    st.session_state.building_details = None
    st.session_state.service = "overview"

    st.session_state.ai_answer = ""
    st.session_state.ai_question = ""
    st.session_state.auto_ai_answer = ""
    st.session_state.auto_ai_checked = False

    st.session_state.map_key += 1


# =========================================================
# NOMINATIM
# =========================================================
@st.cache_data(
    ttl=120,
    show_spinner=False
)
def reverse_geocode(lat, lon):
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


@st.cache_data(
    ttl=120,
    show_spinner=False
)
def search_osm_places(query):
    if not query or not query.strip():
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
# BUILDING DATA
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
      nwr["amenity"="parking"](around:{radius},{lat},{lon});
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
                    and "lon" in point
                )
            ]

            buildings.append(
                {
                    "type": element.get("type"),
                    "id": element.get("id"),
                    "tags": tags,
                    "center": center,
                    "polygon": polygon,
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
                and point_in_polygon(
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

    distance = (
        0

        if (
            selected["polygon"]
            and point_in_polygon(
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

    if distance > 400:
        return None

    result = {
        "building": selected,
        "distance": distance,

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
            and point_in_polygon(
                feature["center"][0],
                feature["center"][1],
                selected["polygon"]
            )
        )

        near = (
            distance_m(
                *feature["center"],
                *selected["center"]
            ) <= 180
        )

        if not (
            inside
            or near
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

        if tags.get("amenity") == "toilets":

            result["toilets"].append(
                feature
            )

            if accessible_tag(
                tags
            ):
                result[
                    "accessible_toilets"
                ].append(feature)

        if (
            tags.get("elevator")
            or tags.get("indoor")
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
                    "accessible",
                }
            ):
                result[
                    "accessible_entrances"
                ].append(feature)

        if tags.get("highway") == "steps":
            result["stairs"].append(
                feature
            )

        if (
            tags.get("ramp")
            or tags.get("highway")
            == "incline"
        ):
            result["ramps"].append(
                feature
            )

        if (
            tags.get("room")
            or tags.get("indoor")
            == "room"
        ):
            result["rooms"].append(
                feature
            )

        if tags.get("wheelchair"):
            result[
                "wheelchair_features"
            ].append(feature)

    result["levels"] = sorted(
        result["levels"],
        key=lambda value: (
            safe_float(value, 999),
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
            or tags.get("disabled")
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
                "center": center,

                "tags": tags,

                "name": get_name(
                    tags,
                    "موقف ذوي الهمم"
                ),

                "kind": kind,

                "distance": distance_m(
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
# ROUTING
# =========================================================
def get_routes(start, destination):

    if (
        not start
        or not destination
    ):
        return []

    url = (
        f"{OSRM_URL}/"
        f"{start[1]},{start[0]};"
        f"{destination[1]},{destination[0]}"
    )

    try:

        response = requests.get(
            url,

            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "true",
                "alternatives": "true",
            },

            headers=HEADERS,
            timeout=30,
        )

        if response.ok:
            return response.json().get(
                "routes",
                []
            )

    except Exception:
        pass

    return []


def route_score(route):
    return (
        route.get("distance", 0)
        + 0.5
        * route.get("duration", 0)
    )


# =========================================================
# MAP MARKERS
# =========================================================
def parking_marker(
    map_object,
    parking,
    large=True
):

    lat, lon = parking["center"]

    size = 62 if large else 48
    font = 31 if large else 24

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

        <b style="font-size:17px">
            🅿️ {html.escape(parking["name"])}
        </b>

        <hr>

        ♿ {html.escape(parking["kind"])}

        <br><br>

        📏 {int(parking["distance"])}
        متر من مركز البحث

    </div>
    """

    folium.CircleMarker(
        [lat, lon],
        radius=32 if large else 25,
        color="#087cff",
        fill=True,
        fill_color="#087cff",
        fill_opacity=.18,
        weight=3,
    ).add_to(map_object)

    folium.Marker(
        [lat, lon],

        tooltip=(
            "🅿️ ♿ "
            + parking["name"]
        ),

        popup=folium.Popup(
            popup,
            max_width=320
        ),

        icon=folium.DivIcon(
            html=icon
        ),
    ).add_to(map_object)


def building_marker(
    map_object,
    details
):

    building = details["building"]

    lat, lon = building["center"]

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
        box-shadow:
            0 4px 16px rgba(0,0,0,.35);
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

        🚻 حمامات مهيأة:
        {len(details["accessible_toilets"])}

        <br>

        🛗 مصاعد:
        {len(details["elevators"])}

        <br>

        🚪 مداخل:
        {len(details["entrances"])}

        <br>

        🪜 درج:
        {len(details["stairs"])}

    </div>
    """

    folium.Marker(
        [lat, lon],

        tooltip=(
            "🏢 "
            + name
        ),

        popup=folium.Popup(
            popup,
            max_width=320
        ),

        icon=folium.DivIcon(
            html=icon
        ),
    ).add_to(map_object)


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
        "address":
            reverse_geocode(
                lat,
                lon
            ),

        "coordinates": {
            "latitude": lat,
            "longitude": lon,
        },
    }

    if details:

        building = details[
            "building"
        ]

        context[
            "openstreetmap_building"
        ] = {

            "name":
                get_name(
                    building["tags"],
                    "غير محدد"
                ),

            "tags":
                building["tags"],

            "distance_from_selected_point":
                round(
                    details["distance"]
                ),

            "accessible_toilets":
                len(
                    details[
                        "accessible_toilets"
                    ]
                ),

            "all_toilets":
                len(
                    details[
                        "toilets"
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
        }

    else:

        context[
            "openstreetmap_building"
        ] = "لم يتم العثور على مبنى واضح في النقطة المحددة."

    context[
        "nearby_accessible_parking"
    ] = [
        {
            "name": item["name"],
            "kind": item["kind"],
            "distance_m":
                round(
                    item["distance"]
                ),
        }

        for item in parking_results[:15]
    ]

    return context


# =========================================================
# AI CALL
# =========================================================
def ask_verifyai(
    question,
    place_context,
    web_search=True
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

    system_prompt = """
أنت VerifyAI Access، مساعد ذكاء اصطناعي
للوصول الشامل والتنقل للأشخاص ذوي الهمم.

وظيفتك المساعدة في معرفة:

• المداخل المهيأة
• المصاعد
• الحمامات المهيأة
• مواقف ذوي الهمم
• المنحدرات
• الوصول داخل المباني
• المعلومات العامة عن إمكانية الوصول

قواعد صارمة:

1. لا تخترع أي معلومة.
2. إذا لم توجد بيانات كافية، قل:
   "غير مؤكد".
3. لا تعتبر غياب المعلومة دليلًا على عدم وجود الشيء.
4. بيانات OpenStreetMap قد تكون ناقصة أو قديمة.
5. إذا كان السؤال عن مكان محدد وكانت البيانات ناقصة،
   استخدم البحث على الويب إذا كان متاحًا.
6. عند استخدام الويب، اعتمد على صفحات موثوقة قدر الإمكان.
7. لا تقل "يوجد" إلا عندما يوجد دليل مناسب.
8. لا تقل "لا يوجد" فقط لأن OpenStreetMap لا يحتوي على المعلومة.
9. أعط المستخدم درجة ثقة:
   مؤكدة / مرجحة / غير مؤكدة.
10. اذكر المصدر أو اسم الموقع عندما يكون ذلك متاحًا.
11. إذا لم تجد شيئًا موثوقًا، قل ذلك بوضوح.
12. لا تدّعي وجود خريطة داخلية إذا لم تتوفر بيانات داخلية.
13. أجب بالعربية.
14. اجعل الإجابة سهلة وسريعة.
15. ركز على إمكانية الوصول فقط.
"""

    user_prompt = f"""
هذه بيانات المكان الحالية:

{json.dumps(
    place_context,
    ensure_ascii=False,
    indent=2
)}

سؤال المستخدم:

{question}

حلل بيانات OpenStreetMap أولًا.

إذا كانت البيانات غير كافية وكان البحث على الويب
مفعّلًا، ابحث عن معلومات إضافية مرتبطة بالمكان.

في النهاية قدم:

الإجابة:
...

درجة الثقة:
مؤكدة / مرجحة / غير مؤكدة

المصدر:
...

ملاحظة:
اذكر بوضوح إذا كانت المعلومة تحتاج تحققًا ميدانيًا.
"""

    try:

        tools = []

        if web_search:
            tools = [
                {
                    "type": "web_search",
                    "search_context_size": "low",
                }
            ]

        response = openai_client.responses.create(

            model=MODEL,

            instructions=system_prompt,

            input=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],

            tools=tools,

            max_output_tokens=900,
        )

        st.session_state.ai_calls += 1

        answer = getattr(
            response,
            "output_text",
            ""
        )

        if answer:
            return answer

        return (
            "لم أستطع الحصول على إجابة من VerifyAI."
        )

    except Exception as error:

        st.session_state.ai_calls += 1

        return (
            "حدث خطأ أثناء تشغيل VerifyAI.\n\n"
            f"التفاصيل التقنية: "
            f"{str(error)[:500]}"
        )


# =========================================================
# SHOULD AUTO SEARCH?
# =========================================================
def needs_ai_web_search(
    details,
    parking_results
):

    # لا يوجد مبنى
    if not details:
        return True

    has_useful_building_data = any(
        [
            len(
                details[
                    "accessible_toilets"
                ]
            ) > 0,

            len(
                details[
                    "elevators"
                ]
            ) > 0,

            len(
                details[
                    "accessible_entrances"
                ]
            ) > 0,

            len(
                details[
                    "ramps"
                ]
            ) > 0,

            len(
                details[
                    "rooms"
                ]
            ) > 0,

            len(
                details[
                    "levels"
                ]
            ) > 0,
        ]
    )

    if not has_useful_building_data:
        return True

    return False


# =========================================================
# AUTO AI SEARCH
# =========================================================
def run_auto_ai(
    lat,
    lon,
    details,
    parking_results
):

    if st.session_state.auto_ai_checked:
        return

    st.session_state.auto_ai_checked = True

    if not AUTO_AI_WEB_SEARCH:
        return

    if not ai_available():
        return

    if ai_remaining() <= 0:
        return

    if not needs_ai_web_search(
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

    place_name = context.get(
        "address",
        "المكان المحدد"
    )

    question = f"""
أريد منك التحقق من معلومات إمكانية الوصول
للمكان التالي:

{place_name}

بيانات OpenStreetMap المحلية غير كافية.

ابحث عن معلومات موثوقة عن:

1. مدخل مهيأ للكراسي المتحركة
2. مصعد
3. حمام مهيأ
4. مواقف ذوي الهمم
5. منحدرات
6. إمكانية الوصول داخل المبنى

إذا لم تجد دليلًا موثوقًا على أي نقطة،
قل إنها غير مؤكدة.
"""

    st.session_state.auto_ai_answer = ask_verifyai(
        question,
        context,
        web_search=True
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
        "المصدر الأساسي للمعلومات: "
        "OpenStreetMap"
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
        اختر المكان أولًا، ثم اكتشف خدمات الوصول،
        وإذا كانت المعلومات ناقصة يساعدك VerifyAI
        في البحث عنها.
        </div>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # SEARCH CARD
    # =====================================================
    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    query = st.text_input(
        "🔎 اسم المكان أو البناية",
        value=st.session_state.search_query,
        placeholder="مثال: Red Sea Mall Jeddah",
        key="place_search",
    )

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "🔎 ابحث بالاسم",
            use_container_width=True,
        ):

            st.session_state.search_query = query

            st.session_state.search_results = (
                search_osm_places(query)
            )

            st.session_state.search_index = 0

            if not st.session_state.search_results:

                st.warning(
                    "ما لقيت المكان في OpenStreetMap."
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
        ♿ الخدمات:
        🚻 حمام مهيأ •
        🛗 مصعد •
        🚪 مدخل مهيأ •
        🅿️ موقف ذوي الهمم •
        🤖 بحث AI عند نقص البيانات
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
            result.get(
                "display_name",
                "موقع"
            )

            for result
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
            st.session_state.search_results[
                index
            ]
        )

        chosen_lat = safe_float(
            chosen.get("lat")
        )

        chosen_lon = safe_float(
            chosen.get("lon")
        )

        if (
            chosen_lat is not None
            and chosen_lon is not None
            and st.button(
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
    lat, lon = st.session_state.center

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

        folium.Marker(
            [lat, lon],
            tooltip="المركز الحالي",
            icon=folium.Icon(
                color="blue",
                icon="crosshairs"
            )
        ).add_to(manual_map)

        manual_result = st_folium(
            manual_map,
            width=None,
            height=500,
            key=(
                "manual_main_"
                + str(
                    st.session_state.map_key
                )
            ),
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
    # LOAD BUILDING
    # =====================================================
    if (
        st.session_state.building_details
        is None
    ):

        with st.spinner(
            "🔎 أبحث عن معلومات المكان..."
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
    # AUTO AI SEARCH
    # =====================================================
    if (
        not st.session_state.auto_ai_checked
        and AUTO_AI_WEB_SEARCH
        and ai_available()
    ):

        with st.spinner(
            "🤖 البيانات ناقصة — VerifyAI يبحث عن معلومات إضافية..."
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
            "📋 نظرة عامة"
        ),
        (
            "toilet",
            "🚻 حمام ذوي الهمم"
        ),
        (
            "elevator",
            "🛗 مصعد"
        ),
        (
            "entrance",
            "🚪 مدخل مهيأ"
        ),
        (
            "parking",
            "🅿️ موقف ذوي الهمم"
        ),
        (
            "ai",
            "🤖 اسأل AI"
        ),
    ]

    columns = st.columns(
        len(options)
    )

    for column, (key, label) in zip(
        columns,
        options
    ):

        with column:

            if st.button(
                label,
                use_container_width=True,
                key=f"service_{key}",
            ):

                st.session_state.service = key

                st.rerun()

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # MAIN MAP
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
    ).add_to(main_map)


    if details:

        building_marker(
            main_map,
            details
        )

        polygon = (
            details["building"]
            .get("polygon")
        )

        if polygon:

            folium.Polygon(
                polygon,
                color="#7657ff",
                fill=True,
                fill_color="#7657ff",
                fill_opacity=.10,
                weight=4
            ).add_to(main_map)


    # =====================================================
    # SERVICE MARKERS
    # =====================================================
    if (
        details
        and st.session_state.service
        == "toilet"
    ):

        for item in details[
            "accessible_toilets"
        ]:

            tags = item["tags"]

            folium.CircleMarker(
                item["center"],
                radius=11,
                color="#16a05c",
                fill=True,
                fill_color="#16a05c",
                fill_opacity=.95,

                tooltip=(
                    "🚻 حمام مهيأ — "
                    + floor_label(
                        feature_level(tags)
                    )
                ),
            ).add_to(main_map)


    elif (
        details
        and st.session_state.service
        == "elevator"
    ):

        for item in details[
            "elevators"
        ]:

            tags = item["tags"]

            folium.CircleMarker(
                item["center"],
                radius=11,
                color="#1677ff",
                fill=True,
                fill_color="#1677ff",
                fill_opacity=.95,

                tooltip=(
                    "🛗 مصعد — "
                    + floor_label(
                        feature_level(tags)
                    )
                ),
            ).add_to(main_map)


    elif (
        details
        and st.session_state.service
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
            ).add_to(main_map)


    elif (
        st.session_state.service
        == "parking"
    ):

        for parking in nearby_parking[:30]:

            parking_marker(
                main_map,
                parking,
                True
            )


    # =====================================================
    # DISPLAY MAP
    # =====================================================
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
        ),
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # OVERVIEW
    # =====================================================
    if st.session_state.service == "overview":

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        if details:

            name = get_name(
                details["building"]["tags"],
                "المكان المحدد"
            )

            st.markdown(
                f"""
                <span class="badge-purple">
                🏢 {html.escape(name)}
                </span>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                "### الخدمات المسجلة"
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "🚻 حمام مهيأ",
                len(
                    details[
                        "accessible_toilets"
                    ]
                )
            )

            col2.metric(
                "🛗 مصاعد",
                len(
                    details["elevators"]
                )
            )

            col3.metric(
                "🚪 مداخل مهيأة",
                len(
                    details[
                        "accessible_entrances"
                    ]
                )
            )

            col4.metric(
                "🪜 درج",
                len(
                    details["stairs"]
                )
            )

        else:

            st.info(
                "لم أجد معلومات داخلية واضحة "
                "لهذا الموقع."
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
            and details[
                "accessible_toilets"
            ]
        ):

            for item in details[
                "accessible_toilets"
            ]:

                st.success(
                    "🚻 حمام مهيأ لذوي الهمم — "
                    + floor_label(
                        feature_level(
                            item["tags"]
                        )
                    )
                )

        else:

            st.warning(
                "لا توجد بيانات مؤكدة حاليًا "
                "عن حمام مهيأ لهذا المكان."
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
            and details["elevators"]
        ):

            for item in details[
                "elevators"
            ]:

                st.success(
                    "🛗 مصعد — "
                    + floor_label(
                        feature_level(
                            item["tags"]
                        )
                    )
                )

        else:

            st.info(
                "لا توجد بيانات مصعد مسجلة "
                "لهذا المكان."
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
            and details[
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
                        ♿ موقف ذوي الهمم
                        </span>

                        <div style="
                            font-size:18px;
                            font-weight:800;
                            color:#126ed8;
                            margin-top:10px;
                        ">
                            🅿️
                            {html.escape(
                                parking["name"]
                            )}
                        </div>

                        <div style="
                            color:#555;
                            margin-top:8px;
                        ">
                            {html.escape(
                                parking["kind"]
                            )}

                            <br>

                            📏
                            {int(
                                parking["distance"]
                            )}
                            متر
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if st.button(
                    "📍 اجعل هذا الموقف وجهتي",
                    key=(
                        "main_spot_"
                        + str(
                            parking["center"][0]
                        )
                        + "_"
                        + str(
                            parking["center"][1]
                        )
                    ),
                    use_container_width=True,
                ):

                    st.session_state.destination_point = (
                        parking["center"]
                    )

                    st.success(
                        "تم اختيار الموقف كوجهة."
                    )

        else:

            st.info(
                "لا توجد إحداثيات لمواقف مهيأة "
                "مسجلة حاليًا في OpenStreetMap."
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
            اسأل عن إمكانية الوصول في المكان المحدد.
            إذا كانت الخريطة لا تحتوي على المعلومة،
            يستطيع VerifyAI محاولة البحث عنها على الويب.
            </div>
            """,
            unsafe_allow_html=True
        )

        if not ai_available():

            st.warning(
                "الـAI غير متصل. "
                "أضف OPENAI_API_KEY في Secrets."
            )

        else:

            st.caption(
                f"طلبات AI المتبقية: "
                f"{ai_remaining()}"
            )

            question = st.text_area(
                "💬 سؤالك",
                value=st.session_state.ai_question,
                placeholder=(
                    "مثال:\n"
                    "هل يوجد مصعد؟\n"
                    "هل يوجد حمام لذوي الهمم؟\n"
                    "هل للمبنى مدخل مناسب للكراسي؟\n"
                    "هل يوجد موقف مخصص قريب؟"
                ),
                height=130,
                key="ai_question_box",
            )

            if st.button(
                "🤖 اسأل VerifyAI",
                use_container_width=True,
            ):

                if not question.strip():

                    st.warning(
                        "اكتب سؤالك أولًا."
                    )

                elif ai_remaining() <= 0:

                    st.error(
                        "انتهت طلبات AI لهذه الجلسة."
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
                            web_search=True
                        )

                    st.session_state.ai_question = question
                    st.session_state.ai_answer = answer

                    st.session_state.ai_history.append(
                        {
                            "question": question,
                            "answer": answer,
                        }
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
            🤖 معلومات إضافية وجدها VerifyAI
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
            "هذه المعلومات مساعدة وليست ضمانًا "
            "ميدانيًا لإمكانية الوصول."
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

    r1, r2, r3 = st.columns(3)

    with r1:

        if st.button(
            "🟢 اختر البداية",
            use_container_width=True,
        ):

            st.session_state.selection_mode = "start"

    with r2:

        if st.button(
            "🔴 اختر الوجهة",
            use_container_width=True,
        ):

            st.session_state.selection_mode = (
                "destination"
            )

    with r3:

        if st.button(
            "🗑️ مسح المسار",
            use_container_width=True,
        ):

            st.session_state.start_point = None
            st.session_state.destination_point = None
            st.session_state.route_result = None
            st.session_state.selection_mode = None

            st.rerun()


    # =====================================================
    # ROUTE POINT SELECTION MAP
    # =====================================================
    if st.session_state.selection_mode:

        if (
            st.session_state.selection_mode
            == "start"
        ):

            st.info(
                "🟢 اضغط على الخريطة أدناه "
                "لتحديد نقطة البداية."
            )

        else:

            st.info(
                "🔴 اضغط على الخريطة أدناه "
                "لتحديد الوجهة."
            )

        route_select_map = folium.Map(
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
                route_select_map
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
                route_select_map
            )

        route_click_result = st_folium(
            route_select_map,
            width=None,
            height=450,
            key=(
                "route_select_"
                + str(
                    st.session_state.map_key
                )
                + "_"
                + str(
                    st.session_state.selection_mode
                )
            ),
        )

        route_click_result = (
            route_click_result
            or {}
        )

        clicked = route_click_result.get(
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

                st.session_state.start_point = point

            else:

                st.session_state.destination_point = point

            st.session_state.selection_mode = None

            st.rerun()


    # =====================================================
    # ROUTE STATUS
    # =====================================================
    if st.session_state.start_point:

        st.write(
            "🟢 البداية: "
            f"{st.session_state.start_point[0]:.5f}, "
            f"{st.session_state.start_point[1]:.5f}"
        )

    if st.session_state.destination_point:

        st.write(
            "🔴 الوجهة: "
            f"{st.session_state.destination_point[0]:.5f}, "
            f"{st.session_state.destination_point[1]:.5f}"
        )


    if (
        st.session_state.start_point
        and st.session_state.destination_point
    ):

        if st.button(
            "🚶 حساب المسار",
            use_container_width=True,
        ):

            with st.spinner(
                "جاري حساب المسار..."
            ):

                routes = get_routes(
                    st.session_state.start_point,
                    st.session_state.destination_point,
                )

            if routes:

                st.session_state.route_result = (
                    sorted(
                        routes,
                        key=route_score
                    )[0]
                )

            else:

                st.session_state.route_result = None

                st.warning(
                    "لم أستطع حساب المسار."
                )

        route = (
            st.session_state.route_result
        )

        if route:

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
        ابحث عن مكان، ثم اعرض المواقف المهيأة
        المسجلة في OpenStreetMap.
        </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # PARKING SEARCH
    # =====================================================
    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    parking_query = st.text_input(
        "🔎 اسم المكان",
        value=st.session_state.parking_query,
        placeholder="مثال: Red Sea Mall Jeddah",
        key="parking_search"
    )

    p1, p2 = st.columns(2)

    with p1:

        if st.button(
            "🔎 بحث بالاسم",
            use_container_width=True,
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

            if not st.session_state.parking_results_search:

                st.warning(
                    "ما لقيت المكان."
                )

    with p2:

        if st.button(
            "📍 اختر الموقع يدويًا",
            use_container_width=True,
        ):

            st.session_state.parking_manual_mode = True

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # PARKING SEARCH RESULTS
    # =====================================================
    if st.session_state.parking_results_search:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        labels = [
            result.get(
                "display_name",
                "موقع"
            )

            for result
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

        chosen = (
            st.session_state
            .parking_results_search[index]
        )

        parking_lat = safe_float(
            chosen.get("lat")
        )

        parking_lon = safe_float(
            chosen.get("lon")
        )

        if (
            parking_lat is not None
            and parking_lon is not None
            and st.button(
                "📍 استخدام هذا المكان",
                use_container_width=True,
            )
        ):

            st.session_state.parking_center = (
                parking_lat,
                parking_lon
            )

            st.session_state.parking_key = None

            st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # PARKING MANUAL LOCATION
    # =====================================================
    plat, plon = (
        st.session_state.parking_center
    )

    if st.session_state.parking_manual_mode:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        parking_manual_map = folium.Map(
            [plat, plon],
            zoom_start=15,
            control_scale=True
        )

        result = st_folium(
            parking_manual_map,
            width=None,
            height=500,
            key=(
                "parking_manual_"
                + str(
                    st.session_state.map_key
                )
            ),
        )

        result = result or {}

        clicked = result.get(
            "last_clicked"
        )

        if clicked:

            st.session_state.parking_center = (
                clicked["lat"],
                clicked["lng"]
            )

            st.session_state.parking_manual_mode = False
            st.session_state.parking_key = None

            st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # RADIUS
    # =====================================================
    radius_options = [
        500,
        1000,
        1800,
        2500,
        5000
    ]

    parking_radius = st.selectbox(
        "📏 نطاق البحث",
        radius_options,

        index=radius_options.index(
            st.session_state.parking_radius
        ),

        format_func=lambda x:
            f"{x:,} متر"
    )

    if (
        parking_radius
        != st.session_state.parking_radius
    ):

        st.session_state.parking_radius = (
            parking_radius
        )

        st.session_state.parking_key = None


    parking_key = (
        round(plat, 5),
        round(plon, 5),
        parking_radius
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
                    parking_radius
                )
            )

        st.session_state.parking_key = (
            parking_key
        )


    parking_spots = (
        st.session_state.parking_results
    )


    # =====================================================
    # PARKING MAP
    # =====================================================
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
    ).add_to(parking_map)

    folium.Circle(
        [plat, plon],
        radius=parking_radius,
        color="#087cff",
        fill=True,
        fill_opacity=.04
    ).add_to(parking_map)

    for parking in parking_spots:

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
            "parking_main_"
            + str(
                st.session_state.map_key
            )
        ),
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    st.markdown(
        f"### 🅿️ تم العثور على {len(parking_spots)} موقفًا مسجلًا"
    )


    # =====================================================
    # PARKING LIST
    # =====================================================
    if parking_spots:

        for i, parking in enumerate(
            parking_spots
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
                        {html.escape(
                            parking["name"]
                        )}
                    </div>

                    <div style="
                        margin-top:8px;
                        color:#555;
                    ">
                        {html.escape(
                            parking["kind"]
                        )}

                        <br>

                        📏
                        {int(
                            parking["distance"]
                        )}
                        متر
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(
                "📍 استخدم هذا الموقف كوجهة",
                key=f"parking_use_{i}",
                use_container_width=True,
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

                st.success(
                    "تم اختيار الموقف كوجهة."
                )

                st.rerun()

    else:

        st.info(
            "لا توجد إحداثيات لمواقف مهيأة "
            "مسجلة ضمن النطاق. هذا لا يعني "
            "بالضرورة عدم وجود المواقف؛ قد تكون "
            "غير مسجلة في OpenStreetMap."
        )


# =========================================================
# FOOTER
# =========================================================
st.markdown(
    """
    <div class="footer">
    VerifyAI Access • Inclusive AI Navigation
    </div>
    """,
    unsafe_allow_html=True
)
