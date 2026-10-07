import os
import math
import html
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

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OSRM_URL = "https://router.project-osrm.org/route/v1/foot"

HEADERS = {
    "User-Agent": "VerifyAI-Access/8.0"
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
        padding-top: 1.5rem;
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

    .openable-card {
        background: white;
        border-radius: 18px;
        padding: 18px;
        border: 2px solid #e5ddff;
        box-shadow: 0 5px 20px rgba(80, 50, 160, 0.07);
        margin-bottom: 12px;
    }

    .openable-badge {
        display: inline-block;
        background: #7657ff;
        color: white;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
    }

    .big-openable-label {
        color: #7657ff;
        font-size: 18px;
        font-weight: 800;
    }

    .search-example {
        background: #f7f4ff;
        border: 1px solid #ded5ff;
        border-radius: 14px;
        padding: 12px 15px;
        margin-top: 8px;
        color: #44356e;
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
    "selection_mode": None,
    "start_point": None,
    "destination_point": None,
    "selected_building": None,
    "selected_floor": None,
    "indoor_mode": False,
    "indoor_destination": None,
    "route_result": None,
    "ai_answer": "",
    "map_key": 0,

    "search_results": [],
    "selected_search_result": None,

    "building_search_center": (21.5433, 39.1728),
    "building_search_radius": 2500,
    "openable_buildings": [],
    "openable_loaded_key": None,

    "search_selection_mode": False,

    "search_query": "",
}

for key, value in defaults.items():
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


def distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000

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

    return 2 * R * math.asin(math.sqrt(a))


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
            data = response.json()
            return data.get("display_name", "موقع محدد")

    except Exception:
        pass

    return "موقع محدد"


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


def point_in_polygon(lat, lon, polygon):
    inside = False

    if not polygon or len(polygon) < 3:
        return False

    j = len(polygon) - 1

    for i in range(len(polygon)):
        yi, xi = polygon[i]
        yj, xj = polygon[j]

        intersect = (
            ((xi > lon) != (xj > lon))
            and
            (
                lat
                < (yj - yi)
                * (lon - xi)
                / ((xj - xi) or 1e-12)
                + yi
            )
        )

        if intersect:
            inside = not inside

        j = i

    return inside


def draw_polygon(points):
    if not points:
        return None

    return [[p[0], p[1]] for p in points]


def element_center(element):
    geometry = element.get("geometry", [])

    if not geometry:
        lat = element.get("lat")
        lon = element.get("lon")

        if lat is not None and lon is not None:
            return float(lat), float(lon)

        return None

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
        return None

    return (
        sum(lats) / len(lats),
        sum(lons) / len(lons)
    )


# =========================================================
# OPENABLE BUILDINGS
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_openable_buildings(lat, lon, radius=2500):

    query = f"""
    [out:json][timeout:90];

    (
      way["building"](around:{radius},{lat},{lon});
      relation["building"](around:{radius},{lat},{lon});

      way["building:part"](around:{radius},{lat},{lon});

      node["indoor"](around:{radius},{lat},{lon});
      way["indoor"](around:{radius},{lat},{lon});
      relation["indoor"](around:{radius},{lat},{lon});

      node["room"](around:{radius},{lat},{lon});
      way["room"](around:{radius},{lat},{lon});

      node["level"](around:{radius},{lat},{lon});
      way["level"](around:{radius},{lat},{lon});

      node["entrance"](around:{radius},{lat},{lon});
      way["entrance"](around:{radius},{lat},{lon});

      node["elevator"](around:{radius},{lat},{lon});
      way["elevator"](around:{radius},{lat},{lon});

      node["highway"="steps"](around:{radius},{lat},{lon});
      way["highway"="steps"](around:{radius},{lat},{lon});

      node["amenity"="toilets"](around:{radius},{lat},{lon});
      way["amenity"="toilets"](around:{radius},{lat},{lon});
    );

    out body geom;
    >;
    out skel qt;
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

        data = response.json()
        elements = data.get("elements", [])

    except Exception:
        return []

    node_lookup = {}

    for element in elements:
        if element.get("type") == "node":
            node_lookup[element.get("id")] = (
                element.get("lat"),
                element.get("lon")
            )

    buildings = []
    building_candidates = []

    indoor_elements = []

    for element in elements:

        tags = element.get("tags", {})
        element_type = element.get("type")

        if (
            tags.get("building")
            or tags.get("building:part")
        ):
            building_candidates.append(element)

        if (
            tags.get("indoor")
            or tags.get("room")
            or tags.get("level")
            or tags.get("entrance")
            or tags.get("elevator")
            or tags.get("highway") == "steps"
            or tags.get("amenity") == "toilets"
        ):
            indoor_elements.append(element)

    # -----------------------------------------------------
    # Create building objects
    # -----------------------------------------------------

    for building in building_candidates:

        tags = building.get("tags", {})

        geometry = building.get("geometry", [])

        polygon = []

        for p in geometry:
            if "lat" in p and "lon" in p:
                polygon.append(
                    (
                        float(p["lat"]),
                        float(p["lon"])
                    )
                )

        if not polygon:

            nodes = building.get("nodes", [])

            for node_id in nodes:
                if node_id in node_lookup:
                    point = node_lookup[node_id]

                    if point[0] is not None:
                        polygon.append(
                            (
                                float(point[0]),
                                float(point[1])
                            )
                        )

        center = element_center(building)

        if not center and polygon:
            center = (
                sum(p[0] for p in polygon) / len(polygon),
                sum(p[1] for p in polygon) / len(polygon)
            )

        if not center:
            continue

        buildings.append(
            {
                "id": f'{building.get("type")}_{building.get("id")}',
                "osm_id": building.get("id"),
                "type": building.get("type"),
                "tags": tags,
                "polygon": polygon,
                "center": center,
                "indoor": [],
                "distance": distance_meters(
                    lat,
                    lon,
                    center[0],
                    center[1]
                )
            }
        )

    # -----------------------------------------------------
    # Match indoor information to buildings
    # -----------------------------------------------------

    for indoor in indoor_elements:

        center = element_center(indoor)

        if not center:
            continue

        closest = None
        closest_distance = float("inf")

        for building in buildings:

            polygon = building.get("polygon", [])

            inside = False

            if polygon:
                inside = point_in_polygon(
                    center[0],
                    center[1],
                    polygon
                )

            if inside:
                closest = building
                closest_distance = 0
                break

            d = distance_meters(
                center[0],
                center[1],
                building["center"][0],
                building["center"][1]
            )

            if d < closest_distance:
                closest_distance = d
                closest = building

        if closest and closest_distance <= 220:
            closest["indoor"].append(indoor)

    # -----------------------------------------------------
    # Only buildings with useful indoor information
    # -----------------------------------------------------

    result = []

    for building in buildings:

        indoor = building["indoor"]

        if not indoor:
            continue

        useful = False

        for item in indoor:

            tags = item.get("tags", {})

            if (
                tags.get("indoor")
                or tags.get("room")
                or tags.get("level")
                or tags.get("entrance")
                or tags.get("elevator")
                or tags.get("highway") == "steps"
                or tags.get("amenity") == "toilets"
            ):
                useful = True
                break

        if useful:
            result.append(building)

    # -----------------------------------------------------
    # Deduplicate nearby building parts
    # -----------------------------------------------------

    unique = {}

    for building in result:

        lat2, lon2 = building["center"]

        key = (
            round(lat2, 4),
            round(lon2, 4)
        )

        if key not in unique:

            unique[key] = building

        else:

            old = unique[key]

            if len(building["indoor"]) > len(old["indoor"]):
                unique[key] = building

    result = list(unique.values())

    result.sort(
        key=lambda x: x["distance"]
    )

    return result


# =========================================================
# BUILDING DATA
# =========================================================

def get_building_name(building):

    tags = building.get("tags", {})

    for key in [
        "name",
        "name:ar",
        "official_name",
        "brand"
    ]:
        if tags.get(key):
            return tags[key]

    return "مبنى قابل للفتح"


def parse_indoor_data(building):

    data = {
        "entrances": [],
        "elevators": [],
        "stairs": [],
        "rooms": [],
        "toilets": [],
        "levels": [],
    }

    levels = set()

    for item in building.get("indoor", []):

        tags = item.get("tags", {})
        center = element_center(item)

        if not center:
            continue

        indoor_type = tags.get("indoor")

        if (
            tags.get("entrance")
            or indoor_type == "entrance"
        ):
            data["entrances"].append(
                {
                    "center": center,
                    "tags": tags
                }
            )

        if (
            tags.get("elevator")
            or indoor_type == "elevator"
        ):
            data["elevators"].append(
                {
                    "center": center,
                    "tags": tags
                }
            )

        if (
            tags.get("highway") == "steps"
            or indoor_type == "steps"
        ):
            data["stairs"].append(
                {
                    "center": center,
                    "tags": tags
                }
            )

        if (
            tags.get("room")
            or indoor_type == "room"
        ):
            data["rooms"].append(
                {
                    "center": center,
                    "tags": tags
                }
            )

        if tags.get("amenity") == "toilets":
            data["toilets"].append(
                {
                    "center": center,
                    "tags": tags
                }
            )

        level = tags.get("level")

        if level is not None:
            levels.add(str(level))

    data["levels"] = sorted(
        levels,
        key=lambda x: (
            safe_float(x, 999),
            x
        )
    )

    return data


def floor_visible(item, selected_floor):

    if selected_floor is None:
        return True

    tags = item.get("tags", {})

    level = tags.get("level")

    if level is None:
        return True

    return str(level) == str(selected_floor)


def get_building_at_point(
    lat,
    lon,
    buildings,
    max_distance=150
):

    nearest = None
    nearest_distance = float("inf")

    for building in buildings:

        polygon = building.get("polygon", [])

        if polygon and point_in_polygon(
            lat,
            lon,
            polygon
        ):
            return building

        center = building.get("center")

        if not center:
            continue

        d = distance_meters(
            lat,
            lon,
            center[0],
            center[1]
        )

        if d < nearest_distance:
            nearest_distance = d
            nearest = building

    if nearest and nearest_distance <= max_distance:
        return nearest

    return None


# =========================================================
# ACCESSIBILITY DATA
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_accessibility_data(lat, lon, radius=500):

    query = f"""
    [out:json][timeout:60];

    (
      nwr["wheelchair"](around:{radius},{lat},{lon});
      nwr["kerb"](around:{radius},{lat},{lon});
      nwr["elevator"](around:{radius},{lat},{lon});
      nwr["highway"="steps"](around:{radius},{lat},{lon});
    );

    out center;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=90
        )

        if not response.ok:
            return []

        return response.json().get(
            "elements",
            []
        )

    except Exception:
        return []


# =========================================================
# ROUTING
# =========================================================

def get_routes(start, destination):

    if not start or not destination:
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
                "alternatives": "true"
            },
            headers=HEADERS,
            timeout=30
        )

        if not response.ok:
            return []

        data = response.json()

        return data.get(
            "routes",
            []
        )

    except Exception:
        return []


def score_route(route):

    distance = route.get(
        "distance",
        0
    )

    duration = route.get(
        "duration",
        0
    )

    return (
        distance
        + duration * 0.5
    )


# =========================================================
# OPEN BUILDING
# =========================================================

def open_building_from_click(building):

    st.session_state.selected_building = building
    st.session_state.selected_floor = None
    st.session_state.indoor_mode = True
    st.session_state.indoor_destination = None
    st.session_state.map_key += 1


def clear_all():

    st.session_state.selection_mode = None
    st.session_state.start_point = None
    st.session_state.destination_point = None
    st.session_state.selected_building = None
    st.session_state.selected_floor = None
    st.session_state.indoor_mode = False
    st.session_state.indoor_destination = None
    st.session_state.route_result = None
    st.session_state.ai_answer = ""
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
            "🏢 المباني القابلة للفتح"
        ],
        index=(
            0
            if st.session_state.page == "🗺️ الخريطة"
            else 1
        )
    )

    st.session_state.page = page


# =========================================================
# PAGE 2
# BUILDINGS
# =========================================================

if st.session_state.page == "🏢 المباني القابلة للفتح":

    st.markdown(
        '<div class="main-title">🏢 المباني القابلة للفتح</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'ابحث عن مكان، اختر موقعًا من الخريطة، أو استخدم أحد الأمثلة الجاهزة.'
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown("### 🔎 البحث عن مكان")

    search_query = st.text_input(
        "اكتب اسم المبنى أو المكان",
        value=st.session_state.search_query,
        placeholder="مثال: Mall of Arabia Jeddah",
        key="place_search_input"
    )

    col1, col2 = st.columns([1, 1])

    with col1:

        if st.button(
            "🔎 بحث عن المكان",
            use_container_width=True
        ):

            st.session_state.search_query = search_query

            results = search_places(
                search_query
            )

            st.session_state.search_results = results

            if results:
                st.session_state.selected_search_result = 0

            else:
                st.warning(
                    "ما لقيت نتائج. جرّب اسم المكان بالإنجليزي أو العربي."
                )

    with col2:

        if st.button(
            "📍 اختيار الموقع من الخريطة",
            use_container_width=True
        ):

            st.session_state.search_selection_mode = True

    # -----------------------------------------------------
    # READY EXAMPLES
    # -----------------------------------------------------

    st.markdown("### 🧪 أمثلة جاهزة للتجربة")

    examples = [
        "Mall of Arabia, Jeddah, Saudi Arabia",
        "Haifaa Mall, Jeddah, Saudi Arabia",
        "Jeddah Mall, Jeddah, Saudi Arabia",
        "Red Sea Mall, Jeddah, Saudi Arabia",
        "Al Salam Mall, Jeddah, Saudi Arabia",
        "King Abdulaziz University, Jeddah, Saudi Arabia",
    ]

    example_choice = st.selectbox(
        "اختر مكانًا للتجربة",
        ["— اختر مثال —"] + examples
    )

    if st.button(
        "🧭 البحث عن المثال",
        use_container_width=True
    ):

        if example_choice != "— اختر مثال —":

            results = search_places(
                example_choice
            )

            st.session_state.search_results = results

            if results:
                st.session_state.selected_search_result = 0

                st.success(
                    f"تم العثور على {len(results)} نتيجة."
                )

            else:

                st.warning(
                    "لم يتم العثور على المكان."
                )

    st.markdown(
        """
        <div class="search-example">
        💡 <b>مهم:</b> الأمثلة تساعدك في تجربة البحث فقط.
        ظهور المكان كمبنى قابل للفتح يعتمد على كمية بيانات
        الخرائط الداخلية الموجودة له في OpenStreetMap.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # SEARCH RESULTS
    # -----------------------------------------------------

    if st.session_state.search_results:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown("### 📍 نتائج البحث")

        labels = []

        for result in st.session_state.search_results:

            name = result.get(
                "display_name",
                "موقع"
            )

            labels.append(name)

        selected_index = st.selectbox(
            "اختر نتيجة",
            range(len(labels)),
            format_func=lambda i: labels[i],
            index=min(
                st.session_state.selected_search_result or 0,
                len(labels) - 1
            )
        )

        selected_result = (
            st.session_state.search_results[
                selected_index
            ]
        )

        lat = safe_float(
            selected_result.get("lat")
        )

        lon = safe_float(
            selected_result.get("lon")
        )

        if lat is not None and lon is not None:

            st.write(
                selected_result.get(
                    "display_name",
                    "الموقع"
                )
            )

            if st.button(
                "📍 استخدام هذا المكان كمركز للبحث",
                use_container_width=True
            ):

                st.session_state.building_search_center = (
                    lat,
                    lon
                )

                st.session_state.search_selection_mode = False
                st.session_state.openable_loaded_key = None

                st.success(
                    "تم اختيار الموقع. يتم الآن البحث عن المباني القابلة للفتح حوله."
                )

                st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    # -----------------------------------------------------
    # MANUAL MAP
    # -----------------------------------------------------

    if st.session_state.search_selection_mode:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 📍 اختر الموقع يدويًا"
        )

        st.info(
            "اضغط على أي مكان في الخريطة لاختياره كمركز للبحث."
        )

        manual_lat, manual_lon = (
            st.session_state.building_search_center
        )

        manual_map = folium.Map(
            location=[
                manual_lat,
                manual_lon
            ],
            zoom_start=15,
            control_scale=True
        )

        folium.Marker(
            [
                manual_lat,
                manual_lon
            ],
            tooltip="الموقع الحالي",
            icon=folium.Icon(
                color="blue",
                icon="crosshairs"
            )
        ).add_to(manual_map)

        manual_map.add_child(
            folium.Circle(
                location=[
                    manual_lat,
                    manual_lon
                ],
                radius=st.session_state.building_search_radius,
                color="#7657ff",
                fill=True,
                fill_opacity=0.08
            )
        )

        manual_result = st_folium(
            manual_map,
            width=None,
            height=450,
            key=f"manual_location_{st.session_state.map_key}"
        )

        clicked = manual_result.get(
            "last_clicked"
        )

        if clicked:

            new_lat = clicked["lat"]
            new_lon = clicked["lng"]

            st.session_state.building_search_center = (
                new_lat,
                new_lon
            )

            st.session_state.search_selection_mode = False
            st.session_state.openable_loaded_key = None

            st.success(
                "تم اختيار الموقع من الخريطة."
            )

            st.rerun()

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    # -----------------------------------------------------
    # RADIUS
    # -----------------------------------------------------

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 🎯 نطاق البحث"
    )

    radius_options = [
        500,
        1000,
        1800,
        2500,
        5000,
        10000
    ]

    current_radius = st.session_state.building_search_radius

    if current_radius not in radius_options:
        current_radius = 2500

    radius_index = radius_options.index(
        current_radius
    )

    radius = st.selectbox(
        "ابحث عن المباني القابلة للفتح ضمن:",
        radius_options,
        index=radius_index,
        format_func=lambda x: f"{x:,} متر"
    )

    if radius != st.session_state.building_search_radius:

        st.session_state.building_search_radius = radius
        st.session_state.openable_loaded_key = None

    center_lat, center_lon = (
        st.session_state.building_search_center
    )

    location_name = reverse_geocode(
        center_lat,
        center_lon
    )

    st.markdown(
        f"""
        <div style="
            background:#f7f5ff;
            border-radius:14px;
            padding:14px;
            margin-top:10px;
        ">
        <b>📍 الموقع المختار:</b><br>
        {html.escape(location_name)}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # LOAD BUILDINGS
    # -----------------------------------------------------

    loaded_key = (
        round(center_lat, 5),
        round(center_lon, 5),
        radius
    )

    if (
        st.session_state.openable_loaded_key
        != loaded_key
    ):

        with st.spinner(
            "🔎 أبحث عن المباني التي تحتوي على بيانات داخلية..."
        ):

            st.session_state.openable_buildings = (
                get_openable_buildings(
                    center_lat,
                    center_lon,
                    radius
                )
            )

        st.session_state.openable_loaded_key = loaded_key

    buildings = st.session_state.openable_buildings

    # -----------------------------------------------------
    # RESULTS INFO
    # -----------------------------------------------------

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🏢 المباني القابلة للفتح",
            len(buildings)
        )

    with col2:
        st.metric(
            "📏 نطاق البحث",
            f"{radius:,} m"
        )

    with col3:
        st.metric(
            "📍 المركز",
            f"{center_lat:.4f}, {center_lon:.4f}"
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # BUILDING MAP
    # -----------------------------------------------------

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 🗺️ المباني على الخريطة"
    )

    building_map = folium.Map(
        location=[
            center_lat,
            center_lon
        ],
        zoom_start=14,
        control_scale=True
    )

    folium.Circle(
        location=[
            center_lat,
            center_lon
        ],
        radius=radius,
        color="#7657ff",
        fill=True,
        fill_opacity=0.05,
        tooltip=f"نطاق البحث: {radius:,} متر"
    ).add_to(building_map)

    folium.Marker(
        [
            center_lat,
            center_lon
        ],
        tooltip="مركز البحث",
        icon=folium.Icon(
            color="blue",
            icon="search"
        )
    ).add_to(building_map)

    for index, building in enumerate(buildings):

        b_lat, b_lon = building["center"]

        name = get_building_name(
            building
        )

        indoor_data = parse_indoor_data(
            building
        )

        popup_html = f"""
        <div style="
            direction:rtl;
            font-family:Arial;
            min-width:200px;
        ">
            <b style="font-size:16px;">
                🏢 {html.escape(name)}
            </b>

            <hr>

            <b>🚪 المداخل:</b>
            {len(indoor_data["entrances"])}<br>

            <b>🛗 المصاعد:</b>
            {len(indoor_data["elevators"])}<br>

            <b>🪜 الدرج:</b>
            {len(indoor_data["stairs"])}<br>

            <b>🚻 دورات المياه:</b>
            {len(indoor_data["toilets"])}<br>

            <b>📏 المسافة:</b>
            {int(building["distance"])} متر
        </div>
        """

        # Purple halo
        folium.CircleMarker(
            location=[
                b_lat,
                b_lon
            ],
            radius=18,
            color="#7657ff",
            fill=True,
            fill_color="#7657ff",
            fill_opacity=0.20,
            weight=2
        ).add_to(building_map)

        # Very obvious purple building marker
        folium.Marker(
            [
                b_lat,
                b_lon
            ],
            tooltip=f"🏢 {name} — اضغط للاختيار",
            popup=folium.Popup(
                popup_html,
                max_width=300
            ),
            icon=folium.DivIcon(
                html="""
                <div style="
                    width:36px;
                    height:36px;
                    border-radius:50%;
                    background:#7657ff;
                    border:4px solid white;
                    box-shadow:0 2px 10px rgba(0,0,0,.30);
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:19px;
                ">
                    🏢
                </div>
                """
            )
        ).add_to(building_map)

    building_map_result = st_folium(
        building_map,
        width=None,
        height=600,
        key=f"openable_buildings_map_{st.session_state.map_key}"
    )

    map_clicked = building_map_result.get(
        "last_clicked"
    )

    if map_clicked:

        clicked_building = get_building_at_point(
            map_clicked["lat"],
            map_clicked["lng"],
            buildings,
            max_distance=180
        )

        if clicked_building:

            st.session_state.building_search_center = (
                clicked_building["center"]
            )

            open_building_from_click(
                clicked_building
            )

            st.session_state.page = "🗺️ الخريطة"

            st.rerun()

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # BUILDING LIST
    # -----------------------------------------------------

    if buildings:

        st.markdown(
            "### 🏢 المباني المتاحة"
        )

        for index, building in enumerate(buildings):

            name = get_building_name(
                building
            )

            indoor_data = parse_indoor_data(
                building
            )

            b_lat, b_lon = building["center"]

            st.markdown(
                f"""
                <div class="openable-card">

                    <span class="openable-badge">
                        قابل للفتح
                    </span>

                    <div class="big-openable-label"
                         style="margin-top:10px;">
                        🏢 {html.escape(name)}
                    </div>

                    <div style="
                        color:#777;
                        font-size:13px;
                        margin-top:6px;
                    ">
                        📍 {b_lat:.5f}, {b_lon:.5f}
                    </div>

                    <div style="
                        margin-top:12px;
                        color:#555;
                    ">
                        🚪 مداخل: {len(indoor_data["entrances"])}
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        🛗 مصاعد: {len(indoor_data["elevators"])}
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        🪜 درج: {len(indoor_data["stairs"])}
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        🚻 دورات مياه: {len(indoor_data["toilets"])}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(
                "🏢 فتح المبنى",
                key=f"open_building_{index}",
                use_container_width=True
            ):

                open_building_from_click(
                    building
                )

                st.session_state.page = "🗺️ الخريطة"

                st.rerun()

    else:

        st.markdown(
            """
            <div class="card">

            <h3>لم يتم العثور على مبانٍ قابلة للفتح</h3>

            <p style="color:#777;">
            هذا لا يعني أن المكان لا يحتوي على مبنى فعلي.
            قد يعني فقط أن OpenStreetMap لا يحتوي حاليًا
            على بيانات داخلية كافية للمبنى.
            </p>

            <p style="color:#7657ff;font-weight:700;">
            جرّب زيادة نطاق البحث أو اختيار مكان آخر.
            </p>

            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# PAGE 1
# MAIN MAP
# =========================================================

else:

    st.markdown(
        '<div class="main-title">♿ VerifyAI Access</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'منصة ذكية للوصول والتنقل داخل وخارج المباني بطريقة أكثر شمولًا.'
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # SELECTED BUILDING HEADER
    # -----------------------------------------------------

    if st.session_state.indoor_mode and st.session_state.selected_building:

        building = st.session_state.selected_building

        building_name = get_building_name(
            building
        )

        st.markdown(
            f"""
            <div class="card">

                <span class="openable-badge">
                    🟣 مبنى قابل للفتح
                </span>

                <h2 style="margin-top:10px;">
                    🏢 {html.escape(building_name)}
                </h2>

                <p style="color:#777;">
                    أنت الآن داخل وضع الخريطة الداخلية للمبنى.
                </p>

            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button(
            "⬅️ العودة للخريطة الخارجية",
            use_container_width=True
        ):

            st.session_state.indoor_mode = False
            st.session_state.selected_building = None
            st.session_state.selected_floor = None
            st.session_state.indoor_destination = None
            st.session_state.map_key += 1

            st.rerun()

    # -----------------------------------------------------
    # MAP CONTROLS
    # -----------------------------------------------------

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        if st.button(
            "🟢 نقطة البداية",
            use_container_width=True
        ):

            st.session_state.selection_mode = "start"

    with col2:

        if st.button(
            "🔴 الوجهة",
            use_container_width=True
        ):

            st.session_state.selection_mode = "destination"

    with col3:

        if st.button(
            "🏢 اختيار مبنى",
            use_container_width=True
        ):

            st.session_state.selection_mode = "building"

    with col4:

        if st.button(
            "🗑️ مسح",
            use_container_width=True
        ):

            clear_all()

            st.rerun()

    if st.session_state.selection_mode:

        mode_text = {
            "start": "🟢 اضغط على الخريطة لاختيار نقطة البداية.",
            "destination": "🔴 اضغط على الخريطة لاختيار الوجهة.",
            "building": "🏢 اضغط على مبنى بنفسجي لاختياره."
        }

        st.info(
            mode_text.get(
                st.session_state.selection_mode,
                ""
            )
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # MAP CENTER
    # -----------------------------------------------------

    if st.session_state.indoor_mode and st.session_state.selected_building:

        center = st.session_state.selected_building[
            "center"
        ]

    elif st.session_state.start_point:

        center = st.session_state.start_point

    elif st.session_state.destination_point:

        center = st.session_state.destination_point

    else:

        center = (
            21.5433,
            39.1728
        )

    map_lat, map_lon = center

    # -----------------------------------------------------
    # MAP
    # -----------------------------------------------------

    main_map = folium.Map(
        location=[
            map_lat,
            map_lon
        ],
        zoom_start=16,
        control_scale=True
    )

    # -----------------------------------------------------
    # OUTDOOR BUILDINGS
    # -----------------------------------------------------

    if not st.session_state.indoor_mode:

        outdoor_buildings = get_openable_buildings(
            map_lat,
            map_lon,
            1800
        )

        for building in outdoor_buildings:

            b_lat, b_lon = building["center"]

            name = get_building_name(
                building
            )

            popup = f"""
            <div style="
                direction:rtl;
                font-family:Arial;
            ">
                <b>🏢 {html.escape(name)}</b>
                <br><br>
                هذا المبنى يحتوي على
                بيانات داخلية في OpenStreetMap.
            </div>
            """

            folium.CircleMarker(
                location=[
                    b_lat,
                    b_lon
                ],
                radius=17,
                color="#7657ff",
                fill=True,
                fill_color="#7657ff",
                fill_opacity=0.20
            ).add_to(main_map)

            folium.Marker(
                [
                    b_lat,
                    b_lon
                ],
                tooltip=f"🏢 {name}",
                popup=folium.Popup(
                    popup,
                    max_width=250
                ),
                icon=folium.DivIcon(
                    html="""
                    <div style="
                        width:34px;
                        height:34px;
                        background:#7657ff;
                        border:4px solid white;
                        border-radius:50%;
                        box-shadow:0 2px 10px rgba(0,0,0,.30);
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        font-size:18px;
                    ">
                        🏢
                    </div>
                    """
                )
            ).add_to(main_map)

    # -----------------------------------------------------
    # SELECTED BUILDING
    # -----------------------------------------------------

    if (
        st.session_state.selected_building
        and st.session_state.indoor_mode
    ):

        building = (
            st.session_state.selected_building
        )

        polygon = building.get(
            "polygon",
            []
        )

        if polygon:

            folium.Polygon(
                locations=polygon,
                color="#7657ff",
                fill=True,
                fill_color="#7657ff",
                fill_opacity=0.12,
                weight=4,
                tooltip="🏢 المبنى المحدد"
            ).add_to(main_map)

        b_lat, b_lon = building["center"]

        folium.Marker(
            [
                b_lat,
                b_lon
            ],
            tooltip="🏢 المبنى المحدد",
            icon=folium.DivIcon(
                html="""
                <div style="
                    width:42px;
                    height:42px;
                    background:#7657ff;
                    border:5px solid white;
                    border-radius:50%;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:22px;
                    box-shadow:0 3px 15px rgba(0,0,0,.35);
                ">
                    🏢
                </div>
                """
            )
        ).add_to(main_map)

    # -----------------------------------------------------
    # START / DESTINATION
    # -----------------------------------------------------

    if st.session_state.start_point:

        folium.Marker(
            st.session_state.start_point,
            tooltip="نقطة البداية",
            icon=folium.Icon(
                color="green",
                icon="play"
            )
        ).add_to(main_map)

    if st.session_state.destination_point:

        folium.Marker(
            st.session_state.destination_point,
            tooltip="الوجهة",
            icon=folium.Icon(
                color="red",
                icon="flag"
            )
        ).add_to(main_map)

    # -----------------------------------------------------
    # INDOOR MAP DATA
    # -----------------------------------------------------

    if (
        st.session_state.indoor_mode
        and st.session_state.selected_building
    ):

        building = (
            st.session_state.selected_building
        )

        indoor_data = parse_indoor_data(
            building
        )

        levels = indoor_data["levels"]

        if levels:

            st.session_state.selected_floor = st.selectbox(
                "📐 الطابق",
                levels,
                index=(
                    levels.index(
                        st.session_state.selected_floor
                    )
                    if st.session_state.selected_floor in levels
                    else 0
                )
            )

        # Entrances
        for item in indoor_data["entrances"]:

            if floor_visible(
                item,
                st.session_state.selected_floor
            ):

                folium.CircleMarker(
                    location=item["center"],
                    radius=7,
                    color="green",
                    fill=True,
                    fill_color="green",
                    fill_opacity=0.85,
                    tooltip="🚪 مدخل"
                ).add_to(main_map)

        # Elevators
        for item in indoor_data["elevators"]:

            if floor_visible(
                item,
                st.session_state.selected_floor
            ):

                folium.CircleMarker(
                    location=item["center"],
                    radius=8,
                    color="blue",
                    fill=True,
                    fill_color="blue",
                    fill_opacity=0.85,
                    tooltip="🛗 مصعد"
                ).add_to(main_map)

        # Stairs
        for item in indoor_data["stairs"]:

            if floor_visible(
                item,
                st.session_state.selected_floor
            ):

                folium.CircleMarker(
                    location=item["center"],
                    radius=7,
                    color="orange",
                    fill=True,
                    fill_color="orange",
                    fill_opacity=0.85,
                    tooltip="🪜 درج"
                ).add_to(main_map)

        # Rooms
        for item in indoor_data["rooms"]:

            if floor_visible(
                item,
                st.session_state.selected_floor
            ):

                room_name = (
                    item["tags"].get(
                        "name"
                    )
                    or item["tags"].get(
                        "ref"
                    )
                    or "غرفة"
                )

                folium.CircleMarker(
                    location=item["center"],
                    radius=6,
                    color="purple",
                    fill=True,
                    fill_color="purple",
                    fill_opacity=0.65,
                    tooltip=f"🚪 {room_name}"
                ).add_to(main_map)

        # Toilets
        for item in indoor_data["toilets"]:

            if floor_visible(
                item,
                st.session_state.selected_floor
            ):

                folium.CircleMarker(
                    location=item["center"],
                    radius=7,
                    color="cadetblue",
                    fill=True,
                    fill_color="cadetblue",
                    fill_opacity=0.85,
                    tooltip="🚻 دورة مياه"
                ).add_to(main_map)

    # -----------------------------------------------------
    # RENDER MAP
    # -----------------------------------------------------

    main_map_result = st_folium(
        main_map,
        width=None,
        height=650,
        key=f"main_map_{st.session_state.map_key}"
    )

    # -----------------------------------------------------
    # HANDLE MAP CLICK
    # -----------------------------------------------------

    clicked = main_map_result.get(
        "last_clicked"
    )

    if clicked:

        click_lat = clicked["lat"]
        click_lon = clicked["lng"]

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

        elif mode == "building":

            buildings = get_openable_buildings(
                click_lat,
                click_lon,
                1800
            )

            building = get_building_at_point(
                click_lat,
                click_lon,
                buildings,
                max_distance=180
            )

            if building:

                open_building_from_click(
                    building
                )

                st.session_state.selection_mode = None

                st.rerun()

            else:

                st.warning(
                    "اضغط قريبًا من علامة 🏢 البنفسجية."
                )

        elif (
            st.session_state.indoor_mode
            and st.session_state.selected_building
        ):

            building = (
                st.session_state.selected_building
            )

            indoor_data = parse_indoor_data(
                building
            )

            nearest = None
            nearest_distance = float("inf")

            all_indoor = (
                indoor_data["entrances"]
                + indoor_data["elevators"]
                + indoor_data["stairs"]
                + indoor_data["rooms"]
                + indoor_data["toilets"]
            )

            for item in all_indoor:

                if not floor_visible(
                    item,
                    st.session_state.selected_floor
                ):
                    continue

                d = distance_meters(
                    click_lat,
                    click_lon,
                    item["center"][0],
                    item["center"][1]
                )

                if d < nearest_distance:

                    nearest_distance = d
                    nearest = item

            if nearest and nearest_distance <= 80:

                st.session_state.indoor_destination = (
                    nearest["center"]
                )

                st.success(
                    "تم اختيار النقطة داخل المبنى."
                )

    # -----------------------------------------------------
    # LOCATION CARDS
    # -----------------------------------------------------

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### 🟢 نقطة البداية")

        if st.session_state.start_point:

            lat, lon = (
                st.session_state.start_point
            )

            st.write(
                reverse_geocode(
                    lat,
                    lon
                )
            )

        else:

            st.caption(
                "لم يتم اختيار نقطة بداية."
            )

    with col2:

        st.markdown("### 🔴 الوجهة")

        if st.session_state.destination_point:

            lat, lon = (
                st.session_state.destination_point
            )

            st.write(
                reverse_geocode(
                    lat,
                    lon
                )
            )

        else:

            st.caption(
                "لم يتم اختيار وجهة."
            )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # BUILDING DETAILS
    # -----------------------------------------------------

    if st.session_state.selected_building:

        building = (
            st.session_state.selected_building
        )

        indoor_data = parse_indoor_data(
            building
        )

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <span class="openable-badge">
                قابل للفتح
            </span>

            <h2>
                🏢 {html.escape(
                    get_building_name(building)
                )}
            </h2>
            """,
            unsafe_allow_html=True
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "🚪 المداخل",
                len(indoor_data["entrances"])
            )

        with c2:
            st.metric(
                "🛗 المصاعد",
                len(indoor_data["elevators"])
            )

        with c3:
            st.metric(
                "🪜 الدرج",
                len(indoor_data["stairs"])
            )

        with c4:
            st.metric(
                "🚻 دورات المياه",
                len(indoor_data["toilets"])
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    # -----------------------------------------------------
    # ROUTE
    # -----------------------------------------------------

    if (
        st.session_state.start_point
        and st.session_state.destination_point
    ):

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 🧭 حساب المسار"
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

                st.session_state.route_result = routes[0]

            else:

                st.warning(
                    "تعذر العثور على مسار."
                )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    # -----------------------------------------------------
    # ROUTE RESULT
    # -----------------------------------------------------

    if st.session_state.route_result:

        route = (
            st.session_state.route_result
        )

        distance = route.get(
            "distance",
            0
        )

        duration = route.get(
            "duration",
            0
        )

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        c1, c2 = st.columns(2)

        with c1:

            st.metric(
                "📏 المسافة",
                f"{distance / 1000:.2f} كم"
            )

        with c2:

            st.metric(
                "⏱️ الوقت التقريبي",
                f"{duration / 60:.0f} دقيقة"
            )

        geometry = (
            route
            .get("geometry", {})
            .get("coordinates", [])
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
                [point[1], point[0]]
                for point in geometry
            ]

            folium.PolyLine(
                route_points,
                weight=6,
                opacity=0.8
            ).add_to(route_map)

            folium.Marker(
                st.session_state.start_point,
                tooltip="البداية",
                icon=folium.Icon(
                    color="green"
                )
            ).add_to(route_map)

            folium.Marker(
                st.session_state.destination_point,
                tooltip="الوجهة",
                icon=folium.Icon(
                    color="red"
                )
            ).add_to(route_map)

            st_folium(
                route_map,
                width=None,
                height=450,
                key=f"route_map_{st.session_state.map_key}"
            )

        st.markdown(
            '</div>',
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
