"""Demo metros: one OpenStreetMap bounding box per metro, plus a default ZIP.

Bounding boxes are (south, west, north, east) in degrees. They are deliberately
small so each one is a single, light Overpass query.
"""

METROS = [
    {"id": "ithaca", "name": "Ithaca, NY", "zip": "14850",
     "bbox": (42.30, -76.75, 42.62, -76.30)},
    {"id": "nyc", "name": "New York City, NY", "zip": "10016",
     "bbox": (40.49, -74.27, 40.92, -73.68)},
    {"id": "bayarea", "name": "Fremont / Bay Area, CA", "zip": "94539",
     "bbox": (37.25, -122.30, 37.85, -121.75)},
    {"id": "miami", "name": "Miami, FL", "zip": "33130",
     "bbox": (25.55, -80.50, 26.05, -80.10)},
    {"id": "chicago", "name": "Chicago, IL", "zip": "60611",
     "bbox": (41.64, -87.95, 42.07, -87.52)},
]


def overpass_query(bbox):
    """One Overpass QL query covering the common urgent-care taggings."""
    b = ",".join(f"{v:.2f}" for v in bbox)
    parts = [
        f'nwr["healthcare"="clinic"]["healthcare:speciality"~"urgent_care"]({b});',
        f'nwr["amenity"="clinic"]["urgent_care"="yes"]({b});',
        f'nwr["healthcare"]["urgent_care"="yes"]({b});',
        f'nwr["healthcare"="urgent_care"]({b});',
        f'nwr["amenity"="urgent_care"]({b});',
        f'nwr["name"~"urgent care",i]({b});',
    ]
    return "[out:json][timeout:120];(" + "".join(parts) + ");out center tags;"
