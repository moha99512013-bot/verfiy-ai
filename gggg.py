def get_openable_buildings(lat, lon, radius=1800):
    query = f"""
    [out:json][timeout:45];

    (
        way["building"](around:{radius},{lat},{lon});
        relation["building"](around:{radius},{lat},{lon});

        node["indoor"](around:{radius},{lat},{lon});
        way["indoor"](around:{radius},{lat},{lon});

        node["room"](around:{radius},{lat},{lon});
        way["room"](around:{radius},{lat},{lon});

        node["level"](around:{radius},{lat},{lon});
        way["level"](around:{radius},{lat},{lon});

        node["highway"="elevator"](around:{radius},{lat},{lon});
        node["elevator"="yes"](around:{radius},{lat},{lon});

        node["entrance"](around:{radius},{lat},{lon});
        way["entrance"](around:{radius},{lat},{lon});
    );

    out center;
    """

    try:
        response = requests.post(
            OVERPASS_URL,
            data=query,
            headers=HEADERS,
            timeout=55
        )

        elements = response.json().get("elements", [])

    except Exception:
        return []

    buildings = []
    indoor_points = []

    for item in elements:

        tags = item.get("tags", {})

        if "lat" in item:
            p_lat = float(item["lat"])
            p_lon = float(item["lon"])

        elif item.get("center"):
            p_lat = float(item["center"]["lat"])
            p_lon = float(item["center"]["lon"])

        else:
            continue

        # Buildings
        if "building" in tags:

            buildings.append({
                "id": item.get("id"),
                "type": item.get("type"),
                "lat": p_lat,
                "lon": p_lon,
                "tags": tags
            })

        # Indoor evidence
        if (
            tags.get("indoor")
            or tags.get("room")
            or tags.get("level")
            or tags.get("entrance")
            or tags.get("elevator") == "yes"
            or tags.get("highway") == "elevator"
        ):

            indoor_points.append({
                "lat": p_lat,
                "lon": p_lon,
                "tags": tags
            })

    openable = []

    for building in buildings:

        has_indoor_data = False

        for point in indoor_points:

            distance = distance_meters(
                building["lat"],
                building["lon"],
                point["lat"],
                point["lon"]
            )

            if distance <= 120:
                has_indoor_data = True
                break

        if has_indoor_data:
            openable.append(building)

    return openable
