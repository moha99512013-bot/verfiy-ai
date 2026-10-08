import os
import math
import html
from urllib.parse import quote

import requests
import streamlit as st
import folium
from streamlit_folium import st_folium


# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="VerifyAI Access",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OSRM_URL = "https://router.project-osrm.org/route/v1/foot"

HEADERS = {
    "User-Agent": "VerifyAI-Access/10.0"
}


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
        padding-top: 1.3rem;
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
        margin-bottom: 20px;
    }

    .card {
        background: white;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 5px 25px rgba(60, 40, 120, 0.08);
        border: 1px solid #ebe7ff;
        margin-bottom: 16px;
    }

    .feature-card {
        background: #ffffff;
        border-radius: 18px;
        padding: 16px;
        border: 1px solid #e9e5ff;
        margin-bottom: 10px;
    }

    .parking-card {
        background: white;
        border-radius: 18px;
        padding: 18px;
        border: 2px solid #d6e8ff;
        box-shadow: 0 5px 20px rgba(35, 105, 180, 0.08);
        margin-bottom: 12px;
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
        background: #1677ff;
        color: white;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
    }

    .feature-title {
        font-size: 18px;
        font-weight: 800;
        color: #24194e;
        margin-top: 8px;
    }

    .info-line {
        margin: 7px 0;
        color: #555;
    }

    .search-hint {
        background: #f7f4ff;
        border: 1px solid #ded5ff;
        border-radius: 14px;
        padding: 13px 15px;
        color: #44356e;
        margin-top: 10px;
    }

    .parking-title {
        color: #126ed8;
        font-size: 18px;
        font-weight: 800;
    }

    .footer {
        text-align: center;
        color: #888;
        font-size: 12px;
        margin-top: 30px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "page": "🗺️ الخريطة",

    # Search
    "search_query": "",
    "search_results": [],
    "selected_search_result": 0,
    "search_center": (21.5433, 39.1728),
    "manual_search_mode": False,

    # Building
    "selected_building": None,
    "building_details": None,
    "building_context_key": None,
    "indoor_mode": False,
    "selected_floor": None,

    # Main route
    "selection_mode": None,
    "start_point": None,
    "destination_point": None,
    "route_result": None,

    # Parking page
    "parking_search_query": "",
    "parking_search_results": [],
    "parking_selected_search_result": 0,
    "parking_center": (21.5433, 39.1728),
    "parking_manual_mode": False,
    "parking_radius": 2500,
    "parking_results": [],
    "parking_loaded_key": None,

    "map_key": 0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# BASIC HELPERS
# =========================================================

def safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def distance_meters(lat1, lon1, lat2, lon2):
    earth_radius = 6371000.0

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

    return (
        2
        * earth_radius
        * math.asin(math.sqrt(a))
    )


def point_in_polygon(lat, lon, polygon):
    if not polygon or len(polygon) < 3:
        return False

    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):
        yi, xi = polygon[i]
        yj, xj = polygon[j]

        if (xi > lon) != (xj > lon):
            denominator = (xj - xi) or 1e-12

            cross_lat = (
                (yj - yi)
                * (lon - xi)
                / denominator
                + yi
            )

            if lat < cross_lat:
                inside = not inside

        j = i

    return inside


def element_center(element):
    center = element.get("center")

    if center:
        lat = safe_float(center.get("lat"))
        lon = safe_float(center.get("lon"))

        if lat is not None and lon is not None:
            return lat, lon

    geometry = element.get("geometry", [])

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
                sum(lons) / len(lons)
            )

    lat = safe_float(element.get("lat"))
    lon = safe_float(element.get("lon"))

    if lat is not None and lon is not None:
        return lat, lon

    return None


def feature_level(tags):
    value = (
        tags.get("level")
        or tags.get("level:ref")
        or tags.get("floor")
        or tags.get("addr:floor")
    )

    if value is None:
        return None

    return str(value)


def format_floor(level):
    if level is None:
        return "الطابق غير محدد"

    value = str(level).strip()

    if ";" in value:
        parts = [
            p.strip()
            for p in value.split(";")
            if p.strip()
        ]

        return "الأدوار: " + "، ".join(
            format_floor(p).replace("الدور ", "")
            for p in parts
        )

    ordinals = {
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

    if value in ordinals:
        return ordinals[value]

    return f"الطابق {value}"


def is_accessible(tags):
    values = {
        str(tags.get("wheelchair", "")).lower(),
        str(tags.get("toilets:wheelchair", "")).lower(),
    }

    return bool(
        {"yes", "designated", "accessible"} & values
    )


def get_name(tags, default="بدون اسم"):
    for key in (
        "name:ar",
        "name",
        "official_name",
        "brand",
        "operator",
    ):
        if tags.get(key):
            return tags[key]

    return default


def building_image_url(tags):
    direct = (
        tags.get("image")
        or tags.get("image:url")
        or tags.get("image_url")
    )

    if direct and str(direct).startswith("http"):
        return str(direct)

    commons = tags.get("wikimedia_commons")

    if commons:
        value = str(commons).strip()

        if value.startswith("File:"):
            filename = value[5:].strip()

            return (
                "https://commons.wikimedia.org/wiki/"
                "Special:FilePath/"
                + quote(filename.replace(" ", "_"))
            )

    return None


# =========================================================
# GEOCODING
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
def search_places(query):

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
# BUILDING DETAILS
# =========================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
def get_building_details(
    lat,
    lon,
    radius=300
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
    );

    out body geom center;
    """

    try:

        response = requests.post(
            OVERPASS_URL,

            data=query,

            headers=HEADERS,

            timeout=120
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
            or
            tags.get("building:part")
        ):

            polygon = []

            for p in element.get(
                "geometry",
                []
            ):

                if (
                    "lat" in p
                    and
                    "lon" in p
                ):

                    polygon.append(
                        (
                            float(p["lat"]),
                            float(p["lon"])
                        )
                    )

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

        elif (
            tags.get("amenity") == "toilets"
            or
            tags.get("elevator")
            or
            tags.get("entrance")
            or
            tags.get("highway") == "steps"
            or
            tags.get("room")
            or
            tags.get("indoor")
            or
            tags.get("level") is not None
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

    selected = None
    selected_distance = float(
        "inf"
    )

    for building in buildings:

        c = building[
            "center"
        ]

        if (
            building["polygon"]
            and
            point_in_polygon(
                lat,
                lon,
                building["polygon"]
            )
        ):

            selected = building
            selected_distance = 0

            break

        d = distance_meters(
            lat,
            lon,
            c[0],
            c[1]
        )

        if d < selected_distance:

            selected = building
            selected_distance = d

    if selected is None:
        return None

    if selected_distance > 180:
        return None

    attached = []

    for feature in features:

        f_lat, f_lon = feature[
            "center"
        ]

        inside = False

        if selected["polygon"]:

            inside = point_in_polygon(
                f_lat,
                f_lon,
                selected["polygon"]
            )

        d = distance_meters(
            f_lat,
            f_lon,
            selected["center"][0],
            selected["center"][1]
        )

        if (
            inside
            or
            d <= 180
        ):

            attached.append(
                feature
            )

    details = {
        "building":
            selected,

        "distance":
            selected_distance,

        "toilets":
            [],

        "accessible_toilets":
            [],

        "elevators":
            [],

        "entrances":
            [],

        "stairs":
            [],

        "rooms":
            [],

        "levels":
            set(),
    }

    for item in attached:

        tags = item[
            "tags"
        ]

        if (
            tags.get("amenity")
            ==
            "toilets"
        ):

            details[
                "toilets"
            ].append(
                item
            )

            if is_accessible(
                tags
            ):

                details[
                    "accessible_toilets"
                ].append(
                    item
                )

        if (
            tags.get("elevator")
            or
            tags.get("indoor")
            ==
            "elevator"
        ):

            details[
                "elevators"
            ].append(
                item
            )

        if tags.get("entrance"):

            details[
                "entrances"
            ].append(
                item
            )

        if (
            tags.get("highway")
            ==
            "steps"
        ):

            details[
                "stairs"
            ].append(
                item
            )

        if (
            tags.get("room")
            or
            tags.get("indoor")
            ==
            "room"
        ):

            details[
                "rooms"
            ].append(
                item
            )

        level = feature_level(
            tags
        )

        if level is not None:

            details[
                "levels"
            ].add(
                level
            )

    details[
        "levels"
    ] = sorted(
        details["levels"],
        key=lambda x: (
            safe_float(
                x,
                999
            ),
            x
        )
    )

    details[
        "building"
    ][
        "distance"
    ] = selected_distance

    return details


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

      nwr["amenity"="parking_space"]["parking_space"="disabled"]
        (around:{radius},{lat},{lon});

      nwr["amenity"="parking_space"]["wheelchair"="yes"]
        (around:{radius},{lat},{lon});

      nwr["amenity"="parking_space"]["capacity:disabled"]
        (around:{radius},{lat},{lon});
    );

    out body geom center;
    """

    try:

        response = requests.post(
            OVERPASS_URL,

            data=query,

            headers=HEADERS,

            timeout=120
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
            round(
                center[0],
                5
            ),
            round(
                center[1],
                5
            )
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        disabled_count = tags.get(
            "capacity:disabled"
        )

        if (
            tags.get(
                "parking_space"
            )
            ==
            "disabled"
        ):

            kind = (
                "موقف مخصص لذوي الإعاقة"
            )

        elif disabled_count:

            kind = (
                f"موقف يحتوي على "
                f"{disabled_count} موقف مخصص حسب البيانات"
            )

        else:

            kind = (
                "موقف مهيأ حسب بيانات "
                "OpenStreetMap"
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
                        "موقف ذوي الاحتياجات الخاصة"
                    ),

                "kind":
                    kind,

                "distance":
                    distance_meters(
                        lat,
                        lon,
                        center[0],
                        center[1]
                    ),
            }
        )

    results.sort(
        key=lambda x:
        x["distance"]
    )

    return results[
        :80
    ]


# =========================================================
# ROUTING
# =========================================================

def get_routes(
    start,
    destination
):

    if (
        not start
        or
        not destination
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
                "overview":
                    "full",

                "geometries":
                    "geojson",

                "steps":
                    "true",

                "alternatives":
                    "true",
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


def score_route(
    route
):

    return (
        route.get(
            "distance",
            0
        )
        +
        route.get(
            "duration",
            0
        )
        *
        0.5
    )


# =========================================================
# MAP HELPERS
# =========================================================

def add_parking_marker(
    target_map,
    parking,
    large=True
):

    lat, lon = parking[
        "center"
    ]

    size = (
        58
        if large
        else
        46
    )

    font = (
        30
        if large
        else
        23
    )

    marker_html = f"""
    <div style="
        width:{size}px;
        height:{size}px;
        background:#087cff;
        border:5px solid white;
        border-radius:50%;
        box-shadow:
            0 0 0 6px rgba(8,124,255,.28),
            0 5px 16px rgba(0,0,0,.35);
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:{font}px;
        font-weight:900;
        color:white;
        position:relative;
        z-index:9999;
    ">
        ♿
    </div>
    """

    popup = f"""
    <div style="
        direction:rtl;
        font-family:Arial;
        min-width:220px;
        text-align:right;
    ">

        <b style="font-size:17px;">
            🅿️ {html.escape(
                parking["name"]
            )}
        </b>

        <hr>

        <b>
            ♿ موقف مخصص / مهيأ
        </b>

        <br><br>

        {html.escape(
            parking["kind"]
        )}

        <br><br>

        📏 المسافة:
        {int(
            parking["distance"]
        )} متر

    </div>
    """

    folium.CircleMarker(
        location=[
            lat,
            lon
        ],

        radius=(
            31
            if large
            else
            24
        ),

        color="#087cff",

        fill=True,

        fill_color="#087cff",

        fill_opacity=0.18,

        weight=3,
    ).add_to(
        target_map
    )

    folium.Marker(
        [
            lat,
            lon
        ],

        tooltip=(
            f"🅿️ ♿ "
            f"{parking['name']}"
        ),

        popup=folium.Popup(
            popup,
            max_width=300
        ),

        icon=folium.DivIcon(
            html=marker_html
        )

    ).add_to(
        target_map
    )


def add_building_marker(
    target_map,
    details
):

    building = details[
        "building"
    ]

    lat, lon = building[
        "center"
    ]

    folium.CircleMarker(
        location=[
            lat,
            lon
        ],

        radius=24,

        color="#7657ff",

        fill=True,

        fill_color="#7657ff",

        fill_opacity=0.20,

        weight=3,
    ).add_to(
        target_map
    )

    marker_html = """
    <div style="
        width:48px;
        height:48px;
        background:#7657ff;
        border:5px solid white;
        border-radius:50%;
        box-shadow:0 4px 16px rgba(0,0,0,.35);
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:25px;
    ">
        🏢
    </div>
    """

    name = get_name(
        building["tags"],
        "المبنى"
    )

    folium.Marker(
        [
            lat,
            lon
        ],

        tooltip=(
            f"🏢 {name}"
        ),

        popup=folium.Popup(
            f"""
            <div style="
                direction:rtl;
                font-family:Arial;
            ">

                <b>
                    🏢 {html.escape(name)}
                </b>

                <br><br>

                🚻 حمامات مهيأة:
                {len(
                    details["accessible_toilets"]
                )}

                <br>

                🛗 مصاعد:
                {len(
                    details["elevators"]
                )}

                <br>

                🚪 مداخل:
                {len(
                    details["entrances"]
                )}

                <br>

                🪜 درج:
                {len(
                    details["stairs"]
                )}

            </div>
            """,

            max_width=300
        ),

        icon=folium.DivIcon(
            html=marker_html
        )

    ).add_to(
        target_map
    )


# =========================================================
# STATE ACTIONS
# =========================================================

def load_main_center(
    lat,
    lon
):

    st.session_state.search_center = (
        lat,
        lon
    )

    st.session_state.building_context_key = None

    st.session_state.building_details = None

    st.session_state.selected_building = None

    st.session_state.indoor_mode = False

    st.session_state.selected_floor = None


def clear_all():

    st.session_state.selection_mode = None

    st.session_state.start_point = None

    st.session_state.destination_point = None

    st.session_state.route_result = None

    st.session_state.selected_building = None

    st.session_state.building_details = None

    st.session_state.indoor_mode = False

    st.session_state.selected_floor = None

    st.session_state.map_key += 1


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

    page = st.radio(
        "التنقل",

        [
            "🗺️ الخريطة",
            "🅿️ مواقف ذوي الاحتياجات الخاصة"
        ],

        index=(
            0
            if st.session_state.page
            ==
            "🗺️ الخريطة"
            else
            1
        )
    )

    st.session_state.page = page


# =========================================================
# MAIN MAP PAGE
# =========================================================

if (
    st.session_state.page
    ==
    "🗺️ الخريطة"
):

    st.markdown(
        '<div class="main-title">'
        '♿ VerifyAI Access'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'ابحث عن المكان بالاسم أو اختره مباشرة من الخريطة، ثم اعرف خدمات الوصول والمواقف والمعلومات الداخلية المتاحة.'
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # SEARCH
    # =====================================================

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 🔎 ابحث عن مكان أو مبنى"
    )

    search_query = st.text_input(
        "اسم المكان",

        value=st.session_state.search_query,

        placeholder=(
            "مثال: Red Sea Mall Jeddah"
        ),

        key="main_place_search"
    )

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "🔎 بحث بالاسم",
            use_container_width=True
        ):

            st.session_state.search_query = (
                search_query
            )

            results = search_places(
                search_query
            )

            st.session_state.search_results = (
                results
            )

            st.session_state.selected_search_result = (
                0
                if results
                else
                None
            )

            if not results:

                st.warning(
                    "ما لقيت المكان. جرّب اسمًا مختلفًا."
                )

    with c2:

        if st.button(
            "📍 اختيار الموقع يدويًا من الخريطة",
            use_container_width=True
        ):

            st.session_state.manual_search_mode = True

    st.markdown(
        """
        <div class="search-hint">

        🔎 اكتب اسم المكان أو المبنى،

        أو

        📍 اضغط اختيار الموقع ثم اضغط أي نقطة في الخريطة.

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

        st.markdown(
            "### 📍 اختر النتيجة الصحيحة"
        )

        labels = [
            result.get(
                "display_name",
                "موقع"
            )

            for result
            in
            st.session_state.search_results
        ]

        current_index = (
            st.session_state.selected_search_result
            if
            st.session_state.selected_search_result
            is not None
            else
            0
        )

        current_index = min(
            current_index,
            len(labels) - 1
        )

        selected_index = st.selectbox(
            "نتائج البحث",

            range(
                len(labels)
            ),

            index=current_index,

            format_func=lambda i:
                labels[i],

            key="main_search_result_select"
        )

        st.session_state.selected_search_result = (
            selected_index
        )

        selected_result = (
            st.session_state.search_results[
                selected_index
            ]
        )

        result_lat = safe_float(
            selected_result.get(
                "lat"
            )
        )

        result_lon = safe_float(
            selected_result.get(
                "lon"
            )
        )

        if (
            result_lat is not None
            and
            result_lon is not None
        ):

            if st.button(
                "📍 استخدام هذا المكان",
                use_container_width=True
            ):

                load_main_center(
                    result_lat,
                    result_lon
                )

                st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # MANUAL MAP SELECTION
    # =====================================================

    if st.session_state.manual_search_mode:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 📍 اختر الموقع من الخريطة"
        )

        st.info(
            "اضغط أي نقطة على الخريطة لتحديد الموقع."
        )

        center_lat, center_lon = (
            st.session_state.search_center
        )

        manual_map = folium.Map(
            location=[
                center_lat,
                center_lon
            ],

            zoom_start=15,

            control_scale=True
        )

        folium.Marker(
            [
                center_lat,
                center_lon
            ],

            tooltip="المركز الحالي",

            icon=folium.Icon(
                color="blue",
                icon="crosshairs"
            )
        ).add_to(
            manual_map
        )

        manual_map_result = st_folium(
            manual_map,

            width=None,

            height=500,

            key=(
                f"main_manual_map_"
                f"{st.session_state.map_key}"
            )
        )

        clicked = manual_map_result.get(
            "last_clicked"
        )

        if clicked:

            load_main_center(
                clicked["lat"],
                clicked["lng"]
            )

            st.session_state.manual_search_mode = False

            st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # BUILDING CONTEXT
    # =====================================================

    center_lat, center_lon = (
        st.session_state.search_center
    )

    context_key = (
        round(center_lat, 5),
        round(center_lon, 5)
    )

    if (
        st.session_state.building_context_key
        !=
        context_key
    ):

        with st.spinner(
            "🔎 أبحث عن معلومات المبنى..."
        ):

            st.session_state.building_details = (
                get_building_details(
                    center_lat,
                    center_lon,
                    300
                )
            )

        st.session_state.building_context_key = (
            context_key
        )

        st.session_state.selected_building = (
            st.session_state.building_details
        )

    details = (
        st.session_state.building_details
    )


    # =====================================================
    # MAIN MAP
    # =====================================================

    main_map = folium.Map(
        location=[
            center_lat,
            center_lon
        ],

        zoom_start=16,

        control_scale=True
    )

    folium.Marker(
        [
            center_lat,
            center_lon
        ],

        tooltip="📍 الموقع المحدد",

        icon=folium.Icon(
            color="blue",
            icon="search"
        )
    ).add_to(
        main_map
    )


    # Nearby parking on the main map
    nearby_parking = get_accessible_parking(
        center_lat,
        center_lon,
        1800
    )

    for parking in nearby_parking[
        :25
    ]:

        add_parking_marker(
            main_map,
            parking,
            large=True
        )


    if details:

        building = details[
            "building"
        ]

        add_building_marker(
            main_map,
            details
        )

        if building.get(
            "polygon"
        ):

            folium.Polygon(
                locations=building[
                    "polygon"
                ],

                color="#7657ff",

                fill=True,

                fill_color="#7657ff",

                fill_opacity=0.10,

                weight=4,

            ).add_to(
                main_map
            )


    # =====================================================
    # ROUTE MARKERS
    # =====================================================

    if st.session_state.start_point:

        folium.Marker(
            st.session_state.start_point,

            tooltip="🟢 البداية",

            icon=folium.Icon(
                color="green",
                icon="play"
            )
        ).add_to(
            main_map
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
            main_map
        )


    # =====================================================
    # INDOOR FEATURES ON MAP
    # =====================================================

    if (
        details
        and
        st.session_state.indoor_mode
    ):

        selected_floor = (
            st.session_state.selected_floor
        )


        for feature in details[
            "accessible_toilets"
        ]:

            tags = feature[
                "tags"
            ]

            if (
                selected_floor
                and
                feature_level(
                    tags
                )
                and
                feature_level(
                    tags
                )
                !=
                selected_floor
            ):
                continue

            folium.CircleMarker(
                location=feature[
                    "center"
                ],

                radius=9,

                color="#18a957",

                fill=True,

                fill_color="#18a957",

                fill_opacity=0.9,

                tooltip=(
                    "🚻 حمام مهيأ — "
                    +
                    format_floor(
                        feature_level(
                            tags
                        )
                    )
                )
            ).add_to(
                main_map
            )


        for feature in details[
            "elevators"
        ]:

            tags = feature[
                "tags"
            ]

            if (
                selected_floor
                and
                feature_level(
                    tags
                )
                and
                feature_level(
                    tags
                )
                !=
                selected_floor
            ):
                continue

            folium.CircleMarker(
                location=feature[
                    "center"
                ],

                radius=9,

                color="#1677ff",

                fill=True,

                fill_color="#1677ff",

                fill_opacity=0.9,

                tooltip=(
                    "🛗 مصعد — "
                    +
                    format_floor(
                        feature_level(
                            tags
                        )
                    )
                )
            ).add_to(
                main_map
            )


        for feature in details[
            "entrances"
        ]:

            tags = feature[
                "tags"
            ]

            if (
                selected_floor
                and
                feature_level(
                    tags
                )
                and
                feature_level(
                    tags
                )
                !=
                selected_floor
            ):
                continue

            folium.CircleMarker(
                location=feature[
                    "center"
                ],

                radius=8,

                color="#7a45e8",

                fill=True,

                fill_color="#7a45e8",

                fill_opacity=0.9,

                tooltip="🚪 مدخل"
            ).add_to(
                main_map
            )


    map_result = st_folium(
        main_map,

        width=None,

        height=650,

        key=(
            f"main_map_"
            f"{st.session_state.map_key}"
        )
    )


    # =====================================================
    # MAP CLICK FOR ROUTING
    # =====================================================

    map_clicked = map_result.get(
        "last_clicked"
    )

    if map_clicked:

        click_lat = map_clicked[
            "lat"
        ]

        click_lon = map_clicked[
            "lng"
        ]

        mode = st.session_state.selection_mode

        if mode == "start":

            st.session_state.start_point = (
                click_lat,
                click_lon
            )

            st.session_state.selection_mode = None

            st.session_state.route_result = None

            st.rerun()

        elif mode == "destination":

            st.session_state.destination_point = (
                click_lat,
                click_lon
            )

            st.session_state.selection_mode = None

            st.session_state.route_result = None

            st.rerun()


    # =====================================================
    # BUILDING INFORMATION
    # =====================================================

    if details:

        building = details[
            "building"
        ]

        tags = building[
            "tags"
        ]

        building_name = get_name(
            tags,
            "المبنى المحدد"
        )

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            '<span class="badge-purple">'
            'معلومات المكان'
            '</span>',

            unsafe_allow_html=True
        )

        st.markdown(
            f"## 🏢 "
            f"{html.escape(building_name)}"
        )

        st.caption(
            "يبعد المبنى عن النقطة المحددة "
            f"{int(details['distance'])} متر تقريبًا."
        )


        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "🚻 حمامات مهيأة",
                len(
                    details[
                        "accessible_toilets"
                    ]
                )
            )

        with c2:

            st.metric(
                "🛗 مصاعد",
                len(
                    details[
                        "elevators"
                    ]
                )
            )

        with c3:

            st.metric(
                "🚪 مداخل",
                len(
                    details[
                        "entrances"
                    ]
                )
            )

        with c4:

            st.metric(
                "🪜 درج",
                len(
                    details[
                        "stairs"
                    ]
                )
            )


        # -------------------------------------------------
        # BUILDING IMAGE
        # -------------------------------------------------

        image_url = building_image_url(
            tags
        )

        if image_url:

            try:

                st.image(
                    image_url,

                    caption=(
                        "صورة المكان المتوفرة "
                        "في بيانات OpenStreetMap"
                    ),

                    use_container_width=True
                )

            except Exception:
                pass


        # -------------------------------------------------
        # ACCESSIBLE TOILETS
        # -------------------------------------------------

        st.markdown(
            "### 🚻 دورات المياه المهيأة"
        )

        if details[
            "accessible_toilets"
        ]:

            for toilet in details[
                "accessible_toilets"
            ]:

                toilet_tags = toilet[
                    "tags"
                ]

                toilet_name = get_name(
                    toilet_tags,
                    "حمام مهيأ"
                )

                floor = format_floor(
                    feature_level(
                        toilet_tags
                    )
                )

                st.markdown(
                    f"""
                    <div class="feature-card">

                        <div class="feature-title">
                            ♿ {html.escape(
                                toilet_name
                            )}
                        </div>

                        <div class="info-line">
                            📐 {html.escape(
                                floor
                            )}
                        </div>

                        <div class="info-line">
                            ✅ مهيأ حسب بيانات الخريطة
                        </div>

                    </div>
                    """,

                    unsafe_allow_html=True
                )

        else:

            st.info(
                "لا توجد حاليًا بيانات مؤكدة عن حمام مهيأ لهذا المبنى."
            )


        # -------------------------------------------------
        # ELEVATORS
        # -------------------------------------------------

        st.markdown(
            "### 🛗 المصاعد"
        )

        if details[
            "elevators"
        ]:

            for elevator in details[
                "elevators"
            ]:

                tags2 = elevator[
                    "tags"
                ]

                st.markdown(
                    f"""
                    <div class="feature-card">

                        <div class="feature-title">
                            🛗 مصعد
                        </div>

                        <div class="info-line">
                            📐 {html.escape(
                                format_floor(
                                    feature_level(
                                        tags2
                                    )
                                )
                            )}
                        </div>

                    </div>
                    """,

                    unsafe_allow_html=True
                )

        else:

            st.info(
                "لا توجد بيانات مصاعد مسجلة لهذا المبنى."
            )


        # -------------------------------------------------
        # ENTRANCES
        # -------------------------------------------------

        st.markdown(
            "### 🚪 المداخل"
        )

        if details[
            "entrances"
        ]:

            for entrance in details[
                "entrances"
            ]:

                tags2 = entrance[
                    "tags"
                ]

                wheelchair = str(
                    tags2.get(
                        "wheelchair",
                        ""
                    )
                ).lower()

                if wheelchair in {
                    "yes",
                    "designated",
                    "accessible"
                }:

                    access_text = (
                        "♿ مدخل مهيأ"
                    )

                elif wheelchair == "no":

                    access_text = (
                        "⚠️ غير مهيأ حسب البيانات"
                    )

                else:

                    access_text = (
                        "ℹ️ حالة الوصول غير محددة"
                    )

                st.markdown(
                    f"""
                    <div class="feature-card">

                        <div class="feature-title">
                            🚪 مدخل
                        </div>

                        <div class="info-line">
                            {access_text}
                        </div>

                    </div>
                    """,

                    unsafe_allow_html=True
                )

        else:

            st.info(
                "لا توجد بيانات مداخل مسجلة لهذا المبنى."
            )


        # -------------------------------------------------
        # FLOORS
        # -------------------------------------------------

        levels = details[
            "levels"
        ]

        if levels:

            st.markdown(
                "### 📐 الطوابق"
            )

            floor_options = [
                "كل الطوابق"
            ] + levels

            selected_floor = st.selectbox(
                "عرض معلومات طابق محدد",

                floor_options,

                index=(
                    floor_options.index(
                        st.session_state.selected_floor
                    )
                    if
                    st.session_state.selected_floor
                    in floor_options
                    else
                    0
                ),

                key="building_floor_select"
            )

            if selected_floor == "كل الطوابق":

                st.session_state.selected_floor = None

            else:

                st.session_state.selected_floor = (
                    selected_floor
                )


        # -------------------------------------------------
        # INDOOR MODE
        # -------------------------------------------------

        if st.button(
            "🗺️ عرض تفاصيل المبنى على الخريطة",
            use_container_width=True
        ):

            st.session_state.indoor_mode = True

            st.rerun()


        if st.session_state.indoor_mode:

            if st.button(
                "⬅️ إلغاء عرض التفاصيل الداخلية",
                use_container_width=True
            ):

                st.session_state.indoor_mode = False

                st.session_state.selected_floor = None

                st.rerun()


        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="card">

                <h3>
                    🏢 لم يتم العثور على مبنى قريب
                </h3>

                <p style="color:#777;">
                جرّب البحث باسم مبنى أو اختر نقطة أقرب إلى المبنى من الخريطة.
                </p>

            </div>
            """,

            unsafe_allow_html=True
        )


    # =====================================================
    # ROUTE CONTROLS
    # =====================================================

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 🧭 التنقل"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        if st.button(
            "🟢 اختر نقطة البداية",
            use_container_width=True
        ):

            st.session_state.selection_mode = "start"


    with c2:

        if st.button(
            "🔴 اختر الوجهة",
            use_container_width=True
        ):

            st.session_state.selection_mode = "destination"


    with c3:

        if st.button(
            "🗑️ مسح",
            use_container_width=True
        ):

            clear_all()

            st.rerun()


    if (
        st.session_state.selection_mode
        ==
        "start"
    ):

        st.info(
            "🟢 اضغط على الخريطة لتحديد نقطة البداية."
        )

    elif (
        st.session_state.selection_mode
        ==
        "destination"
    ):

        st.info(
            "🔴 اضغط على الخريطة لتحديد الوجهة."
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # ROUTE
    # =====================================================

    if (
        st.session_state.start_point
        and
        st.session_state.destination_point
    ):

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 🚶 المسار"
        )

        if st.button(
            "🚶 حساب أفضل مسار",
            use_container_width=True
        ):

            with st.spinner(
                "جاري حساب المسار..."
            ):

                routes = get_routes(
                    st.session_state.start_point,
                    st.session_state.destination_point
                )

            if routes:

                routes = sorted(
                    routes,
                    key=score_route
                )

                st.session_state.route_result = (
                    routes[0]
                )

            else:

                st.warning(
                    "تعذر العثور على مسار."
                )


        route = (
            st.session_state.route_result
        )

        if route:

            distance = route.get(
                "distance",
                0
            )

            duration = route.get(
                "duration",
                0
            )

            c1, c2 = st.columns(2)

            with c1:

                st.metric(
                    "📏 المسافة",
                    f"{distance / 1000:.2f} كم"
                )

            with c2:

                st.metric(
                    "⏱️ الوقت",
                    f"{duration / 60:.0f} دقيقة"
                )

            geometry = (
                route
                .get(
                    "geometry",
                    {}
                )
                .get(
                    "coordinates",
                    []
                )
            )

            if geometry:

                route_map = folium.Map(
                    location=[
                        st.session_state.start_point[0],
                        st.session_state.start_point[1]
                    ],

                    zoom_start=15,

                    control_scale=True
                )

                route_points = [
                    [
                        point[1],
                        point[0]
                    ]
                    for point in geometry
                ]

                folium.PolyLine(
                    route_points,

                    weight=7,

                    opacity=0.85
                ).add_to(
                    route_map
                )

                folium.Marker(
                    st.session_state.start_point,

                    tooltip="🟢 البداية",

                    icon=folium.Icon(
                        color="green"
                    )
                ).add_to(
                    route_map
                )

                folium.Marker(
                    st.session_state.destination_point,

                    tooltip="🔴 الوجهة",

                    icon=folium.Icon(
                        color="red"
                    )
                ).add_to(
                    route_map
                )

                st_folium(
                    route_map,

                    width=None,

                    height=450,

                    key=(
                        f"route_"
                        f"{st.session_state.map_key}"
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
        '<div class="main-title">'
        '🅿️ مواقف ذوي الاحتياجات الخاصة'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'ابحث عن موقع بالاسم أو اختره يدويًا من الخريطة، وستظهر المواقف المهيأة حوله بعلامات كبيرة وواضحة.'
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # PARKING SEARCH
    # =====================================================

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 🔎 ابحث عن موقع المواقف"
    )

    parking_query = st.text_input(
        "اسم المكان",

        value=st.session_state.parking_search_query,

        placeholder=(
            "مثال: Red Sea Mall Jeddah"
        ),

        key="parking_place_search"
    )

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "🔎 بحث بالاسم",
            use_container_width=True
        ):

            st.session_state.parking_search_query = (
                parking_query
            )

            results = search_places(
                parking_query
            )

            st.session_state.parking_search_results = (
                results
            )

            st.session_state.parking_selected_search_result = (
                0
                if results
                else None
            )

            if not results:

                st.warning(
                    "ما لقيت المكان."
                )

    with c2:

        if st.button(
            "📍 اختيار الموقع يدويًا",
            use_container_width=True
        ):

            st.session_state.parking_manual_mode = True

    st.markdown(
        """
        <div class="search-hint">

            🔎 ابحث باسم المكان

            أو

            📍 حدد موقعه يدويًا من الخريطة.

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # PARKING SEARCH RESULTS
    # =====================================================

    if (
        st.session_state.parking_search_results
    ):

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
            in
            st.session_state.parking_search_results
        ]

        current_index = (
            st.session_state.parking_selected_search_result
            if
            st.session_state.parking_selected_search_result
            is not None
            else
            0
        )

        current_index = min(
            current_index,
            len(labels) - 1
        )

        selected_index = st.selectbox(
            "اختر المكان الصحيح",

            range(
                len(labels)
            ),

            index=current_index,

            format_func=lambda i:
                labels[i],

            key="parking_result_select"
        )

        st.session_state.parking_selected_search_result = (
            selected_index
        )

        selected_result = (
            st.session_state.parking_search_results[
                selected_index
            ]
        )

        result_lat = safe_float(
            selected_result.get(
                "lat"
            )
        )

        result_lon = safe_float(
            selected_result.get(
                "lon"
            )
        )

        if (
            result_lat is not None
            and
            result_lon is not None
        ):

            if st.button(
                "📍 استخدام هذا المكان",
                use_container_width=True
            ):

                st.session_state.parking_center = (
                    result_lat,
                    result_lon
                )

                st.session_state.parking_loaded_key = None

                st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # PARKING MANUAL MAP
    # =====================================================

    if st.session_state.parking_manual_mode:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 📍 اختر موقع المواقف من الخريطة"
        )

        parking_lat, parking_lon = (
            st.session_state.parking_center
        )

        manual_parking_map = folium.Map(
            location=[
                parking_lat,
                parking_lon
            ],

            zoom_start=15,

            control_scale=True
        )

        folium.Marker(
            [
                parking_lat,
                parking_lon
            ],

            tooltip="الموقع الحالي",

            icon=folium.Icon(
                color="blue",
                icon="crosshairs"
            )
        ).add_to(
            manual_parking_map
        )

        parking_manual_result = st_folium(
            manual_parking_map,

            width=None,

            height=500,

            key=(
                f"parking_manual_"
                f"{st.session_state.map_key}"
            )
        )

        clicked = parking_manual_result.get(
            "last_clicked"
        )

        if clicked:

            st.session_state.parking_center = (
                clicked["lat"],
                clicked["lng"]
            )

            st.session_state.parking_manual_mode = False

            st.session_state.parking_loaded_key = None

            st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # =====================================================
    # PARKING RADIUS
    # =====================================================

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    parking_radius_options = [
        500,
        1000,
        1800,
        2500,
        5000
    ]

    parking_radius = st.selectbox(
        "نطاق البحث",

        parking_radius_options,

        index=parking_radius_options.index(
            st.session_state.parking_radius
        ),

        format_func=lambda x:
            f"{x:,} متر",

        key="parking_radius_select"
    )

    if (
        parking_radius
        !=
        st.session_state.parking_radius
    ):

        st.session_state.parking_radius = (
            parking_radius
        )

        st.session_state.parking_loaded_key = None


    parking_lat, parking_lon = (
        st.session_state.parking_center
    )

    st.markdown(
        f"""
        <div class="search-hint">
            📍 {html.escape(
                reverse_geocode(
                    parking_lat,
                    parking_lon
                )
            )}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # LOAD PARKING
    # =====================================================

    parking_key = (
        round(
            parking_lat,
            5
        ),

        round(
            parking_lon,
            5
        ),

        parking_radius
    )

    if (
        st.session_state.parking_loaded_key
        !=
        parking_key
    ):

        with st.spinner(
            "🅿️ أبحث عن المواقف المهيأة..."
        ):

            st.session_state.parking_results = (
                get_accessible_parking(
                    parking_lat,
                    parking_lon,
                    parking_radius
                )
            )

        st.session_state.parking_loaded_key = (
            parking_key
        )


    parking_results = (
        st.session_state.parking_results
    )


    # =====================================================
    # PARKING MAP
    # =====================================================

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 🗺️ المواقف على الخريطة"
    )

    parking_map = folium.Map(
        location=[
            parking_lat,
            parking_lon
        ],

        zoom_start=14,

        control_scale=True
    )

    folium.Circle(
        location=[
            parking_lat,
            parking_lon
        ],

        radius=parking_radius,

        color="#087cff",

        fill=True,

        fill_opacity=0.05
    ).add_to(
        parking_map
    )

    folium.Marker(
        [
            parking_lat,
            parking_lon
        ],

        tooltip="📍 مركز البحث",

        icon=folium.Icon(
            color="blue",
            icon="search"
        )
    ).add_to(
        parking_map
    )

    for parking in parking_results:

        add_parking_marker(
            parking_map,
            parking,
            large=True
        )

    parking_map_result = st_folium(
        parking_map,

        width=None,

        height=650,

        key=(
            f"parking_map_"
            f"{st.session_state.map_key}"
        )
    )

    clicked = parking_map_result.get(
        "last_clicked"
    )

    if (
        clicked
        and
        parking_results
    ):

        nearest = min(
            parking_results,

            key=lambda p:
                distance_meters(
                    clicked["lat"],
                    clicked["lng"],
                    p["center"][0],
                    p["center"][1]
                )
        )

        nearest_distance = distance_meters(
            clicked["lat"],
            clicked["lng"],
            nearest["center"][0],
            nearest["center"][1]
        )

        if nearest_distance <= 100:

            st.session_state.destination_point = (
                nearest["center"]
            )

            st.success(
                "♿ تم اختيار هذا الموقف كوجهة."
            )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # PARKING LIST
    # =====================================================

    st.markdown(
        "### 🅿️ المواقف الموجودة"
    )

    if parking_results:

        for index, parking in enumerate(
            parking_results
        ):

            tags = parking[
                "tags"
            ]

            disabled_count = tags.get(
                "capacity:disabled"
            )

            count_line = ""

            if disabled_count:

                count_line = (
                    f"<br>"
                    f"🅿️ عدد المواقف المخصصة: "
                    f"{html.escape(
                        str(disabled_count)
                    )}"
                )

            st.markdown(
                f"""
                <div class="parking-card">

                    <span class="badge-blue">
                        ♿ موقف واضح ومهيأ
                    </span>

                    <div
                        class="parking-title"
                        style="margin-top:10px;"
                    >

                        🅿️ {html.escape(
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

                        {count_line}

                        <br>

                        📏 {int(
                            parking["distance"]
                        )} متر من مركز البحث

                    </div>

                </div>
                """,

                unsafe_allow_html=True
            )

            if st.button(
                "📍 استخدم هذا الموقف كوجهة",

                key=(
                    f"parking_destination_"
                    f"{index}"
                ),

                use_container_width=True
            ):

                st.session_state.destination_point = (
                    parking["center"]
                )

                st.session_state.page = (
                    "🗺️ الخريطة"
                )

                st.session_state.search_center = (
                    parking["center"]
                )

                st.session_state.building_context_key = None

                st.success(
                    "تم اختيار الموقف. تقدر الآن تختار نقطة البداية وتحسب المسار."
                )

                st.rerun()

    else:

        st.markdown(
            """
            <div class="card">

                <h3>
                    لا توجد مواقف مهيأة مسجلة
                </h3>

                <p style="color:#777;">
                عدم ظهور موقف لا يعني بالضرورة عدم وجوده؛
                قد لا تكون بياناته مسجلة في OpenStreetMap.
                </p>

            </div>
            """,

            unsafe_allow_html=True
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
