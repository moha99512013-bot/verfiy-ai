import os
import math
import html
import requests
import streamlit as st
import folium
from folium.plugins import MarkerCluster
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

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OSRM_URL = "https://router.project-osrm.org/route/v1/foot"

HEADERS = {
    "User-Agent": "VerifyAI-Access/7.0"
}


# =========================================================
# STYLE
# =========================================================

st.markdown(
    """
<style>

@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: "Cairo", sans-serif;
}

.stApp {
    background:
        radial-gradient(
            circle at 10% 5%,
            rgba(118,87,255,.10),
            transparent 25%
        ),
        radial-gradient(
            circle at 90% 10%,
            rgba(0,190,180,.08),
            transparent 25%
        ),
        #f7f8fc;
}

.block-container {
    max-width: 1450px;
    padding-top: 1rem;
    padding-bottom: 3rem;
}

.stButton > button {
    border-radius: 14px !important;
    border: 0 !important;
    background: #7657ff !important;
    color: white !important;
    font-weight: 800 !important;
    min-height: 45px !important;
    box-shadow: 0 8px 22px rgba(118,87,255,.20);
}

.stButton > button:hover {
    background: #6549e8 !important;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e8e7ef;
    padding: 14px;
    border-radius: 18px;
    box-shadow: 0 8px 25px rgba(35,25,80,.04);
}

.footer {
    text-align: center;
    color: #999aa8;
    font-size: 11px;
    padding: 30px 0 10px;
}

.search-card {
    background: white;
    border: 1px solid #e8e7ef;
    border-radius: 20px;
    padding: 18px;
    margin-bottom: 15px;
}

.building-card {
    background: white;
    border: 1px solid #e8e7ef;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 12px;
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

    "selection_mode": None,

    "start_point": None,
    "destination_point": None,

    "selected_building": None,
    "selected_floor": "كل الطوابق",

    "indoor_mode": False,
    "indoor_destination": None,

    "route_result": None,
    "ai_answer": None,

    "map_key": 0,

    # Search
    "search_query": "",
    "search_results": [],
    "search_center": None,
    "search_center_name": None,
    "search_radius": 3000,

    # Buildings
    "openable_buildings": [],
    "buildings_loaded_key": None,

    # Search map selection
    "search_map_mode": False,
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# HELPERS
# =========================================================

def reverse_geocode(lat, lon):

    try:

        response = requests.get(
            f"{NOMINATIM_URL}/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "json",
                "zoom": 18,
                "addressdetails": 1
            },
            headers=HEADERS,
            timeout=15
        )

        return response.json().get(
            "display_name",
            "الموقع المحدد"
        )

    except Exception:

        return "الموقع المحدد"


def search_places(query):

    if not query.strip():
        return []

    try:

        response = requests.get(
            f"{NOMINATIM_URL}/search",
            params={
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 10
            },
            headers=HEADERS,
            timeout=20
        )

        if response.status_code != 200:
            return []

        return response.json()

    except Exception:

        return []


def distance_meters(
    lat1,
    lon1,
    lat2,
    lon2
):

    earth = 6371000

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

    return earth * 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )


def has_indoor_information(indoor):

    return (
        len(indoor.get("levels", [])) > 0
        or len(indoor.get("rooms", [])) > 0
        or len(indoor.get("entrances", [])) > 0
        or len(indoor.get("elevators", [])) > 0
        or len(indoor.get("stairs", [])) > 0
        or len(indoor.get("toilets", [])) > 0
        or len(indoor.get("corridors", [])) > 0
    )


def floor_visible(point, selected_floor):

    if selected_floor == "كل الطوابق":
        return True

    tags = point.get("tags", {})

    point_level = tags.get("level")

    if not point_level:
        return True

    levels = [
        str(x).strip()
        for x in str(point_level).split(";")
    ]

    return str(selected_floor) in levels


def draw_polygon(
    map_object,
    geometry,
    **kwargs
):

    points = [
        [
            point["lat"],
            point["lon"]
        ]
        for point in geometry
        if "lat" in point and "lon" in point
    ]

    if len(points) >= 3:

        folium.Polygon(
            points,
            **kwargs
        ).add_to(map_object)


def element_point(element):

    if "lat" in element and "lon" in element:

        return (
            float(element["lat"]),
            float(element["lon"])
        )

    center = element.get("center")

    if center:

        return (
            float(center["lat"]),
            float(center["lon"])
        )

    geometry = element.get("geometry", [])

    if geometry:

        valid = [
            p for p in geometry
            if "lat" in p and "lon" in p
        ]

        if valid:

            return (
                sum(p["lat"] for p in valid) / len(valid),
                sum(p["lon"] for p in valid) / len(valid)
            )

    return None


def point_in_polygon(lat, lon, geometry):

    if len(geometry) < 3:
        return False

    inside = False

    j = len(geometry) - 1

    for i in range(len(geometry)):

        yi = geometry[i]["lat"]
        xi = geometry[i]["lon"]

        yj = geometry[j]["lat"]
        xj = geometry[j]["lon"]

        if (
            (yi > lat) != (yj > lat)
            and
            lon < (
                (xj - xi)
                * (lat - yi)
                / ((yj - yi) or 0.0000001)
                + xi
            )
        ):

            inside = not inside

        j = i

    return inside


def building_name(building):

    tags = building.get("tags", {})

    return (
        tags.get("name")
        or tags.get("official_name")
        or tags.get("brand")
        or tags.get("amenity")
        or tags.get("shop")
        or tags.get("building")
        or "مبنى قابل للفتح"
    )


# =========================================================
# OPENABLE BUILDINGS
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_openable_buildings(
    lat,
    lon,
    radius=3000
):

    query = f"""
    [out:json][timeout:90];

    (
        way["building"](around:{radius},{lat},{lon});
        relation["building"](around:{radius},{lat},{lon});

        node["indoor"](around:{radius},{lat},{lon});
        way["indoor"](around:{radius},{lat},{lon});
        relation["indoor"](around:{radius},{lat},{lon});

        node["room"](around:{radius},{lat},{lon});
        way["room"](around:{radius},{lat},{lon});

        node["entrance"](around:{radius},{lat},{lon});
        way["entrance"](around:{radius},{lat},{lon});

        node["level"](around:{radius},{lat},{lon});
        way["level"](around:{radius},{lat},{lon});

        node["highway"="elevator"](around:{radius},{lat},{lon});
        node["elevator"="yes"](around:{radius},{lat},{lon});

        node["highway"="steps"](around:{radius},{lat},{lon});
        way["highway"="steps"](around:{radius},{lat},{lon});

        node["amenity"="toilets"](around:{radius},{lat},{lon});
        way["amenity"="toilets"](around:{radius},{lat},{lon});
    );

    out center geom;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=100
        )

        if response.status_code != 200:
            return []

        elements = response.json().get(
            "elements",
            []
        )

    except Exception:

        return []

    buildings = []

    indoor_elements = []

    # -----------------------------------------------------
    # BUILDINGS
    # -----------------------------------------------------

    for item in elements:

        tags = item.get("tags", {})

        if "building" not in tags:
            continue

        point = element_point(item)

        if not point:
            continue

        buildings.append(
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "lat": point[0],
                "lon": point[1],
                "tags": tags,
                "geometry": item.get("geometry", []),
                "indoor_elements": []
            }
        )

    # -----------------------------------------------------
    # INDOOR ELEMENTS
    # -----------------------------------------------------

    for item in elements:

        tags = item.get("tags", {})

        is_indoor = (
            bool(tags.get("indoor"))
            or bool(tags.get("room"))
            or bool(tags.get("entrance"))
            or bool(tags.get("level"))
            or tags.get("elevator") == "yes"
            or tags.get("highway") in {
                "elevator",
                "steps"
            }
            or tags.get("amenity") == "toilets"
        )

        if not is_indoor:
            continue

        point = element_point(item)

        if not point:
            continue

        indoor_elements.append(
            {
                "element": item,
                "lat": point[0],
                "lon": point[1]
            }
        )

    # -----------------------------------------------------
    # MATCH INDOOR DATA
    # -----------------------------------------------------

    for indoor_item in indoor_elements:

        p_lat = indoor_item["lat"]
        p_lon = indoor_item["lon"]

        candidates = []

        # First: buildings whose actual footprint contains point
        for building in buildings:

            geometry = building.get(
                "geometry",
                []
            )

            if not geometry:
                continue

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

            if not lats or not lons:
                continue

            if (
                min(lats) <= p_lat <= max(lats)
                and
                min(lons) <= p_lon <= max(lons)
            ):

                if point_in_polygon(
                    p_lat,
                    p_lon,
                    geometry
                ):

                    candidates.append(
                        building
                    )

        # Fallback: nearest building
        if not candidates:

            nearest = None
            nearest_distance = float("inf")

            for building in buildings:

                d = distance_meters(
                    p_lat,
                    p_lon,
                    building["lat"],
                    building["lon"]
                )

                if d < nearest_distance:

                    nearest_distance = d
                    nearest = building

            if nearest and nearest_distance <= 180:

                candidates = [nearest]

        for building in candidates:

            building["indoor_elements"].append(
                indoor_item["element"]
            )

    # -----------------------------------------------------
    # CREATE OPENABLE LIST
    # -----------------------------------------------------

    openable = []

    seen = set()

    for building in buildings:

        if not building["indoor_elements"]:
            continue

        key = (
            building["type"],
            building["id"]
        )

        if key in seen:
            continue

        seen.add(key)

        indoor = parse_indoor_data(
            building["indoor_elements"]
        )

        if not has_indoor_information(indoor):
            continue

        building["indoor"] = indoor

        building["distance"] = distance_meters(
            lat,
            lon,
            building["lat"],
            building["lon"]
        )

        openable.append(
            building
        )

    openable.sort(
        key=lambda x: x["distance"]
    )

    return openable


# =========================================================
# FIND BUILDING
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_building_at_point(
    lat,
    lon,
    radius=180
):

    query = f"""
    [out:json][timeout:35];

    (
        way["building"](around:{radius},{lat},{lon});
        relation["building"](around:{radius},{lat},{lon});
    );

    out center geom;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=45
        )

        elements = response.json().get(
            "elements",
            []
        )

    except Exception:

        return None

    best = None
    best_distance = float("inf")

    for item in elements:

        point = element_point(item)

        if not point:
            continue

        d = distance_meters(
            lat,
            lon,
            point[0],
            point[1]
        )

        if d < best_distance:

            best_distance = d

            best = {
                "id": item.get("id"),
                "type": item.get("type"),
                "tags": item.get("tags", {}),
                "center": {
                    "lat": point[0],
                    "lon": point[1]
                },
                "geometry": item.get(
                    "geometry",
                    []
                )
            }

    return best


# =========================================================
# INDOOR DATA
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_indoor_data(
    lat,
    lon,
    radius=400
):

    query = f"""
    [out:json][timeout:60];

    (
        node["entrance"](around:{radius},{lat},{lon});
        way["entrance"](around:{radius},{lat},{lon});

        node["indoor"](around:{radius},{lat},{lon});
        way["indoor"](around:{radius},{lat},{lon});
        relation["indoor"](around:{radius},{lat},{lon});

        node["room"](around:{radius},{lat},{lon});
        way["room"](around:{radius},{lat},{lon});

        node["highway"="elevator"](around:{radius},{lat},{lon});
        node["elevator"="yes"](around:{radius},{lat},{lon});

        node["highway"="steps"](around:{radius},{lat},{lon});
        way["highway"="steps"](around:{radius},{lat},{lon});

        node["amenity"="toilets"](around:{radius},{lat},{lon});
        way["amenity"="toilets"](around:{radius},{lat},{lon});

        node["wheelchair"](around:{radius},{lat},{lon});
        way["wheelchair"](around:{radius},{lat},{lon});

        node["level"](around:{radius},{lat},{lon});
        way["level"](around:{radius},{lat},{lon});
    );

    out center geom;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=70
        )

        return response.json().get(
            "elements",
            []
        )

    except Exception:

        return []


def parse_indoor_data(elements):

    result = {
        "entrances": [],
        "elevators": [],
        "stairs": [],
        "rooms": [],
        "toilets": [],
        "corridors": [],
        "other": [],
        "levels": set()
    }

    for element in elements:

        tags = element.get(
            "tags",
            {}
        )

        point = element_point(element)

        if not point:
            continue

        point_data = {
            "lat": point[0],
            "lon": point[1],
            "tags": tags,
            "geometry": element.get(
                "geometry",
                []
            )
        }

        if tags.get("level"):

            for level in str(
                tags["level"]
            ).split(";"):

                result["levels"].add(
                    level.strip()
                )

        if "entrance" in tags:
            result["entrances"].append(
                point_data
            )

        if (
            tags.get("highway") == "elevator"
            or tags.get("elevator") == "yes"
            or tags.get("indoor") == "elevator"
        ):

            result["elevators"].append(
                point_data
            )

        if (
            tags.get("highway") == "steps"
            or tags.get("indoor") == "stairs"
        ):

            result["stairs"].append(
                point_data
            )

        if (
            tags.get("room")
            or tags.get("indoor") == "room"
        ):

            result["rooms"].append(
                point_data
            )

        if tags.get("amenity") == "toilets":

            result["toilets"].append(
                point_data
            )

        if (
            tags.get("indoor") == "corridor"
            or tags.get("highway") == "corridor"
        ):

            result["corridors"].append(
                point_data
            )

        if tags.get("indoor"):

            if tags.get("indoor") not in {
                "room",
                "corridor",
                "stairs",
                "elevator"
            }:

                result["other"].append(
                    point_data
                )

    def floor_sort(value):

        try:
            return float(value)
        except Exception:
            return 999

    result["levels"] = sorted(
        list(result["levels"]),
        key=floor_sort
    )

    return result


# =========================================================
# OUTDOOR ACCESSIBILITY
# =========================================================

def get_accessibility_data(
    lat,
    lon,
    radius=1800
):

    query = f"""
    [out:json][timeout:40];

    (
        node["highway"="steps"](around:{radius},{lat},{lon});
        way["highway"="steps"](around:{radius},{lat},{lon});

        node["highway"="elevator"](around:{radius},{lat},{lon});
        node["elevator"="yes"](around:{radius},{lat},{lon});

        node["ramp"="yes"](around:{radius},{lat},{lon});
        way["ramp"="yes"](around:{radius},{lat},{lon});

        node["wheelchair"](around:{radius},{lat},{lon});
        way["wheelchair"](around:{radius},{lat},{lon});

        node["amenity"="toilets"]["wheelchair"="yes"](around:{radius},{lat},{lon});

        node["amenity"="parking"]["wheelchair"="yes"](around:{radius},{lat},{lon});

        node["entrance"]["wheelchair"="yes"](around:{radius},{lat},{lon});
    );

    out center;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=50
        )

        elements = response.json().get(
            "elements",
            []
        )

    except Exception:

        elements = []

    result = {
        "stairs": [],
        "elevators": [],
        "ramps": [],
        "wheelchair_yes": [],
        "wheelchair_no": [],
        "toilets": [],
        "parking": [],
        "entrances": []
    }

    for element in elements:

        tags = element.get(
            "tags",
            {}
        )

        point = element_point(element)

        if not point:
            continue

        point_data = {
            "lat": point[0],
            "lon": point[1],
            "tags": tags
        }

        if tags.get("highway") == "steps":
            result["stairs"].append(point_data)

        if (
            tags.get("highway") == "elevator"
            or tags.get("elevator") == "yes"
        ):

            result["elevators"].append(point_data)

        if tags.get("ramp") == "yes":
            result["ramps"].append(point_data)

        if tags.get("wheelchair") == "yes":
            result["wheelchair_yes"].append(point_data)

        if tags.get("wheelchair") == "no":
            result["wheelchair_no"].append(point_data)

        if (
            tags.get("amenity") == "toilets"
            and tags.get("wheelchair") == "yes"
        ):

            result["toilets"].append(point_data)

        if (
            tags.get("amenity") == "parking"
            and tags.get("wheelchair") == "yes"
        ):

            result["parking"].append(point_data)

        if (
            tags.get("entrance")
            and tags.get("wheelchair") == "yes"
        ):

            result["entrances"].append(point_data)

    return result


# =========================================================
# ROUTING
# =========================================================

def get_routes(
    start,
    destination
):

    url = (
        f"{OSRM_URL}/"
        f"{start['lon']},{start['lat']};"
        f"{destination['lon']},{destination['lat']}"
    )

    params = {
        "alternatives": "true",
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        return response.json().get(
            "routes",
            []
        )

    except Exception:

        return []


def score_route(
    route,
    accessibility
):

    score = 100

    coordinates = route[
        "geometry"
    ]["coordinates"]

    step = max(
        1,
        len(coordinates) // 80
    )

    for lon, lat in coordinates[::step]:

        for stair in accessibility["stairs"]:

            if distance_meters(
                lat,
                lon,
                stair["lat"],
                stair["lon"]
            ) < 80:

                score -= 15

        for bad in accessibility["wheelchair_no"]:

            if distance_meters(
                lat,
                lon,
                bad["lat"],
                bad["lon"]
            ) < 80:

                score -= 20

    return max(
        0,
        min(
            100,
            round(score)
        )
    )


# =========================================================
# OPEN BUILDING
# =========================================================

def load_building_indoor(building):

    center = building.get(
        "center",
        {
            "lat": building["lat"],
            "lon": building["lon"]
        }
    )

    elements = get_indoor_data(
        center["lat"],
        center["lon"],
        radius=400
    )

    building["indoor"] = parse_indoor_data(
        elements
    )

    return building


def open_building(building):

    building = dict(building)

    if "indoor" not in building:

        building = load_building_indoor(
            building
        )

    if not has_indoor_information(
        building.get("indoor", {})
    ):

        return False

    st.session_state.selected_building = building
    st.session_state.indoor_mode = True

    levels = building["indoor"].get(
        "levels",
        []
    )

    st.session_state.selected_floor = (
        levels[0]
        if levels
        else "كل الطوابق"
    )

    st.session_state.selection_mode = None
    st.session_state.map_key += 1

    return True


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

with st.sidebar:

    st.markdown(
        "## ♿ VerifyAI Access"
    )

    st.caption(
        "التنقل"
    )

    page = st.radio(
        "الصفحات",
        [
            "🗺️ الخريطة",
            "🏢 المباني القابلة للفتح"
        ],
        index=(
            0
            if st.session_state.page == "🗺️ الخريطة"
            else 1
        ),
        label_visibility="collapsed"
    )

    st.session_state.page = page

    st.divider()

    st.markdown(
        "**VerifyAI Access**\n\n"
        "نظام يساعد على اكتشاف الأماكن "
        "والطرق والبيانات الداخلية المناسبة "
        "للوصول الشامل."
    )


# =========================================================
# HEADER
# =========================================================

st.title(
    "♿ VerifyAI Access"
)

st.caption(
    "خريطة وصول ذكية — اكتشف الطرق والمباني الداخلية بسهولة."
)


# =========================================================
# SEARCH COMPONENT
# =========================================================

st.markdown(
    '<div class="search-card">',
    unsafe_allow_html=True
)

st.subheader(
    "🔎 البحث عن مكان"
)

search_col1, search_col2 = st.columns(
    [5, 1]
)

with search_col1:

    search_text = st.text_input(
        "ابحث باسم مبنى أو منطقة أو شارع",
        value=st.session_state.search_query,
        placeholder="مثال: جامعة الملك عبدالعزيز أو مستشفى...",
        label_visibility="collapsed"
    )

with search_col2:

    search_button = st.button(
        "🔎 بحث",
        use_container_width=True
    )


if search_button:

    st.session_state.search_query = search_text

    with st.spinner(
        "جاري البحث..."
    ):

        st.session_state.search_results = (
            search_places(search_text)
        )


if st.session_state.search_results:

    result_names = [
        item.get(
            "display_name",
            "موقع"
        )
        for item in st.session_state.search_results
    ]

    selected_index = st.selectbox(
        "اختر الموقع",
        range(
            len(result_names)
        ),
        format_func=lambda i: result_names[i]
    )

    if st.button(
        "📍 استخدام هذا الموقع",
        use_container_width=True
    ):

        selected = st.session_state.search_results[
            selected_index
        ]

        lat = float(
            selected["lat"]
        )

        lon = float(
            selected["lon"]
        )

        st.session_state.search_center = {
            "lat": lat,
            "lon": lon
        }

        st.session_state.search_center_name = (
            selected.get(
                "display_name",
                "الموقع المحدد"
            )
        )

        st.session_state.openable_buildings = []
        st.session_state.buildings_loaded_key = None
        st.session_state.map_key += 1

        st.rerun()


st.markdown(
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# PAGE 2 - OPENABLE BUILDINGS
# =========================================================

if st.session_state.page == "🏢 المباني القابلة للفتح":

    st.header(
        "🏢 المباني القابلة للفتح"
    )

    st.write(
        "هذه الصفحة تعرض المباني التي وجد لها النظام "
        "بيانات داخلية في OpenStreetMap."
    )

    radius = st.select_slider(
        "📏 نطاق البحث",
        options=[
            1000,
            2000,
            3000,
            5000
        ],
        value=st.session_state.search_radius,
        format_func=lambda x: f"{x // 1000} كم"
    )

    st.session_state.search_radius = radius

    if st.session_state.search_center:

        center = st.session_state.search_center

        st.success(
            "📍 مركز البحث:\n\n"
            + st.session_state.search_center_name
        )

    else:

        center = {
            "lat": 21.5433,
            "lon": 39.1728
        }

        st.info(
            "لم تحدد موقعًا بعد، لذلك يبدأ البحث من جدة. "
            "استخدم البحث أعلاه لاختيار أي منطقة."
        )

    # -----------------------------------------------------
    # MANUAL LOCATION BUTTON
    # -----------------------------------------------------

    if st.button(
        "📍 أريد اختيار مركز البحث من الخريطة",
        use_container_width=True
    ):

        st.session_state.search_map_mode = True
        st.session_state.map_key += 1

    if st.session_state.search_map_mode:

        st.info(
            "اضغط على الخريطة في المكان الذي تريد البحث حوله."
        )

        search_map = folium.Map(
            location=[
                center["lat"],
                center["lon"]
            ],
            zoom_start=14,
            tiles="OpenStreetMap",
            control_scale=True
        )

        folium.Marker(
            [
                center["lat"],
                center["lon"]
            ],
            tooltip="📍 مركز البحث الحالي",
            icon=folium.Icon(
                color="blue",
                icon="search",
                prefix="fa"
            )
        ).add_to(
            search_map
        )

        search_click = st_folium(
            search_map,
            width=None,
            height=500,
            returned_objects=[
                "last_clicked"
            ],
            key=f"search_map_{st.session_state.map_key}"
        )

        if (
            search_click
            and search_click.get("last_clicked")
        ):

            clicked = search_click[
                "last_clicked"
            ]

            lat = float(
                clicked["lat"]
            )

            lon = float(
                clicked["lng"]
            )

            st.session_state.search_center = {
                "lat": lat,
                "lon": lon
            }

            st.session_state.search_center_name = (
                reverse_geocode(
                    lat,
                    lon
                )
            )

            st.session_state.search_map_mode = False

            st.session_state.openable_buildings = []
            st.session_state.buildings_loaded_key = None

            st.rerun()

    # -----------------------------------------------------
    # LOAD BUILDINGS
    # -----------------------------------------------------

    center_key = (
        round(center["lat"], 5),
        round(center["lon"], 5),
        radius
    )

    if (
        st.session_state.buildings_loaded_key
        != center_key
    ):

        with st.spinner(
            "🏢 جاري البحث عن المباني التي تحتوي بيانات داخلية..."
        ):

            buildings = get_openable_buildings(
                center["lat"],
                center["lon"],
                radius
            )

        st.session_state.openable_buildings = buildings
        st.session_state.buildings_loaded_key = center_key

    buildings = st.session_state.openable_buildings

    st.divider()

    if buildings:

        st.success(
            f"🏢 تم العثور على {len(buildings)} مبنى قابل للفتح "
            f"ضمن نطاق {radius // 1000} كم."
        )

        # -------------------------------------------------
        # BUILDINGS MAP
        # -------------------------------------------------

        buildings_map = folium.Map(
            location=[
                center["lat"],
                center["lon"]
            ],
            zoom_start=14,
            tiles="OpenStreetMap",
            control_scale=True
        )

        folium.Marker(
            [
                center["lat"],
                center["lon"]
            ],
            tooltip="📍 مركز البحث",
            icon=folium.Icon(
                color="blue",
                icon="search",
                prefix="fa"
            )
        ).add_to(
            buildings_map
        )

        cluster = MarkerCluster().add_to(
            buildings_map
        )

        for index, building in enumerate(
            buildings
        ):

            name = building_name(
                building
            )

            indoor = building.get(
                "indoor",
                {}
            )

            popup = f"""
            <div style="font-family:Arial;min-width:220px">
                <b>🏢 {html.escape(str(name))}</b>
                <hr>
                🚪 المداخل: {len(indoor.get("entrances", []))}<br>
                🛗 المصاعد: {len(indoor.get("elevators", []))}<br>
                📍 الأماكن: {len(indoor.get("rooms", []))}<br>
                🪜 السلالم: {len(indoor.get("stairs", []))}<br>
                🚻 دورات المياه: {len(indoor.get("toilets", []))}
            </div>
            """

            folium.Marker(
                [
                    building["lat"],
                    building["lon"]
                ],
                tooltip=f"🏢 {name}",
                popup=folium.Popup(
                    popup,
                    max_width=300
                ),
                icon=folium.Icon(
                    color="purple",
                    icon="building",
                    prefix="fa"
                )
            ).add_to(
                cluster
            )

        st_folium(
            buildings_map,
            width=None,
            height=550,
            returned_objects=[],
            key=f"buildings_map_{st.session_state.map_key}"
        )

        st.divider()

        # -------------------------------------------------
        # BUILDINGS LIST
        # -------------------------------------------------

        st.subheader(
            "📋 قائمة المباني"
        )

        for index, building in enumerate(
            buildings
        ):

            name = building_name(
                building
            )

            tags = building.get(
                "tags",
                {}
            )

            indoor = building.get(
                "indoor",
                {}
            )

            distance = building.get(
                "distance",
                distance_meters(
                    center["lat"],
                    center["lon"],
                    building["lat"],
                    building["lon"]
                )
            )

            if distance < 1000:

                distance_text = (
                    f"{round(distance)} متر"
                )

            else:

                distance_text = (
                    f"{distance / 1000:.1f} كم"
                )

            with st.container():

                st.markdown(
                    '<div class="building-card">',
                    unsafe_allow_html=True
                )

                col_info, col_button = st.columns(
                    [4, 1]
                )

                with col_info:

                    st.markdown(
                        f"### 🏢 {html.escape(str(name))}"
                    )

                    st.caption(
                        f"📍 يبعد {distance_text}"
                    )

                    m1, m2, m3, m4 = st.columns(4)

                    m1.metric(
                        "🚪 مداخل",
                        len(
                            indoor.get(
                                "entrances",
                                []
                            )
                        )
                    )

                    m2.metric(
                        "🛗 مصاعد",
                        len(
                            indoor.get(
                                "elevators",
                                []
                            )
                        )
                    )

                    m3.metric(
                        "📍 أماكن",
                        len(
                            indoor.get(
                                "rooms",
                                []
                            )
                        )
                    )

                    m4.metric(
                        "🪜 سلالم",
                        len(
                            indoor.get(
                                "stairs",
                                []
                            )
                        )
                    )

                with col_button:

                    if st.button(
                        "🏢 فتح المبنى",
                        key=f"open_building_{index}_{building['id']}",
                        use_container_width=True
                    ):

                        if open_building(
                            building
                        ):

                            st.session_state.page = (
                                "🗺️ الخريطة"
                            )

                            st.rerun()

                        else:

                            st.warning(
                                "تعذر تحميل الخريطة الداخلية."
                            )

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )

    else:

        st.warning(
            f"لم يتم العثور على مبانٍ قابلة للفتح ضمن "
            f"{radius // 1000} كم."
        )

        st.info(
            "جرّب البحث عن منطقة أو مبنى آخر، "
            "أو وسّع نطاق البحث إلى 5 كم. "
            "وجود المبنى في الخريطة لا يعني بالضرورة أن "
            "OpenStreetMap يحتوي على بيانات Indoor له."
        )


# =========================================================
# PAGE 1 - MAP
# =========================================================

else:

    # =====================================================
    # CONTROLS
    # =====================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        if st.button(
            "🟢 نقطة البداية",
            use_container_width=True
        ):

            st.session_state.selection_mode = "start"

    with c2:

        if st.button(
            "🔴 الوجهة",
            use_container_width=True
        ):

            st.session_state.selection_mode = "destination"

    with c3:

        if st.button(
            "🏢 اختيار مبنى",
            use_container_width=True
        ):

            st.session_state.selection_mode = "building"

    with c4:

        if st.button(
            "🗑️ مسح",
            use_container_width=True
        ):

            st.session_state.selection_mode = None

            st.session_state.start_point = None
            st.session_state.destination_point = None

            st.session_state.selected_building = None
            st.session_state.selected_floor = "كل الطوابق"
            st.session_state.indoor_mode = False
            st.session_state.indoor_destination = None

            st.session_state.route_result = None
            st.session_state.ai_answer = None

            st.session_state.map_key += 1

            st.rerun()

    # =====================================================
    # MODE MESSAGE
    # =====================================================

    if st.session_state.selection_mode == "start":

        st.info(
            "🟢 اضغط على الخريطة لتحديد نقطة البداية."
        )

    elif st.session_state.selection_mode == "destination":

        st.info(
            "🔴 اضغط على الخريطة لتحديد الوجهة."
        )

    elif st.session_state.selection_mode == "building":

        st.info(
            "🏢 اضغط على مبنى قابل للفتح أو على مكان مبنى."
        )

    else:

        st.info(
            "استخدم البحث بالأعلى، أو اختر البداية والوجهة، "
            "أو افتح أحد المباني."
        )

    # =====================================================
    # MAP CENTER
    # =====================================================

    if st.session_state.search_center:

        map_center = [
            st.session_state.search_center["lat"],
            st.session_state.search_center["lon"]
        ]

    elif st.session_state.start_point:

        map_center = [
            st.session_state.start_point["lat"],
            st.session_state.start_point["lon"]
        ]

    elif st.session_state.destination_point:

        map_center = [
            st.session_state.destination_point["lat"],
            st.session_state.destination_point["lon"]
        ]

    elif st.session_state.selected_building:

        map_center = [
            st.session_state.selected_building["center"]["lat"],
            st.session_state.selected_building["center"]["lon"]
        ]

    else:

        map_center = [
            21.5433,
            39.1728
        ]

    # =====================================================
    # LOAD OPENABLE BUILDINGS FOR MAP
    # =====================================================

    map_radius = 3000

    building_key = (
        round(map_center[0], 5),
        round(map_center[1], 5),
        map_radius
    )

    if (
        st.session_state.buildings_loaded_key
        != building_key
    ):

        with st.spinner(
            "جاري تجهيز المباني القابلة للفتح..."
        ):

            st.session_state.openable_buildings = (
                get_openable_buildings(
                    map_center[0],
                    map_center[1],
                    map_radius
                )
            )

        st.session_state.buildings_loaded_key = (
            building_key
        )

    openable_buildings = (
        st.session_state.openable_buildings
    )

    # =====================================================
    # OUTDOOR MAP
    # =====================================================

    outdoor_map = folium.Map(
        location=map_center,
        zoom_start=14,
        tiles="OpenStreetMap",
        control_scale=True
    )

    # Search center

    if st.session_state.search_center:

        folium.Marker(
            [
                st.session_state.search_center["lat"],
                st.session_state.search_center["lon"]
            ],
            tooltip="📍 موقع البحث",
            popup=folium.Popup(
                html.escape(
                    st.session_state.search_center_name
                    or "موقع البحث"
                ),
                max_width=350
            ),
            icon=folium.Icon(
                color="blue",
                icon="search",
                prefix="fa"
            )
        ).add_to(
            outdoor_map
        )

    # -----------------------------------------------------
    # BUILDING MARKERS
    # -----------------------------------------------------

    cluster = MarkerCluster().add_to(
        outdoor_map
    )

    for building in openable_buildings:

        name = building_name(
            building
        )

        indoor = building.get(
            "indoor",
            {}
        )

        popup = f"""
        <div style="font-family:Arial;min-width:220px">
            <b>🏢 {html.escape(str(name))}</b><br><br>
            🚪 المداخل: {len(indoor.get("entrances", []))}<br>
            🛗 المصاعد: {len(indoor.get("elevators", []))}<br>
            📍 الأماكن: {len(indoor.get("rooms", []))}<br>
            🪜 السلالم: {len(indoor.get("stairs", []))}<br>
            🚻 دورات المياه: {len(indoor.get("toilets", []))}
        </div>
        """

        folium.Marker(
            location=[
                building["lat"],
                building["lon"]
            ],
            tooltip=f"🏢 {name}",
            popup=folium.Popup(
                popup,
                max_width=320
            ),
            icon=folium.Icon(
                color="purple",
                icon="building",
                prefix="fa"
            )
        ).add_to(
            cluster
        )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    if st.session_state.start_point:

        point = st.session_state.start_point

        folium.Marker(
            [
                point["lat"],
                point["lon"]
            ],
            tooltip="🟢 نقطة البداية",
            popup="🟢 نقطة البداية",
            icon=folium.Icon(
                color="green",
                icon="play",
                prefix="fa"
            )
        ).add_to(
            outdoor_map
        )

    # -----------------------------------------------------
    # DESTINATION
    # -----------------------------------------------------

    if st.session_state.destination_point:

        point = st.session_state.destination_point

        folium.Marker(
            [
                point["lat"],
                point["lon"]
            ],
            tooltip="🔴 الوجهة",
            popup="🔴 الوجهة",
            icon=folium.Icon(
                color="red",
                icon="flag",
                prefix="fa"
            )
        ).add_to(
            outdoor_map
        )

    # -----------------------------------------------------
    # SELECTED BUILDING
    # -----------------------------------------------------

    if (
        st.session_state.selected_building
        and st.session_state.selected_building.get(
            "geometry"
        )
    ):

        draw_polygon(
            outdoor_map,
            st.session_state.selected_building["geometry"],
            color="#7657ff",
            fill=True,
            fill_opacity=0.25,
            weight=4,
            tooltip="🏢 المبنى المحدد"
        )

    # =====================================================
    # MAP
    # =====================================================

    map_data = st_folium(
        outdoor_map,
        width=None,
        height=620,
        returned_objects=[
            "last_clicked",
            "last_object_clicked",
            "last_object_clicked_tooltip"
        ],
        key=f"outdoor_map_{st.session_state.map_key}"
    )

    # =====================================================
    # BUILDING MARKER CLICK
    # =====================================================

    if map_data:

        object_clicked = map_data.get(
            "last_object_clicked"
        )

        object_tooltip = map_data.get(
            "last_object_clicked_tooltip"
        )

        if object_clicked:

            clicked_lat = float(
                object_clicked["lat"]
            )

            clicked_lon = float(
                object_clicked["lng"]
            )

            closest = None
            closest_distance = float("inf")

            for building in openable_buildings:

                d = distance_meters(
                    clicked_lat,
                    clicked_lon,
                    building["lat"],
                    building["lon"]
                )

                if d < closest_distance:

                    closest_distance = d
                    closest = building

            if (
                closest
                and (
                    object_tooltip
                    and object_tooltip.startswith("🏢")
                    or closest_distance < 100
                )
            ):

                with st.spinner(
                    "🏢 جاري فتح المبنى..."
                ):

                    if open_building(
                        closest
                    ):

                        st.rerun()

    # =====================================================
    # NORMAL MAP CLICK
    # =====================================================

    if (
        map_data
        and map_data.get("last_clicked")
        and not map_data.get("last_object_clicked")
        and st.session_state.selection_mode
    ):

        clicked = map_data[
            "last_clicked"
        ]

        lat = float(
            clicked["lat"]
        )

        lon = float(
            clicked["lng"]
        )

        # -------------------------------------------------
        # START
        # -------------------------------------------------

        if st.session_state.selection_mode == "start":

            st.session_state.start_point = {
                "lat": lat,
                "lon": lon,
                "name": reverse_geocode(
                    lat,
                    lon
                )
            }

            st.session_state.selection_mode = None
            st.session_state.route_result = None
            st.session_state.map_key += 1

            st.rerun()

        # -------------------------------------------------
        # DESTINATION
        # -------------------------------------------------

        elif st.session_state.selection_mode == "destination":

            st.session_state.destination_point = {
                "lat": lat,
                "lon": lon,
                "name": reverse_geocode(
                    lat,
                    lon
                )
            }

            st.session_state.selection_mode = None
            st.session_state.route_result = None
            st.session_state.map_key += 1

            st.rerun()

        # -------------------------------------------------
        # BUILDING
        # -------------------------------------------------

        elif st.session_state.selection_mode == "building":

            with st.spinner(
                "🏢 البحث عن المبنى..."
            ):

                building = get_building_at_point(
                    lat,
                    lon
                )

                if building:

                    building = load_building_indoor(
                        building
                    )

                    if has_indoor_information(
                        building.get(
                            "indoor",
                            {}
                        )
                    ):

                        st.session_state.selected_building = (
                            building
                        )

                        st.session_state.indoor_mode = True

                        levels = building[
                            "indoor"
                        ].get(
                            "levels",
                            []
                        )

                        st.session_state.selected_floor = (
                            levels[0]
                            if levels
                            else "كل الطوابق"
                        )

                        st.session_state.selection_mode = None
                        st.session_state.map_key += 1

                        st.rerun()

                    else:

                        st.warning(
                            "المبنى موجود، لكن لا توجد له "
                            "بيانات داخلية كافية."
                        )

                else:

                    st.warning(
                        "لم يتم العثور على مبنى في هذا المكان."
                    )

    # =====================================================
    # LOCATIONS
    # =====================================================

    st.subheader(
        "📌 المواقع المحددة"
    )

    left, right = st.columns(2)

    with left:

        if st.session_state.start_point:

            st.success(
                "🟢 البداية\n\n"
                + st.session_state.start_point["name"]
            )

        else:

            st.info(
                "لم يتم اختيار نقطة البداية."
            )

    with right:

        if st.session_state.destination_point:

            st.error(
                "🔴 الوجهة\n\n"
                + st.session_state.destination_point["name"]
            )

        else:

            st.info(
                "لم يتم اختيار الوجهة."
            )

    # =====================================================
    # BUILDING PANEL
    # =====================================================

    building = (
        st.session_state.selected_building
    )

    if building:

        tags = building.get(
            "tags",
            {}
        )

        indoor = building.get(
            "indoor",
            {}
        )

        name = building_name(
            building
        )

        st.divider()

        st.header(
            f"🏢 {name}"
        )

        st.success(
            "هذا المبنى يحتوي على بيانات داخلية متاحة."
        )

        s1, s2, s3, s4 = st.columns(4)

        s1.metric(
            "🚪 المداخل",
            len(indoor["entrances"])
        )

        s2.metric(
            "🛗 المصاعد",
            len(indoor["elevators"])
        )

        s3.metric(
            "📍 الأماكن",
            len(indoor["rooms"])
        )

        s4.metric(
            "🪜 السلالم",
            len(indoor["stairs"])
        )

        levels = indoor.get(
            "levels",
            []
        )

        floor_options = (
            ["كل الطوابق"] + levels
            if levels
            else ["كل الطوابق"]
        )

        current_floor = (
            st.session_state.selected_floor
        )

        if current_floor not in floor_options:
            current_floor = floor_options[0]

        selected_floor = st.selectbox(
            "🏷️ اختر الطابق",
            floor_options,
            index=floor_options.index(
                current_floor
            )
        )

        st.session_state.selected_floor = selected_floor

        if st.button(
            "🗺️ فتح الخريطة الداخلية",
            use_container_width=True
        ):

            st.session_state.indoor_mode = True
            st.session_state.map_key += 1
            st.rerun()

    # =====================================================
    # INDOOR MAP
    # =====================================================

    if (
        building
        and st.session_state.indoor_mode
    ):

        indoor = building["indoor"]
        selected_floor = (
            st.session_state.selected_floor
        )

        st.divider()

        st.header(
            "🏢 الخريطة الداخلية"
        )

        if selected_floor == "كل الطوابق":

            st.caption(
                "جميع البيانات الداخلية المتوفرة."
            )

        else:

            st.caption(
                f"الطابق: {selected_floor}"
            )

        indoor_map = folium.Map(
            location=[
                building["center"]["lat"],
                building["center"]["lon"]
            ],
            zoom_start=19,
            tiles="OpenStreetMap",
            control_scale=True
        )

        if building.get("geometry"):

            draw_polygon(
                indoor_map,
                building["geometry"],
                color="#7657ff",
                fill=True,
                fill_opacity=0.10,
                weight=3,
                tooltip="🏢 المبنى"
            )

        # -------------------------------------------------
        # ENTRANCES
        # -------------------------------------------------

        for point in indoor["entrances"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue

            level = point["tags"].get(
                "level",
                "غير محدد"
            )

            wheelchair = point["tags"].get(
                "wheelchair",
                "غير محدد"
            )

            folium.Marker(
                [
                    point["lat"],
                    point["lon"]
                ],
                tooltip="🚪 مدخل",
                popup=folium.Popup(
                    "<b>🚪 مدخل</b><br>"
                    f"الطابق: {html.escape(str(level))}<br>"
                    f"الوصول: {html.escape(str(wheelchair))}",
                    max_width=300
                ),
                icon=folium.Icon(
                    color="green",
                    icon="sign-in",
                    prefix="fa"
                )
            ).add_to(
                indoor_map
            )

        # -------------------------------------------------
        # ELEVATORS
        # -------------------------------------------------

        for point in indoor["elevators"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue

            level = point["tags"].get(
                "level",
                "غير محدد"
            )

            folium.Marker(
                [
                    point["lat"],
                    point["lon"]
                ],
                tooltip="🛗 مصعد",
                popup=folium.Popup(
                    "<b>🛗 مصعد داخلي</b><br>"
                    f"الطابق: {html.escape(str(level))}",
                    max_width=300
                ),
                icon=folium.Icon(
                    color="blue",
                    icon="arrow-up",
                    prefix="fa"
                )
            ).add_to(
                indoor_map
            )

        # -------------------------------------------------
        # STAIRS
        # -------------------------------------------------

        for point in indoor["stairs"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue

            level = point["tags"].get(
                "level",
                "غير محدد"
            )

            folium.Marker(
                [
                    point["lat"],
                    point["lon"]
                ],
                tooltip="🪜 درج",
                popup=folium.Popup(
                    "<b>🪜 درج داخلي</b><br>"
                    f"الطابق: {html.escape(str(level))}",
                    max_width=300
                ),
                icon=folium.Icon(
                    color="red",
                    icon="warning-sign",
                    prefix="glyphicon"
                )
            ).add_to(
                indoor_map
            )

        # -------------------------------------------------
        # ROOMS
        # -------------------------------------------------

        for point in indoor["rooms"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue

            name = (
                point["tags"].get("name")
                or point["tags"].get("ref")
                or "مكان داخلي"
            )

            level = point["tags"].get(
                "level",
                "غير محدد"
            )

            wheelchair = point["tags"].get(
                "wheelchair",
                "غير محدد"
            )

            folium.CircleMarker(
                [
                    point["lat"],
                    point["lon"]
                ],
                radius=7,
                color="#7657ff",
                fill=True,
                fill_opacity=0.9,
                tooltip=f"📍 {name}",
                popup=folium.Popup(
                    "<b>📍 مكان داخلي</b><br>"
                    f"الاسم: {html.escape(str(name))}<br>"
                    f"الطابق: {html.escape(str(level))}<br>"
                    f"الوصول: {html.escape(str(wheelchair))}",
                    max_width=320
                )
            ).add_to(
                indoor_map
            )

        # -------------------------------------------------
        # TOILETS
        # -------------------------------------------------

        for point in indoor["toilets"]:

            if not floor_visible(
                point,
                selected_floor
            ):
                continue

            level = point["tags"].get(
                "level",
                "غير محدد"
            )

            wheelchair = point["tags"].get(
                "wheelchair",
                "غير محدد"
            )

            folium.Marker(
                [
                    point["lat"],
                    point["lon"]
                ],
                tooltip="🚻 دورة مياه",
                popup=folium.Popup(
                    "<b>🚻 دورة مياه</b><br>"
                    f"الطابق: {html.escape(str(level))}<br>"
                    f"الوصول: {html.escape(str(wheelchair))}",
                    max_width=300
                ),
                icon=folium.Icon(
                    color="purple",
                    icon="home",
                    prefix="glyphicon"
                )
            ).add_to(
                indoor_map
            )

        indoor_result = st_folium(
            indoor_map,
            width=None,
            height=650,
            returned_objects=[
                "last_clicked"
            ],
            key=f"indoor_map_{st.session_state.map_key}"
        )

        if (
            indoor_result
            and indoor_result.get("last_clicked")
        ):

            point = indoor_result[
                "last_clicked"
            ]

            st.session_state.indoor_destination = {
                "lat": float(
                    point["lat"]
                ),
                "lon": float(
                    point["lng"]
                ),
                "level": selected_floor
            }

            st.success(
                "📍 تم اختيار نقطة داخل المبنى."
            )

        st.subheader(
            "📋 معلومات المبنى"
        )

        if indoor["levels"]:

            st.write(
                "**الطوابق:** "
                + "، ".join(
                    f"الطابق {x}"
                    for x in indoor["levels"]
                )
            )

        st.write(
            f"🚪 المداخل: {len(indoor['entrances'])}"
        )

        st.write(
            f"🛗 المصاعد: {len(indoor['elevators'])}"
        )

        st.write(
            f"📍 الأماكن الداخلية: {len(indoor['rooms'])}"
        )

        st.write(
            f"🪜 السلالم: {len(indoor['stairs'])}"
        )

        st.write(
            f"🚻 دورات المياه: {len(indoor['toilets'])}"
        )

    # =====================================================
    # OUTDOOR ROUTE
    # =====================================================

    if (
        st.session_state.start_point
        and st.session_state.destination_point
    ):

        st.divider()

        if st.button(
            "🚀 احسب أفضل مسار",
            use_container_width=True
        ):

            with st.spinner(
                "جاري تحليل المسارات..."
            ):

                start = st.session_state.start_point
                destination = (
                    st.session_state.destination_point
                )

                routes = get_routes(
                    start,
                    destination
                )

                accessibility = (
                    get_accessibility_data(
                        destination["lat"],
                        destination["lon"]
                    )
                )

                if routes:

                    scores = []

                    for route in routes:

                        score = score_route(
                            route,
                            accessibility
                        )

                        scores.append(
                            (
                                score,
                                route
                            )
                        )

                    scores.sort(
                        key=lambda x: x[0],
                        reverse=True
                    )

                    best_score, best_route = (
                        scores[0]
                    )

                else:

                    best_score = 0
                    best_route = None

                st.session_state.route_result = {
                    "start": start,
                    "destination": destination,
                    "route": best_route,
                    "score": best_score,
                    "accessibility": accessibility
                }

                st.session_state.ai_answer = None

                st.rerun()

    # =====================================================
    # ROUTE RESULT
    # =====================================================

    route_result = (
        st.session_state.route_result
    )

    if route_result:

        st.divider()

        st.header(
            "🚶 المسار المقترح"
        )

        route = route_result["route"]

        accessibility = route_result[
            "accessibility"
        ]

        score = route_result["score"]

        if route:

            distance_km = (
                route["distance"] / 1000
            )

            minutes = max(
                1,
                round(
                    route["duration"] / 60
                )
            )

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "♿ مؤشر الإتاحة",
                f"{score}%"
            )

            c2.metric(
                "🛣️ المسافة",
                f"{distance_km:.1f} كم"
            )

            c3.metric(
                "⏱️ الوقت",
                f"{minutes} دقيقة"
            )

            c4.metric(
                "🛗 المصاعد",
                len(
                    accessibility[
                        "elevators"
                    ]
                )
            )

            route_map = folium.Map(
                location=[
                    (
                        route_result["start"]["lat"]
                        + route_result["destination"]["lat"]
                    ) / 2,

                    (
                        route_result["start"]["lon"]
                        + route_result["destination"]["lon"]
                    ) / 2
                ],
                zoom_start=15,
                tiles="OpenStreetMap"
            )

            folium.Marker(
                [
                    route_result["start"]["lat"],
                    route_result["start"]["lon"]
                ],
                tooltip="🟢 البداية",
                popup="🟢 البداية",
                icon=folium.Icon(
                    color="green",
                    icon="play",
                    prefix="fa"
                )
            ).add_to(
                route_map
            )

            folium.Marker(
                [
                    route_result["destination"]["lat"],
                    route_result["destination"]["lon"]
                ],
                tooltip="🔴 الوجهة",
                popup="🔴 الوجهة",
                icon=folium.Icon(
                    color="red",
                    icon="flag",
                    prefix="fa"
                )
            ).add_to(
                route_map
            )

            points = [
                [
                    coord[1],
                    coord[0]
                ]
                for coord in route[
                    "geometry"
                ]["coordinates"]
            ]

            folium.PolyLine(
                points,
                color="#7657ff",
                weight=7,
                opacity=0.9,
                tooltip="🟣 المسار المقترح"
            ).add_to(
                route_map
            )

            for point in accessibility["elevators"]:

                folium.Marker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    tooltip="🛗 مصعد",
                    popup="🛗 مصعد مسجل.",
                    icon=folium.Icon(
                        color="blue",
                        icon="arrow-up",
                        prefix="fa"
                    )
                ).add_to(
                    route_map
                )

            for point in accessibility["ramps"]:

                folium.Marker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    tooltip="🛝 منحدر",
                    popup="🛝 منحدر مسجل.",
                    icon=folium.Icon(
                        color="green",
                        icon="road",
                        prefix="fa"
                    )
                ).add_to(
                    route_map
                )

            for point in accessibility["stairs"]:

                folium.Marker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    tooltip="🚫 درج",
                    popup="🚫 درج مسجل.",
                    icon=folium.Icon(
                        color="red",
                        icon="warning-sign",
                        prefix="glyphicon"
                    )
                ).add_to(
                    route_map
                )

            for point in accessibility["wheelchair_yes"]:

                folium.CircleMarker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    radius=7,
                    color="#00a884",
                    fill=True,
                    fill_opacity=0.9,
                    tooltip="♿ وصول مهيأ",
                    popup="♿ وصول مهيأ مسجل."
                ).add_to(
                    route_map
                )

            for point in accessibility["wheelchair_no"]:

                folium.CircleMarker(
                    [
                        point["lat"],
                        point["lon"]
                    ],
                    radius=8,
                    color="#e5484d",
                    fill=True,
                    fill_opacity=0.9,
                    tooltip="⚠️ غير مهيأ",
                    popup="⚠️ غير مهيأ مسجل."
                ).add_to(
                    route_map
                )

            st_folium(
                route_map,
                width=None,
                height=620,
                returned_objects=[],
                key="route_result_map"
            )

            with st.expander(
                "📍 معنى العلامات"
            ):

                st.write(
                    "🏢 **مبنى قابل للفتح** — اضغط عليه لفتح الخريطة الداخلية."
                )

                st.write(
                    "🟣 **المسار المقترح** — الطريق الذي اختاره النظام."
                )

                st.write(
                    "🟢 **البداية** — نقطة الانطلاق."
                )

                st.write(
                    "🔴 **الوجهة** — نقطة الوصول."
                )

                st.write(
                    "🛗 **مصعد** — مصعد مسجل."
                )

                st.write(
                    "🛝 **منحدر** — منحدر مسجل."
                )

                st.write(
                    "♿ **وصول مهيأ** — موقع مسجل كمتاح."
                )

                st.write(
                    "🚫 **درج** — درج مسجل."
                )

                st.write(
                    "⚠️ **غير مهيأ** — موقع مسجل كغير مناسب."
                )

            if (
                score >= 80
                and not accessibility["stairs"]
            ):

                st.success(
                    "♿ المسار يبدو مناسبًا بدرجة جيدة حسب البيانات المتاحة."
                )

            elif accessibility["stairs"]:

                st.warning(
                    "⚠️ توجد درجات مسجلة قرب منطقة المسار."
                )

            else:

                st.info(
                    "بيانات الإتاحة محدودة."
                )

        else:

            st.error(
                "تعذر العثور على مسار."
            )


# =========================================================
# AI
# =========================================================

st.divider()

st.header(
    "✨ VerifyAI"
)

if st.button(
    "✨ تحليل المكان بالذكاء الاصطناعي",
    use_container_width=True
):

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        try:

            api_key = st.secrets[
                "OPENAI_API_KEY"
            ]

        except Exception:

            api_key = None

    if not api_key:

        st.warning(
            "مفتاح OpenAI غير متصل."
        )

    else:

        try:

            from openai import OpenAI

            client = OpenAI(
                api_key=api_key
            )

            building = (
                st.session_state.selected_building
            )

            indoor = (
                building.get(
                    "indoor",
                    {}
                )
                if building
                else {}
            )

            prompt = f"""
أنت VerifyAI Access، مساعد متخصص في الوصول الشامل.

بيانات المبنى:

المداخل:
{len(indoor.get("entrances", []))}

المصاعد:
{len(indoor.get("elevators", []))}

الأماكن الداخلية:
{len(indoor.get("rooms", []))}

السلالم:
{len(indoor.get("stairs", []))}

دورات المياه:
{len(indoor.get("toilets", []))}

الطوابق:
{", ".join(indoor.get("levels", [])) if indoor.get("levels") else "غير متوفرة"}

القواعد:

- لا تخترع أي معلومات.
- لا تقل إن المكان مضمون 100%.
- إذا لم توجد بيانات داخلية كافية، وضح ذلك.
- اشرح للمستخدم العلامات المهمة.
- اذكر أن بيانات OpenStreetMap قد تكون ناقصة.
- أجب بالعربية بشكل واضح.
"""

            response = client.responses.create(
                model=MODEL,
                input=prompt
            )

            st.session_state.ai_answer = (
                response.output_text
            )

        except Exception as error:

            st.error(
                f"حدث خطأ: {error}"
            )


if st.session_state.ai_answer:

    st.info(
        st.session_state.ai_answer
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "VerifyAI Access — Smart Accessibility Navigation"
)

st.caption(
    "الوصول للجميع."
)
