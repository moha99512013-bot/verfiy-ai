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

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', sans-serif;
}

.stApp {
    background: #f7f7fb;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    font-weight: 800 !important;
}

.main-title {
    font-size: 38px;
    font-weight: 800;
    margin-bottom: 5px;
}

.subtitle {
    color: #666;
    font-size: 15px;
    margin-bottom: 25px;
}

.card {
    background: white;
    border-radius: 18px;
    padding: 20px;
    border: 1px solid #ececf3;
    box-shadow: 0 5px 20px rgba(0,0,0,.04);
    margin-bottom: 18px;
}

.metric-card {
    background: white;
    border-radius: 16px;
    padding: 18px;
    text-align: center;
    border: 1px solid #ececf3;
    box-shadow: 0 4px 16px rgba(0,0,0,.04);
}

.metric-number {
    font-size: 28px;
    font-weight: 800;
    color: #7657ff;
}

.metric-label {
    color: #666;
    font-size: 13px;
}

.openable-card {
    background: white;
    border-radius: 18px;
    padding: 18px;
    border: 2px solid #7657ff;
    box-shadow: 0 5px 20px rgba(118,87,255,.12);
    margin-bottom: 15px;
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

.info-box {
    background: #f0edff;
    border-radius: 14px;
    padding: 15px;
    border: 1px solid #ded7ff;
    margin-bottom: 18px;
}

.search-result-card {
    background: white;
    border-radius: 15px;
    padding: 15px;
    border: 1px solid #ececf3;
    margin-bottom: 10px;
}

.big-openable-label {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: #7657ff;
    color: white;
    padding: 8px 15px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 800;
    box-shadow: 0 4px 12px rgba(118,87,255,.25);
}

.footer {
    text-align: center;
    color: #999;
    margin-top: 40px;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)


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
    "ai_answer": None,

    "map_key": 0,

    "search_results": [],
    "selected_search_result": None,

    "building_search_center": None,
    "building_search_radius": 2500,

    "openable_buildings": [],
    "openable_loaded_key": None,

    "search_selection_mode": False
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# BASIC HELPERS
# =========================================================

def safe_float(value):

    try:
        return float(value)
    except:
        return None


def distance_meters(lat1, lon1, lat2, lon2):

    R = 6371000

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )


def reverse_geocode(lat, lon):

    try:

        response = requests.get(
            f"{NOMINATIM_URL}/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "zoom": 18
            },
            headers=HEADERS,
            timeout=15
        )

        if response.status_code != 200:
            return f"{lat:.5f}, {lon:.5f}"

        data = response.json()

        return data.get(
            "display_name",
            f"{lat:.5f}, {lon:.5f}"
        )

    except:

        return f"{lat:.5f}, {lon:.5f}"


# =========================================================
# SEARCH PLACES
# =========================================================

def search_places(query):

    if not query or not query.strip():
        return []

    try:

        response = requests.get(
            f"{NOMINATIM_URL}/search",
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 10,
                "addressdetails": 1
            },
            headers=HEADERS,
            timeout=15
        )

        if response.status_code != 200:
            return []

        return response.json()

    except:

        return []


# =========================================================
# POLYGON HELPERS
# =========================================================

def point_in_polygon(lat, lon, polygon):

    if not polygon or len(polygon) < 3:
        return False

    x = lon
    y = lat

    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):

        xi = polygon[i][1]
        yi = polygon[i][0]

        xj = polygon[j][1]
        yj = polygon[j][0]

        denominator = yj - yi

        if denominator == 0:
            denominator = 0.0000001

        intersect = (
            ((yi > y) != (yj > y))
            and
            (
                x <
                (xj - xi)
                * (y - yi)
                / denominator
                + xi
            )
        )

        if intersect:
            inside = not inside

        j = i

    return inside


def draw_polygon(element):

    geometry = element.get(
        "geometry",
        []
    )

    points = []

    for point in geometry:

        lat = safe_float(
            point.get("lat")
        )

        lon = safe_float(
            point.get("lon")
        )

        if lat is not None and lon is not None:

            points.append(
                [lat, lon]
            )

    return points


def element_center(element, node_lookup):

    # Node
    if element.get("type") == "node":

        lat = safe_float(
            element.get("lat")
        )

        lon = safe_float(
            element.get("lon")
        )

        if lat is not None and lon is not None:

            return lat, lon

    # Geometry
    geometry = draw_polygon(
        element
    )

    if geometry:

        lat = sum(
            p[0] for p in geometry
        ) / len(geometry)

        lon = sum(
            p[1] for p in geometry
        ) / len(geometry)

        return lat, lon

    # Way node references
    nodes = element.get(
        "nodes",
        []
    )

    points = []

    for node_id in nodes:

        point = node_lookup.get(
            node_id
        )

        if point:
            points.append(
                point
            )

    if points:

        lat = sum(
            p[0] for p in points
        ) / len(points)

        lon = sum(
            p[1] for p in points
        ) / len(points)

        return lat, lon

    return None, None


# =========================================================
# OPENABLE BUILDINGS
# =========================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
def get_openable_buildings(
    lat,
    lon,
    radius=2500
):

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

        if response.status_code != 200:
            return []

        data = response.json()

        elements = data.get(
            "elements",
            []
        )

        # -------------------------------------------------
        # NODE LOOKUP
        # -------------------------------------------------

        node_lookup = {}

        for element in elements:

            if element.get("type") == "node":

                node_id = element.get("id")

                lat_value = safe_float(
                    element.get("lat")
                )

                lon_value = safe_float(
                    element.get("lon")
                )

                if (
                    node_id is not None
                    and lat_value is not None
                    and lon_value is not None
                ):

                    node_lookup[node_id] = (
                        lat_value,
                        lon_value
                    )

        # -------------------------------------------------
        # BUILDINGS
        # -------------------------------------------------

        building_elements = []

        indoor_elements = []

        for element in elements:

            tags = element.get(
                "tags",
                {}
            )

            if (
                tags.get("building")
                or tags.get("building:part")
            ):

                building_elements.append(
                    element
                )

            elif any([
                tags.get("indoor"),
                tags.get("room"),
                tags.get("level"),
                tags.get("entrance"),
                tags.get("elevator"),
                tags.get("highway") == "steps",
                tags.get("amenity") == "toilets"
            ]):

                indoor_elements.append(
                    element
                )

        # -------------------------------------------------
        # BUILDING DATA
        # -------------------------------------------------

        building_data = []

        for building in building_elements:

            tags = building.get(
                "tags",
                {}
            )

            geometry = draw_polygon(
                building
            )

            # Fallback to node references
            if not geometry:

                nodes = building.get(
                    "nodes",
                    []
                )

                for node_id in nodes:

                    point = node_lookup.get(
                        node_id
                    )

                    if point:

                        geometry.append([
                            point[0],
                            point[1]
                        ])

            center_lat = None
            center_lon = None

            if geometry:

                center_lat = sum(
                    p[0]
                    for p in geometry
                ) / len(geometry)

                center_lon = sum(
                    p[1]
                    for p in geometry
                ) / len(geometry)

            else:

                center_lat, center_lon = (
                    element_center(
                        building,
                        node_lookup
                    )
                )

            if (
                center_lat is None
                or center_lon is None
            ):
                continue

            building_data.append({
                "id": (
                    f"{building.get('type')}_"
                    f"{building.get('id')}"
                ),
                "osm_id": building.get("id"),
                "type": building.get("type"),
                "lat": center_lat,
                "lon": center_lon,
                "geometry": geometry,
                "tags": tags,
                "indoor_elements": []
            })

        # -------------------------------------------------
        # MATCH INDOOR DATA TO BUILDINGS
        # -------------------------------------------------

        for indoor in indoor_elements:

            tags = indoor.get(
                "tags",
                {}
            )

            point_lat, point_lon = (
                element_center(
                    indoor,
                    node_lookup
                )
            )

            if (
                point_lat is None
                or point_lon is None
            ):
                continue

            matched_building = None
            best_distance = float("inf")

            # -------------------------------------------------
            # FIRST: INSIDE BUILDING FOOTPRINT
            # -------------------------------------------------

            containing_buildings = []

            for building in building_data:

                geometry = building.get(
                    "geometry",
                    []
                )

                if not geometry:
                    continue

                if point_in_polygon(
                    point_lat,
                    point_lon,
                    geometry
                ):

                    containing_buildings.append(
                        building
                    )

            if containing_buildings:

                # Choose smallest footprint / nearest center
                containing_buildings.sort(
                    key=lambda b:
                    distance_meters(
                        point_lat,
                        point_lon,
                        b["lat"],
                        b["lon"]
                    )
                )

                matched_building = (
                    containing_buildings[0]
                )

            # -------------------------------------------------
            # SECOND: NEAREST BUILDING
            # -------------------------------------------------

            if matched_building is None:

                for building in building_data:

                    d = distance_meters(
                        point_lat,
                        point_lon,
                        building["lat"],
                        building["lon"]
                    )

                    if d < best_distance:

                        best_distance = d
                        matched_building = building

                # Allow reasonable fallback
                if (
                    matched_building is None
                    or best_distance > 220
                ):

                    matched_building = None

            # -------------------------------------------------
            # SAVE MATCH
            # -------------------------------------------------

            if matched_building:

                matched_building[
                    "indoor_elements"
                ].append({
                    "element": indoor,
                    "lat": point_lat,
                    "lon": point_lon,
                    "tags": tags
                })

        # -------------------------------------------------
        # KEEP USEFUL BUILDINGS
        # -------------------------------------------------

        result = []

        for building in building_data:

            indoor_items = building.get(
                "indoor_elements",
                []
            )

            if not indoor_items:
                continue

            useful = False

            for item in indoor_items:

                tags = item.get(
                    "tags",
                    {}
                )

                if any([
                    tags.get("indoor"),
                    tags.get("room"),
                    tags.get("level"),
                    tags.get("entrance"),
                    tags.get("elevator"),
                    tags.get("highway") == "steps",
                    tags.get("amenity") == "toilets"
                ]):

                    useful = True
                    break

            if not useful:
                continue

            building["distance"] = (
                distance_meters(
                    lat,
                    lon,
                    building["lat"],
                    building["lon"]
                )
            )

            result.append(
                building
            )

        # -------------------------------------------------
        # REMOVE DUPLICATES
        # -------------------------------------------------

        unique = {}

        for building in result:

            key = (
                round(
                    building["lat"],
                    5
                ),
                round(
                    building["lon"],
                    5
                )
            )

            if key not in unique:

                unique[key] = building

            else:

                # Merge indoor elements if duplicate
                old = unique[key]

                old_elements = old.get(
                    "indoor_elements",
                    []
                )

                new_elements = building.get(
                    "indoor_elements",
                    []
                )

                old["indoor_elements"] = (
                    old_elements
                    + new_elements
                )

        result = list(
            unique.values()
        )

        result.sort(
            key=lambda x:
            x.get(
                "distance",
                999999999
            )
        )

        return result

    except Exception:

        return []


# =========================================================
# BUILDING DATA
# =========================================================

def has_indoor_information(
    building
):

    if not building:
        return False

    return bool(
        building.get(
            "indoor_elements",
            []
        )
    )


def get_indoor_data(
    building
):

    if not building:
        return []

    return building.get(
        "indoor_elements",
        []
    )


def parse_indoor_data(
    building
):

    data = get_indoor_data(
        building
    )

    result = {
        "entrances": [],
        "elevators": [],
        "stairs": [],
        "rooms": [],
        "toilets": [],
        "levels": []
    }

    for item in data:

        tags = item.get(
            "tags",
            {}
        )

        lat = item.get(
            "lat"
        )

        lon = item.get(
            "lon"
        )

        if (
            lat is None
            or lon is None
        ):
            continue

        # -------------------------------------------------
        # ENTRANCE
        # -------------------------------------------------

        if tags.get("entrance"):

            result["entrances"].append({
                "lat": lat,
                "lon": lon,
                "tags": tags
            })

        # -------------------------------------------------
        # ELEVATOR
        # -------------------------------------------------

        if (
            tags.get("elevator")
            or tags.get("highway") == "elevator"
        ):

            result["elevators"].append({
                "lat": lat,
                "lon": lon,
                "tags": tags
            })

        # -------------------------------------------------
        # STAIRS
        # -------------------------------------------------

        if (
            tags.get("highway") == "steps"
            or tags.get("indoor") == "stairs"
        ):

            result["stairs"].append({
                "lat": lat,
                "lon": lon,
                "tags": tags
            })

        # -------------------------------------------------
        # ROOMS
        # -------------------------------------------------

        if (
            tags.get("room")
            or tags.get("indoor") == "room"
        ):

            result["rooms"].append({
                "lat": lat,
                "lon": lon,
                "tags": tags
            })

        # -------------------------------------------------
        # TOILETS
        # -------------------------------------------------

        if tags.get(
            "amenity"
        ) == "toilets":

            result["toilets"].append({
                "lat": lat,
                "lon": lon,
                "tags": tags
            })

        # -------------------------------------------------
        # LEVELS
        # -------------------------------------------------

        if tags.get("level"):

            level_value = tags.get(
                "level"
            )

            result["levels"].append(
                str(level_value)
            )

    result["levels"] = sorted(
        list(
            set(
                result["levels"]
            )
        ),
        key=lambda x: str(x)
    )

    return result


def floor_visible(
    item,
    selected_floor
):

    if selected_floor is None:
        return True

    tags = item.get(
        "tags",
        {}
    )

    level = tags.get(
        "level"
    )

    if level is None:
        return True

    return str(level) == str(
        selected_floor
    )


def get_building_name(
    building,
    fallback="مبنى قابل للفتح"
):

    tags = building.get(
        "tags",
        {}
    )

    return (
        tags.get("name")
        or tags.get("official_name")
        or tags.get("building")
        or tags.get("building:use")
        or fallback
    )


# =========================================================
# BUILDING AT MAP POINT
# =========================================================

def get_building_at_point(
    lat,
    lon,
    buildings,
    max_distance=120
):

    nearest = None
    nearest_distance = float(
        "inf"
    )

    # First try polygon
    for building in buildings:

        geometry = building.get(
            "geometry",
            []
        )

        if geometry:

            if point_in_polygon(
                lat,
                lon,
                geometry
            ):

                return building

    # Fallback nearest center
    for building in buildings:

        d = distance_meters(
            lat,
            lon,
            building["lat"],
            building["lon"]
        )

        if d < nearest_distance:

            nearest_distance = d
            nearest = building

    if (
        nearest
        and nearest_distance <= max_distance
    ):

        return nearest

    return None


# =========================================================
# ACCESSIBILITY DATA
# =========================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
def get_accessibility_data(
    lat,
    lon,
    radius=700
):

    query = f"""
    [out:json][timeout:40];

    (
        node["wheelchair"](around:{radius},{lat},{lon});
        way["wheelchair"](around:{radius},{lat},{lon});

        node["kerb"](around:{radius},{lat},{lon});
        way["kerb"](around:{radius},{lat},{lon});

        node["elevator"](around:{radius},{lat},{lon});
        node["highway"="steps"](around:{radius},{lat},{lon});
    );

    out center;
    """

    try:

        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=60
        )

        if response.status_code != 200:
            return []

        return response.json().get(
            "elements",
            []
        )

    except:

        return []


# =========================================================
# ROUTES
# =========================================================

def get_routes(
    start_lat,
    start_lon,
    end_lat,
    end_lon
):

    url = (
        f"{OSRM_URL}/"
        f"{start_lon},{start_lat};"
        f"{end_lon},{end_lat}"
    )

    try:

        response = requests.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
                "alternatives": "true",
                "steps": "true"
            },
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:
            return []

        data = response.json()

        return data.get(
            "routes",
            []
        )

    except:

        return []


def score_route(
    route
):

    distance = route.get(
        "distance",
        0
    )

    duration = route.get(
        "duration",
        0
    )

    score = 100

    score -= min(
        distance / 1000 * 3,
        25
    )

    score -= min(
        duration / 60 * 0.4,
        15
    )

    return max(
        0,
        round(score)
    )


# =========================================================
# OPEN BUILDING
# =========================================================

def open_building_from_click(
    building
):

    if not building:
        return

    st.session_state.selected_building = (
        building
    )

    st.session_state.selected_floor = None

    st.session_state.indoor_mode = True

    st.session_state.map_key += 1


# =========================================================
# CLEAR ALL
# =========================================================

def clear_all():

    st.session_state.selection_mode = None

    st.session_state.start_point = None
    st.session_state.destination_point = None

    st.session_state.selected_building = None
    st.session_state.selected_floor = None

    st.session_state.indoor_mode = False
    st.session_state.indoor_destination = None

    st.session_state.route_result = None
    st.session_state.ai_answer = None

    st.session_state.map_key += 1


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        "## ♿ VerifyAI Access"
    )

    st.caption(
        "الوصول الذكي للمباني والمسارات"
    )

    st.markdown("---")

    page = st.radio(
        "التنقل",
        [
            "🗺️ الخريطة",
            "🏢 المباني القابلة للفتح"
        ],
        index=(
            0
            if st.session_state.page
            == "🗺️ الخريطة"
            else 1
        )
    )

    st.session_state.page = page

    st.markdown("---")

    st.markdown(
        """
        **الفكرة**

        يساعدك VerifyAI Access
        على اكتشاف المباني التي تحتوي
        على معلومات داخلية على الخريطة،
        ثم استعراض المداخل والغرف
        والمصاعد والسلالم والطوابق.
        """
    )


# =========================================================
# PAGE 2
# OPENABLE BUILDINGS
# =========================================================

if (
    st.session_state.page
    == "🏢 المباني القابلة للفتح"
):

    st.markdown(
        '<div class="main-title">'
        '🏢 المباني القابلة للفتح'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'ابحث عن أي مكان ثم اعرض المباني التي تحتوي على معلومات داخلية متاحة على الخريطة.'
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

    st.markdown(
        "### 🔎 البحث عن مكان"
    )

    search_query = st.text_input(
        "اكتب اسم المبنى أو المكان أو العنوان",
        placeholder=(
            "مثال: جامعة الملك عبدالعزيز، "
            "مول، مستشفى..."
        )
    )

    col1, col2 = st.columns(
        [1, 1]
    )

    with col1:

        if st.button(
            "🔎 بحث",
            use_container_width=True
        ):

            results = search_places(
                search_query
            )

            st.session_state.search_results = (
                results
            )

            st.session_state.selected_search_result = (
                None
            )

    with col2:

        radius_options = [
            500,
            1000,
            1800,
            2500,
            5000,
            10000
        ]

        current_radius = (
            st.session_state
            .building_search_radius
        )

        if current_radius in radius_options:

            radius_index = radius_options.index(
                current_radius
            )

        else:

            radius_index = 3

        radius = st.selectbox(
            "نطاق البحث",
            radius_options,
            index=radius_index,
            format_func=lambda x:
                f"{x:,} متر"
        )

        if radius != st.session_state.building_search_radius:

            st.session_state.building_search_radius = (
                radius
            )

            st.session_state.openable_loaded_key = None

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # SEARCH RESULTS
    # -----------------------------------------------------

    if st.session_state.search_results:

        st.markdown(
            "### 📍 نتائج البحث"
        )

        names = []

        for i, result in enumerate(
            st.session_state.search_results
        ):

            names.append(
                result.get(
                    "display_name",
                    f"نتيجة {i + 1}"
                )
            )

        selected_index = st.selectbox(
            "اختر الموقع",
            range(len(names)),
            format_func=lambda i:
                names[i]
        )

        selected_result = (
            st.session_state.search_results[
                selected_index
            ]
        )

        st.markdown(
            '<div class="search-result-card">',
            unsafe_allow_html=True
        )

        st.write(
            selected_result.get(
                "display_name",
                "الموقع المختار"
            )
        )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

        if st.button(
            "📍 استخدام هذا الموقع",
            use_container_width=True
        ):

            selected_lat = safe_float(
                selected_result.get(
                    "lat"
                )
            )

            selected_lon = safe_float(
                selected_result.get(
                    "lon"
                )
            )

            if (
                selected_lat is not None
                and selected_lon is not None
            ):

                st.session_state.building_search_center = {
                    "lat": selected_lat,
                    "lon": selected_lon,
                    "name": selected_result.get(
                        "display_name",
                        "الموقع المختار"
                    )
                }

                st.session_state.openable_loaded_key = (
                    None
                )

                st.rerun()

    # -----------------------------------------------------
    # MANUAL LOCATION
    # -----------------------------------------------------

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        "### 📍 اختيار الموقع يدويًا"
    )

    st.write(
        "يمكنك تحديد مركز البحث مباشرة من الخريطة."
    )

    if st.button(
        "📍 تحديد الموقع من الخريطة",
        use_container_width=True
    ):

        st.session_state.search_selection_mode = True

    if st.session_state.search_selection_mode:

        st.info(
            "⬇️ اضغط على أي نقطة في الخريطة بالأسفل لتحديد مركز البحث."
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # DEFAULT CENTER
    # -----------------------------------------------------

    if (
        st.session_state
        .building_search_center
        is None
    ):

        st.session_state.building_search_center = {
            "lat": 21.5433,
            "lon": 39.1728,
            "name": "جدة"
        }

    center = (
        st.session_state
        .building_search_center
    )

    # -----------------------------------------------------
    # LOAD BUILDINGS
    # -----------------------------------------------------

    load_key = (
        round(
            center["lat"],
            5
        ),
        round(
            center["lon"],
            5
        ),
        radius
    )

    if (
        st.session_state.openable_loaded_key
        != load_key
    ):

        with st.spinner(
            "🔎 جاري البحث عن المباني القابلة للفتح..."
        ):

            st.session_state.openable_buildings = (
                get_openable_buildings(
                    center["lat"],
                    center["lon"],
                    radius
                )
            )

        st.session_state.openable_loaded_key = (
            load_key
        )

    buildings = (
        st.session_state.openable_buildings
    )

    # -----------------------------------------------------
    # CENTER INFO
    # -----------------------------------------------------

    st.markdown(
        '<div class="info-box">',
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        **📍 مركز البحث**

        {html.escape(center["name"])}

        **📏 نطاق البحث:** {radius:,} متر

        **🏢 عدد المباني القابلة للفتح:** {len(buildings)}
        """
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # BUILDING MAP
    # -----------------------------------------------------

    building_map = folium.Map(
        location=[
            center["lat"],
            center["lon"]
        ],
        zoom_start=15,
        control_scale=True
    )

    # -----------------------------------------------------
    # SEARCH RADIUS
    # -----------------------------------------------------

    folium.Circle(
        location=[
            center["lat"],
            center["lon"]
        ],
        radius=radius,
        color="#7657ff",
        weight=2,
        fill=False,
        tooltip=f"نطاق البحث: {radius:,} متر"
    ).add_to(
        building_map
    )

    # -----------------------------------------------------
    # CENTER MARKER
    # -----------------------------------------------------

    folium.Marker(
        location=[
            center["lat"],
            center["lon"]
        ],
        tooltip="📍 مركز البحث",
        popup=folium.Popup(
            "📍 مركز البحث",
            max_width=250
        ),
        icon=folium.Icon(
            color="blue",
            icon="crosshairs",
            prefix="fa"
        )
    ).add_to(
        building_map
    )

    # -----------------------------------------------------
    # VERY CLEAR OPENABLE MARKERS
    # -----------------------------------------------------

    for building in buildings:

        building_name = get_building_name(
            building
        )

        indoor_data = parse_indoor_data(
            building
        )

        popup_html = f"""
        <div style="
            font-family:Cairo,Arial;
            text-align:center;
            min-width:230px;
        ">

            <div style="
                background:#7657ff;
                color:white;
                width:62px;
                height:62px;
                border-radius:50%;
                margin:0 auto 10px auto;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:32px;
                border:4px solid white;
                box-shadow:0 5px 18px rgba(118,87,255,.45);
            ">
                🏢
            </div>

            <div style="
                font-size:17px;
                font-weight:800;
                margin-bottom:10px;
            ">
                {html.escape(building_name)}
            </div>

            <div style="
                background:#7657ff;
                color:white;
                padding:8px 14px;
                border-radius:12px;
                font-weight:800;
                display:inline-block;
                margin-bottom:10px;
            ">
                ✓ مبنى قابل للفتح
            </div>

            <div style="
                font-size:13px;
                line-height:1.8;
            ">
                🚪 المداخل:
                {len(indoor_data["entrances"])}
                <br>
                🛗 المصاعد:
                {len(indoor_data["elevators"])}
                <br>
                🪜 السلالم:
                {len(indoor_data["stairs"])}
                <br>
                🚪 الغرف:
                {len(indoor_data["rooms"])}
                <br>
                🚻 دورات المياه:
                {len(indoor_data["toilets"])}
            </div>

            <div style="
                margin-top:10px;
                color:#7657ff;
                font-weight:800;
            ">
                اضغط على المبنى لاختيار موقعه
            </div>

        </div>
        """

        # -------------------------------------------------
        # LARGE HIGHLIGHT
        # -------------------------------------------------

        folium.Circle(
            location=[
                building["lat"],
                building["lon"]
            ],
            radius=45,
            color="#7657ff",
            weight=5,
            fill=True,
            fill_color="#7657ff",
            fill_opacity=0.20,
            tooltip="🏢 مبنى قابل للفتح"
        ).add_to(
            building_map
        )

        # -------------------------------------------------
        # LARGE CLEAR ICON
        # -------------------------------------------------

        folium.Marker(
            location=[
                building["lat"],
                building["lon"]
            ],
            tooltip=(
                "🏢 مبنى قابل للفتح — "
                "اضغط هنا"
            ),
            popup=folium.Popup(
                popup_html,
                max_width=320
            ),
            icon=folium.DivIcon(
                html="""
                <div style="
                    position:relative;
                    width:58px;
                    height:58px;
                    background:#7657ff;
                    color:white;
                    border:5px solid white;
                    border-radius:50%;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:30px;
                    box-shadow:
                        0 5px 20px
                        rgba(118,87,255,.50);
                    transform:
                        translate(-29px,-29px);
                ">
                    🏢
                </div>
                """
            )
        ).add_to(
            building_map
        )

    # -----------------------------------------------------
    # SHOW MAP
    # -----------------------------------------------------

    building_map_result = st_folium(
        building_map,
        width=None,
        height=650,
        key=(
            f"building_page_map_"
            f"{st.session_state.map_key}"
        )
    )

    # -----------------------------------------------------
    # MANUAL MAP SELECTION
    # -----------------------------------------------------

    if (
        st.session_state.search_selection_mode
        and building_map_result
        and building_map_result.get(
            "last_clicked"
        )
    ):

        clicked = (
            building_map_result[
                "last_clicked"
            ]
        )

        clicked_lat = clicked.get(
            "lat"
        )

        clicked_lon = clicked.get(
            "lng"
        )

        if (
            clicked_lat is not None
            and clicked_lon is not None
        ):

            st.session_state.building_search_center = {
                "lat": clicked_lat,
                "lon": clicked_lon,
                "name": reverse_geocode(
                    clicked_lat,
                    clicked_lon
                )
            }

            st.session_state.search_selection_mode = (
                False
            )

            st.session_state.openable_loaded_key = (
                None
            )

            st.rerun()

    # -----------------------------------------------------
    # BUILDING LIST
    # -----------------------------------------------------

    st.markdown(
        "## 🏢 جميع المباني القابلة للفتح"
    )

    if not buildings:

        st.warning(
            "لم يتم العثور على مبانٍ قابلة للفتح في هذا النطاق."
        )

        st.info(
            "جرّب زيادة نطاق البحث إلى 5,000 أو 10,000 متر، "
            "أو ابحث عن منطقة أخرى."
        )

    else:

        for index, building in enumerate(
            buildings
        ):

            building_name = get_building_name(
                building,
                f"مبنى قابل للفتح #{index + 1}"
            )

            indoor_data = parse_indoor_data(
                building
            )

            building_distance = building.get(
                "distance",
                0
            )

            st.markdown(
                '<div class="openable-card">',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(
                [4, 1]
            )

            with col1:

                st.markdown(
                    f"""
                    <div style="
                        font-size:20px;
                        font-weight:800;
                        margin-bottom:8px;
                    ">
                        🏢 {html.escape(building_name)}
                    </div>

                    <span class="openable-badge">
                        ✓ قابل للفتح
                    </span>

                    <div style="
                        margin-top:12px;
                        color:#666;
                        font-size:13px;
                        line-height:1.9;
                    ">

                        📏 يبعد تقريبًا:
                        {round(building_distance)} متر

                        <br>

                        🚪 المداخل:
                        {len(indoor_data["entrances"])}

                        &nbsp;&nbsp;

                        🛗 المصاعد:
                        {len(indoor_data["elevators"])}

                        &nbsp;&nbsp;

                        🪜 السلالم:
                        {len(indoor_data["stairs"])}

                        <br>

                        🚪 الغرف:
                        {len(indoor_data["rooms"])}

                        &nbsp;&nbsp;

                        🚻 دورات المياه:
                        {len(indoor_data["toilets"])}

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col2:

                if st.button(
                    "🏢 فتح المبنى",
                    key=(
                        f"open_building_"
                        f"{index}_"
                        f"{round(building['lat'],5)}_"
                        f"{round(building['lon'],5)}"
                    ),
                    use_container_width=True
                ):

                    st.session_state.selected_building = (
                        building
                    )

                    st.session_state.selected_floor = (
                        None
                    )

                    st.session_state.indoor_mode = (
                        True
                    )

                    st.session_state.page = (
                        "🗺️ الخريطة"
                    )

                    st.session_state.map_key += 1

                    st.rerun()

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )


# =========================================================
# PAGE 1
# MAP
# =========================================================

else:

    st.markdown(
        '<div class="main-title">'
        '♿ VerifyAI Access'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'منصة ذكية للوصول إلى الأماكن والمباني والمسارات المناسبة.'
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # TOP CONTROLS
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(
        [1, 1, 1, 1]
    )

    with c1:

        if st.button(
            "🟢 نقطة البداية",
            use_container_width=True
        ):

            st.session_state.selection_mode = (
                "start"
            )

    with c2:

        if st.button(
            "🔴 الوجهة",
            use_container_width=True
        ):

            st.session_state.selection_mode = (
                "destination"
            )

    with c3:

        if st.button(
            "🏢 اختيار مبنى",
            use_container_width=True
        ):

            st.session_state.selection_mode = (
                "building"
            )

    with c4:

        if st.button(
            "🗑️ مسح",
            use_container_width=True
        ):

            clear_all()

            st.rerun()

    # -----------------------------------------------------
    # SELECTION MESSAGE
    # -----------------------------------------------------

    if (
        st.session_state.selection_mode
        == "start"
    ):

        st.info(
            "🟢 اضغط على الخريطة لتحديد نقطة البداية."
        )

    elif (
        st.session_state.selection_mode
        == "destination"
    ):

        st.info(
            "🔴 اضغط على الخريطة لتحديد الوجهة."
        )

    elif (
        st.session_state.selection_mode
        == "building"
    ):

        st.info(
            "🏢 اضغط على موقع مبنى قابل للفتح في الخريطة."
        )

    # -----------------------------------------------------
    # MAP CENTER
    # -----------------------------------------------------

    if st.session_state.selected_building:

        map_center = [
            st.session_state.selected_building[
                "lat"
            ],
            st.session_state.selected_building[
                "lon"
            ]
        ]

    elif st.session_state.start_point:

        map_center = [
            st.session_state.start_point[
                "lat"
            ],
            st.session_state.start_point[
                "lon"
            ]
        ]

    else:

        map_center = [
            21.5433,
            39.1728
        ]

    # -----------------------------------------------------
    # GET OPENABLE BUILDINGS
    # -----------------------------------------------------

    with st.spinner(
        "🔎 جاري تحميل المباني القابلة للفتح..."
    ):

        openable_buildings = (
            get_openable_buildings(
                map_center[0],
                map_center[1],
                1800
            )
        )

    # -----------------------------------------------------
    # OUTDOOR MAP
    # -----------------------------------------------------

    outdoor_map = folium.Map(
        location=map_center,
        zoom_start=15,
        control_scale=True
    )

    # -----------------------------------------------------
    # OPENABLE BUILDING MARKERS
    # -----------------------------------------------------

    for building in openable_buildings:

        building_name = get_building_name(
            building
        )

        indoor_data = parse_indoor_data(
            building
        )

        popup = f"""
        <div style="
            font-family:Cairo,Arial;
            text-align:center;
            min-width:230px;
        ">

            <div style="
                background:#7657ff;
                color:white;
                width:62px;
                height:62px;
                border-radius:50%;
                margin:0 auto 10px auto;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:32px;
                border:4px solid white;
                box-shadow:
                    0 5px 18px
                    rgba(118,87,255,.45);
            ">
                🏢
            </div>

            <b style="
                font-size:17px;
            ">
                {html.escape(building_name)}
            </b>

            <br><br>

            <span style="
                background:#7657ff;
                color:white;
                padding:8px 14px;
                border-radius:12px;
                font-weight:800;
            ">
                ✓ قابل للفتح
            </span>

            <br><br>

            🚪 المداخل:
            {len(indoor_data["entrances"])}

            <br>

            🛗 المصاعد:
            {len(indoor_data["elevators"])}

            <br>

            🪜 السلالم:
            {len(indoor_data["stairs"])}

            <br>

            🚪 الغرف:
            {len(indoor_data["rooms"])}

            <br>

            🚻 دورات المياه:
            {len(indoor_data["toilets"])}

            <br><br>

            اضغط على المبنى ثم اختر
            <b>🏢 اختيار مبنى</b>
            لفتح الخريطة الداخلية.
        </div>
        """

        # -------------------------------------------------
        # PURPLE HIGHLIGHT
        # -------------------------------------------------

        folium.Circle(
            location=[
                building["lat"],
                building["lon"]
            ],
            radius=45,
            color="#7657ff",
            weight=5,
            fill=True,
            fill_color="#7657ff",
            fill_opacity=0.20,
            tooltip="🏢 مبنى قابل للفتح"
        ).add_to(
            outdoor_map
        )

        # -------------------------------------------------
        # CLEAR BUILDING ICON
        # -------------------------------------------------

        folium.Marker(
            location=[
                building["lat"],
                building["lon"]
            ],
            tooltip=(
                "🏢 مبنى قابل للفتح — "
                "اضغط هنا"
            ),
            popup=folium.Popup(
                popup,
                max_width=320
            ),
            icon=folium.DivIcon(
                html="""
                <div style="
                    position:relative;
                    width:58px;
                    height:58px;
                    background:#7657ff;
                    color:white;
                    border:5px solid white;
                    border-radius:50%;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:30px;
                    box-shadow:
                        0 5px 20px
                        rgba(118,87,255,.50);
                    transform:
                        translate(-29px,-29px);
                ">
                    🏢
                </div>
                """
            )
        ).add_to(
            outdoor_map
        )

    # -----------------------------------------------------
    # START MARKER
    # -----------------------------------------------------

    if st.session_state.start_point:

        folium.Marker(
            location=[
                st.session_state.start_point[
                    "lat"
                ],
                st.session_state.start_point[
                    "lon"
                ]
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
    # DESTINATION MARKER
    # -----------------------------------------------------

    if st.session_state.destination_point:

        folium.Marker(
            location=[
                st.session_state.destination_point[
                    "lat"
                ],
                st.session_state.destination_point[
                    "lon"
                ]
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

    if st.session_state.selected_building:

        selected_building = (
            st.session_state.selected_building
        )

        geometry = selected_building.get(
            "geometry",
            []
        )

        if geometry:

            folium.Polygon(
                locations=geometry,
                color="#7657ff",
                weight=5,
                fill=True,
                fill_color="#7657ff",
                fill_opacity=0.20,
                tooltip="🏢 المبنى المحدد"
            ).add_to(
                outdoor_map
            )

    # -----------------------------------------------------
    # SHOW MAP
    # -----------------------------------------------------

    map_result = st_folium(
        outdoor_map,
        width=None,
        height=650,
        key=(
            f"outdoor_map_"
            f"{st.session_state.map_key}"
        )
    )

    # -----------------------------------------------------
    # MAP CLICK
    # -----------------------------------------------------

    if (
        map_result
        and map_result.get(
            "last_clicked"
        )
    ):

        clicked = map_result[
            "last_clicked"
        ]

        clicked_lat = clicked.get(
            "lat"
        )

        clicked_lon = clicked.get(
            "lng"
        )

        if (
            clicked_lat is not None
            and clicked_lon is not None
        ):

            mode = (
                st.session_state.selection_mode
            )

            if mode == "start":

                st.session_state.start_point = {
                    "lat": clicked_lat,
                    "lon": clicked_lon,
                    "name": reverse_geocode(
                        clicked_lat,
                        clicked_lon
                    )
                }

                st.session_state.selection_mode = (
                    None
                )

                st.session_state.route_result = (
                    None
                )

                st.rerun()

            elif mode == "destination":

                st.session_state.destination_point = {
                    "lat": clicked_lat,
                    "lon": clicked_lon,
                    "name": reverse_geocode(
                        clicked_lat,
                        clicked_lon
                    )
                }

                st.session_state.selection_mode = (
                    None
                )

                st.session_state.route_result = (
                    None
                )

                st.rerun()

            elif mode == "building":

                building = get_building_at_point(
                    clicked_lat,
                    clicked_lon,
                    openable_buildings,
                    max_distance=150
                )

                if building:

                    open_building_from_click(
                        building
                    )

                    st.session_state.selection_mode = (
                        None
                    )

                    st.rerun()

                else:

                    st.warning(
                        "لم يتم العثور على مبنى قابل للفتح بالقرب من هذه النقطة."
                    )

    # -----------------------------------------------------
    # LOCATIONS
    # -----------------------------------------------------

    st.markdown(
        "## 📍 المواقع"
    )

    location_cols = st.columns(
        2
    )

    with location_cols[0]:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 🟢 نقطة البداية"
        )

        if st.session_state.start_point:

            st.write(
                st.session_state.start_point[
                    "name"
                ]
            )

        else:

            st.caption(
                "لم يتم اختيار نقطة البداية."
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    with location_cols[1]:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            "### 🔴 الوجهة"
        )

        if st.session_state.destination_point:

            st.write(
                st.session_state.destination_point[
                    "name"
                ]
            )

        else:

            st.caption(
                "لم يتم اختيار الوجهة."
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    # =====================================================
    # SELECTED BUILDING
    # =====================================================

    if st.session_state.selected_building:

        building = (
            st.session_state.selected_building
        )

        building_name = get_building_name(
            building,
            "المبنى المحدد"
        )

        indoor_data = parse_indoor_data(
            building
        )

        st.markdown(
            f"## 🏢 {html.escape(building_name)}"
        )

        st.markdown(
            """
            <div class="big-openable-label">
                🏢 ✓ مبنى قابل للفتح
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("")

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        m1, m2, m3, m4, m5 = st.columns(
            5
        )

        with m1:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-number">
                        {len(indoor_data["entrances"])}
                    </div>
                    <div class="metric-label">
                        🚪 المداخل
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with m2:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-number">
                        {len(indoor_data["elevators"])}
                    </div>
                    <div class="metric-label">
                        🛗 المصاعد
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with m3:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-number">
                        {len(indoor_data["rooms"])}
                    </div>
                    <div class="metric-label">
                        🚪 الغرف
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with m4:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-number">
                        {len(indoor_data["stairs"])}
                    </div>
                    <div class="metric-label">
                        🪜 السلالم
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with m5:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-number">
                        {len(indoor_data["toilets"])}
                    </div>
                    <div class="metric-label">
                        🚻 دورات المياه
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

        # -------------------------------------------------
        # FLOOR SELECTOR
        # -------------------------------------------------

        levels = indoor_data.get(
            "levels",
            []
        )

        if levels:

            floor_options = [
                "كل الطوابق"
            ] + levels

            current_floor = (
                st.session_state.selected_floor
            )

            if (
                current_floor in floor_options
            ):

                floor_index = (
                    floor_options.index(
                        current_floor
                    )
                )

            else:

                floor_index = 0

            selected_floor = st.selectbox(
                "🏬 الطابق",
                floor_options,
                index=floor_index
            )

            if selected_floor == "كل الطوابق":

                st.session_state.selected_floor = (
                    None
                )

            else:

                st.session_state.selected_floor = (
                    selected_floor
                )

        # -------------------------------------------------
        # INDOOR MAP
        # -------------------------------------------------

        st.markdown(
            "### 🗺️ الخريطة الداخلية"
        )

        indoor_map = folium.Map(
            location=[
                building["lat"],
                building["lon"]
            ],
            zoom_start=19,
            control_scale=True
        )

        # -------------------------------------------------
        # BUILDING CENTER
        # -------------------------------------------------

        folium.Marker(
            location=[
                building["lat"],
                building["lon"]
            ],
            tooltip="🏢 المبنى",
            icon=folium.DivIcon(
                html="""
                <div style="
                    background:#7657ff;
                    color:white;
                    border:4px solid white;
                    width:48px;
                    height:48px;
                    border-radius:50%;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:25px;
                    box-shadow:
                        0 5px 15px
                        rgba(0,0,0,.30);
                    transform:
                        translate(-24px,-24px);
                ">
                    🏢
                </div>
                """
            )
        ).add_to(
            indoor_map
        )

        # -------------------------------------------------
        # ENTRANCES
        # -------------------------------------------------

        for item in indoor_data[
            "entrances"
        ]:

            if not floor_visible(
                item,
                st.session_state.selected_floor
            ):
                continue

            folium.Marker(
                location=[
                    item["lat"],
                    item["lon"]
                ],
                tooltip="🚪 مدخل",
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

        for item in indoor_data[
            "elevators"
        ]:

            if not floor_visible(
                item,
                st.session_state.selected_floor
            ):
                continue

            folium.Marker(
                location=[
                    item["lat"],
                    item["lon"]
                ],
                tooltip="🛗 مصعد",
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

        for item in indoor_data[
            "stairs"
        ]:

            if not floor_visible(
                item,
                st.session_state.selected_floor
            ):
                continue

            folium.Marker(
                location=[
                    item["lat"],
                    item["lon"]
                ],
                tooltip="🪜 درج",
                icon=folium.Icon(
                    color="orange",
                    icon="sort",
                    prefix="fa"
                )
            ).add_to(
                indoor_map
            )

        # -------------------------------------------------
        # ROOMS
        # -------------------------------------------------

        for item in indoor_data[
            "rooms"
        ]:

            if not floor_visible(
                item,
                st.session_state.selected_floor
            ):
                continue

            tags = item.get(
                "tags",
                {}
            )

            room_name = (
                tags.get("name")
                or tags.get("ref")
                or tags.get("room")
                or "غرفة"
            )

            folium.Marker(
                location=[
                    item["lat"],
                    item["lon"]
                ],
                tooltip=(
                    f"🚪 {room_name}"
                ),
                icon=folium.Icon(
                    color="purple",
                    icon="home",
                    prefix="fa"
                )
            ).add_to(
                indoor_map
            )

        # -------------------------------------------------
        # TOILETS
        # -------------------------------------------------

        for item in indoor_data[
            "toilets"
        ]:

            if not floor_visible(
                item,
                st.session_state.selected_floor
            ):
                continue

            folium.Marker(
                location=[
                    item["lat"],
                    item["lon"]
                ],
                tooltip="🚻 دورة مياه",
                icon=folium.Icon(
                    color="cadetblue",
                    icon="female",
                    prefix="fa"
                )
            ).add_to(
                indoor_map
            )

        indoor_result = st_folium(
            indoor_map,
            width=None,
            height=650,
            key=(
                f"indoor_map_"
                f"{st.session_state.map_key}"
            )
        )

        # -------------------------------------------------
        # INDOOR CLICK
        # -------------------------------------------------

        if (
            indoor_result
            and indoor_result.get(
                "last_clicked"
            )
        ):

            clicked = (
                indoor_result[
                    "last_clicked"
                ]
            )

            st.session_state.indoor_destination = {
                "lat": clicked["lat"],
                "lon": clicked["lng"]
            }

            st.success(
                "📍 تم تحديد نقطة داخل المبنى."
            )

    # =====================================================
    # OUTDOOR ROUTES
    # =====================================================

    if (
        st.session_state.start_point
        and st.session_state.destination_point
    ):

        st.markdown(
            "## 🚶 المسارات"
        )

        if st.button(
            "🧭 احسب أفضل المسارات",
            use_container_width=True
        ):

            start = (
                st.session_state.start_point
            )

            destination = (
                st.session_state.destination_point
            )

            with st.spinner(
                "🧭 جاري حساب المسارات..."
            ):

                routes = get_routes(
                    start["lat"],
                    start["lon"],
                    destination["lat"],
                    destination["lon"]
                )

            if routes:

                scored = []

                for route in routes:

                    scored.append({
                        "route": route,
                        "score": score_route(
                            route
                        )
                    })

                scored.sort(
                    key=lambda x:
                    x["score"],
                    reverse=True
                )

                st.session_state.route_result = (
                    scored
                )

            else:

                st.session_state.route_result = (
                    []
                )

        # -------------------------------------------------
        # DISPLAY ROUTES
        # -------------------------------------------------

        if st.session_state.route_result:

            routes = (
                st.session_state.route_result
            )

            for index, item in enumerate(
                routes
            ):

                route = item["route"]

                score = item["score"]

                distance_km = (
                    route.get(
                        "distance",
                        0
                    ) / 1000
                )

                duration_min = (
                    route.get(
                        "duration",
                        0
                    ) / 60
                )

                st.markdown(
                    f"""
                    <div class="card">

                    <h3>
                        المسار {index + 1}
                    </h3>

                    <b>
                        ♿ درجة الوصول:
                        {score}/100
                    </b>

                    <br><br>

                    📏 المسافة:
                    {distance_km:.2f} كم

                    <br>

                    ⏱️ الوقت التقريبي:
                    {duration_min:.1f} دقيقة

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # -------------------------------------------------
            # ROUTE MAP
            # -------------------------------------------------

            best_route = (
                routes[0]["route"]
            )

            route_geometry = (
                best_route
                .get(
                    "geometry",
                    {}
                )
                .get(
                    "coordinates",
                    []
                )
            )

            if route_geometry:

                route_map = folium.Map(
                    location=[
                        st.session_state.start_point[
                            "lat"
                        ],
                        st.session_state.start_point[
                            "lon"
                        ]
                    ],
                    zoom_start=14,
                    control_scale=True
                )

                route_points = [
                    [
                        coord[1],
                        coord[0]
                    ]
                    for coord in route_geometry
                ]

                folium.PolyLine(
                    route_points,
                    weight=6,
                    opacity=0.85,
                    tooltip="♿ أفضل مسار"
                ).add_to(
                    route_map
                )

                folium.Marker(
                    location=[
                        st.session_state.start_point[
                            "lat"
                        ],
                        st.session_state.start_point[
                            "lon"
                        ]
                    ],
                    tooltip="🟢 البداية",
                    icon=folium.Icon(
                        color="green",
                        icon="play",
                        prefix="fa"
                    )
                ).add_to(
                    route_map
                )

                folium.Marker(
                    location=[
                        st.session_state.destination_point[
                            "lat"
                        ],
                        st.session_state.destination_point[
                            "lon"
                        ]
                    ],
                    tooltip="🔴 الوجهة",
                    icon=folium.Icon(
                        color="red",
                        icon="flag",
                        prefix="fa"
                    )
                ).add_to(
                    route_map
                )

                st_folium(
                    route_map,
                    width=None,
                    height=550,
                    key=(
                        f"route_map_"
                        f"{st.session_state.map_key}"
                    )
                )

    # =====================================================
    # AI
    # =====================================================

    st.markdown(
        "## 🤖 المساعد الذكي"
    )

    question = st.text_input(
        "اسأل عن المكان أو المسار",
        placeholder=(
            "مثال: ما أفضل مسار للوصول؟"
        )
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

            try:

                from openai import OpenAI

                api_key = os.getenv(
                    "OPENAI_API_KEY"
                )

                if not api_key:

                    try:

                        api_key = st.secrets[
                            "OPENAI_API_KEY"
                        ]

                    except:

                        api_key = None

                if not api_key:

                    st.error(
                        "OpenAI API Key غير متصل."
                    )

                else:

                    client = OpenAI(
                        api_key=api_key
                    )

                    context = {
                        "start": (
                            st.session_state.start_point
                        ),
                        "destination": (
                            st.session_state.destination_point
                        ),
                        "selected_building": (
                            st.session_state.selected_building
                        )
                    }

                    prompt = f"""
أنت مساعد متخصص في الوصول الشامل والتنقل.

أجب بالعربية بوضوح وباختصار.

معلومات المستخدم الحالية:
{context}

السؤال:
{question}

لا تخترع معلومات غير موجودة.
إذا كانت البيانات غير كافية، وضح ذلك.
"""

                    response = (
                        client.responses.create(
                            model=MODEL,
                            input=prompt
                        )
                    )

                    st.session_state.ai_answer = (
                        response.output_text
                    )

            except Exception as e:

                st.error(
                    f"حدث خطأ في الذكاء الاصطناعي: {e}"
                )

    if st.session_state.ai_answer:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            st.session_state.ai_answer
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
        ♿ VerifyAI Access — الذكاء الاصطناعي للوصول الشامل
    </div>
    """,
    unsafe_allow_html=True
)
