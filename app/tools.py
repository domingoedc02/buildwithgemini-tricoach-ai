import os
import uuid
from google.cloud import firestore
from google.cloud import storage
from google.oauth2 import service_account
import requests
from dotenv import load_dotenv

from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig
from google.adk.tools import ToolContext

load_dotenv()

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-199c3cdcc0c5"
GCS_BUCKET_NAME = "tricoach-ai-media-qwiklabs-gcp-01-199c3cdcc0c5"
COLLECTION_NAME = "workouts"
KEY_PATH = "/tmp/sa-key.json"

CITY_COORDINATES = {
    "boulder": (40.015, -105.2705, "Boulder, CO"),
    "san francisco": (37.7749, -122.4194, "San Francisco, CA"),
    "kona": (19.64, -155.9969, "Kona, HI (Ironman World Championship)"),
    "nice": (43.7102, 7.2620, "Nice, France (Ironman World Championship)"),
    "new york": (40.7128, -74.0060, "New York, NY"),
    "chicago": (41.8781, -87.6298, "Chicago, IL"),
    "austin": (30.2672, -97.7431, "Austin, TX"),
}


def get_firestore_client():
    if os.path.exists(KEY_PATH):
        creds = service_account.Credentials.from_service_account_file(KEY_PATH)
        return firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=creds)
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def list_workouts(discipline: str = "") -> str:
    """Lists workouts from the database, optionally filtered by discipline.

    Args:
        discipline: Optional filter for discipline (e.g. 'swimming', 'cycling', 'running', 'brick').

    Returns:
        A formatted string listing matching workouts with details.
    """
    db = get_firestore_client()
    query = db.collection(COLLECTION_NAME)
    if discipline:
        query = query.where("discipline", "==", discipline.lower().strip())

    docs = query.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)

    if not results:
        filter_msg = f" for discipline '{discipline}'" if discipline else ""
        return f"No workouts found{filter_msg}."

    formatted_items = [
        f"- [{w['id']}] {w['title']} ({w['discipline'].upper()}): "
        f"{w['duration_minutes']} mins, {w['target_zone']} - {w['description']}"
        for w in results
    ]
    return "Workouts found:\n" + "\n".join(formatted_items)


def get_workout(workout_id: str) -> str:
    """Gets details for a specific workout by ID.

    Args:
        workout_id: The ID of the workout to retrieve.

    Returns:
        Details of the requested workout.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(workout_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Workout with ID '{workout_id}' not found."

    data = doc.to_dict()
    return (
        f"Workout '{data.get('title')}': Discipline: {data.get('discipline')}, "
        f"Duration: {data.get('duration_minutes')} mins, Zone: {data.get('target_zone')}, "
        f"Difficulty: {data.get('difficulty')}. Description: {data.get('description')}"
    )


def add_workout(
    title: str,
    discipline: str,
    duration_minutes: int,
    target_zone: str,
    description: str,
    difficulty: str = "Intermediate",
) -> str:
    """Adds a new workout to the training catalog.

    Args:
        title: Title of the workout (e.g. 'FTP Booster Intervals').
        discipline: Discipline type ('swimming', 'cycling', 'running', 'brick').
        duration_minutes: Workout duration in minutes.
        target_zone: Target intensity zone (e.g. 'Zone 2', 'Zone 4/Threshold').
        description: Workout breakdown and instructions.
        difficulty: Difficulty level ('Beginner', 'Intermediate', 'Advanced').

    Returns:
        Confirmation message with the created workout ID.
    """
    db = get_firestore_client()
    workout_id = f"workout-{uuid.uuid4().hex[:6]}"
    workout_data = {
        "title": title,
        "discipline": discipline.lower().strip(),
        "duration_minutes": duration_minutes,
        "target_zone": target_zone,
        "description": description,
        "difficulty": difficulty,
    }
    db.collection(COLLECTION_NAME).document(workout_id).set(workout_data)
    return f"Successfully added workout '{title}' with ID '{workout_id}'."


def calculate_training_zones(
    max_heart_rate: int = 0,
    resting_heart_rate: int = 0,
    ftp_watts: int = 0,
) -> str:
    """Calculates personalized heart rate or cycling power training zones (Zone 1 through Zone 5).

    Args:
        max_heart_rate: Athlete's maximum heart rate in BPM (optional if ftp_watts given).
        resting_heart_rate: Athlete's resting heart rate in BPM (optional, default 0).
        ftp_watts: Athlete's Functional Threshold Power in Watts (optional if max_heart_rate given).

    Returns:
        A formatted summary of calculated training zones.
    """
    if not max_heart_rate and not ftp_watts:
        return "Please provide either max_heart_rate or ftp_watts to calculate training zones."

    output_lines = []

    if max_heart_rate > 0:
        hrr = (
            max_heart_rate - resting_heart_rate
            if resting_heart_rate > 0
            else max_heart_rate
        )
        base = resting_heart_rate if resting_heart_rate > 0 else 0

        z1 = (int(base + hrr * 0.50), int(base + hrr * 0.60))
        z2 = (int(base + hrr * 0.60), int(base + hrr * 0.70))
        z3 = (int(base + hrr * 0.70), int(base + hrr * 0.80))
        z4 = (int(base + hrr * 0.80), int(base + hrr * 0.90))
        z5 = (int(base + hrr * 0.90), max_heart_rate)

        output_lines.append(
            f"Heart Rate Zones (Max: {max_heart_rate} BPM, Resting: {resting_heart_rate} BPM):"
        )
        output_lines.append(f"  Zone 1 (Active Recovery): {z1[0]} - {z1[1]} BPM")
        output_lines.append(f"  Zone 2 (Endurance/Aerobic): {z2[0]} - {z2[1]} BPM")
        output_lines.append(f"  Zone 3 (Tempo): {z3[0]} - {z3[1]} BPM")
        output_lines.append(f"  Zone 4 (Threshold): {z4[0]} - {z4[1]} BPM")
        output_lines.append(f"  Zone 5 (VO2 Max): {z5[0]} - {z5[1]} BPM")

    if ftp_watts > 0:
        if output_lines:
            output_lines.append("")
        pz1 = (0, int(ftp_watts * 0.55))
        pz2 = (int(ftp_watts * 0.56), int(ftp_watts * 0.75))
        pz3 = (int(ftp_watts * 0.76), int(ftp_watts * 0.90))
        pz4 = (int(ftp_watts * 0.91), int(ftp_watts * 1.05))
        pz5 = (int(ftp_watts * 1.06), int(ftp_watts * 1.20))

        output_lines.append(f"Power Zones (FTP: {ftp_watts} Watts):")
        output_lines.append(f"  Zone 1 (Active Recovery): <{pz1[1]}W")
        output_lines.append(f"  Zone 2 (Endurance): {pz2[0]} - {pz2[1]}W")
        output_lines.append(f"  Zone 3 (Tempo): {pz3[0]} - {pz3[1]}W")
        output_lines.append(f"  Zone 4 (Threshold): {pz4[0]} - {pz4[1]}W")
        output_lines.append(f"  Zone 5 (VO2 Max): {pz5[0]} - {pz5[1]}W")

    return "\n".join(output_lines)


def get_outdoor_workout_weather(location: str = "Boulder, CO") -> str:
    """Fetches real-time outdoor weather and wind conditions for triathlon training using the free Open-Meteo API.

    Args:
        location: City or location name (e.g. 'Boulder', 'Kona', 'San Francisco', 'Nice', 'Austin', 'New York').

    Returns:
        A formatted string with current temperature, feels like, wind speed, humidity, and training advice.
    """
    loc_key = location.lower().strip()
    lat, lon, display_name = 40.015, -105.2705, "Boulder, CO"

    for key, (c_lat, c_lon, name) in CITY_COORDINATES.items():
        if key in loc_key:
            lat, lon, display_name = c_lat, c_lon, name
            break

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m"
        f"&temperature_unit=fahrenheit&wind_speed_unit=mph"
    )

    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json().get("current", {})

        temp = data.get("temperature_2m")
        feels_like = data.get("apparent_temperature")
        humidity = data.get("relative_humidity_2m")
        wind = data.get("wind_speed_10m")
        precip = data.get("precipitation")

        advice = []
        if wind and wind > 12:
            advice.append("High wind detected: Use shallow rim wheels on the bike for stability.")
        if temp and temp > 80:
            advice.append("Warm weather: Increase fluid and electrolyte intake (500-750ml/hr).")
        elif temp and temp < 55:
            advice.append("Cool weather: Wear arm warmers and a windbreaker vest.")
        if precip and precip > 0:
            advice.append("Precipitation expected: Reduce tire pressure slightly for wet cornering traction.")

        advice_str = " " + " ".join(advice) if advice else " Great conditions for an outdoor session!"

        return (
            f"Current Outdoor Training Weather for {display_name}:\n"
            f"• Temperature: {temp}°F (Feels like: {feels_like}°F)\n"
            f"• Wind Speed: {wind} mph\n"
            f"• Humidity: {humidity}%\n"
            f"• Precipitation: {precip} in\n"
            f"Coaching Advice:{advice_str}"
        )
    except Exception as e:
        return f"Unable to fetch current weather for {location}: {str(e)}"


def geocode_address(address: str) -> str:
    """Uses the Google Maps Geocoding API to convert an address or place name into geographic coordinates (latitude and longitude).

    Args:
        address: The location, city, or address to geocode (e.g. 'Boulder, CO' or '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A formatted string with the full address and latitude/longitude coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return f"No geocoding results found for '{address}'."

        first = results[0]
        formatted_address = first.get("formatted_address")
        location = first.get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")

        return f"Geocoding result for '{address}':\n• Address: {formatted_address}\n• Location: Latitude {lat}, Longitude {lng}"
    except Exception as e:
        return f"Geocoding API error: {str(e)}"


def find_nearby_training_places(
    address_or_location: str,
    place_type: str = "gym",
    radius_meters: float = 3000.0,
) -> str:
    """Uses the Google Maps Places API (New) to search for nearby places (like gyms, parks, swimming pools) around an address.

    Args:
        address_or_location: Starting location or address (e.g. 'Boulder, CO' or 'Austin, TX').
        place_type: Type of place to search for (e.g. 'gym', 'park', 'sports_complex').
        radius_meters: Search radius in meters (default 3000m / 3km).

    Returns:
        A list of nearby places with name, address, and coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geo_resp = requests.get(geo_url, params={"address": address_or_location, "key": api_key}, timeout=5)
    if geo_resp.status_code != 200 or not geo_resp.json().get("results"):
        return f"Could not locate address '{address_or_location}'."

    geo_data = geo_resp.json()["results"][0]["geometry"]["location"]
    lat, lng = geo_data["lat"], geo_data["lng"]

    places_url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    body = {
        "includedTypes": [place_type.lower().strip()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_meters,
            }
        },
    }

    try:
        resp = requests.post(places_url, json=body, headers=headers, timeout=5)
        resp.raise_for_status()
        places_data = resp.json().get("places", [])

        if not places_data:
            return f"No nearby '{place_type}' places found within {int(radius_meters)}m of '{address_or_location}'."

        formatted_places = []
        for p in places_data:
            name = p.get("displayName", {}).get("text", "Unknown Place")
            addr = p.get("formattedAddress", "No address")
            loc = p.get("location", {})
            plat, plng = loc.get("latitude"), loc.get("longitude")
            formatted_places.append(f"• {name}\n  Address: {addr}\n  Location: Lat {plat}, Lng {plng}")

        return f"Nearby '{place_type}' locations near '{address_or_location}':\n" + "\n".join(formatted_places)
    except Exception as e:
        return f"Places API (New) error: {str(e)}"


async def generate_workout_visual(
    prompt: str, tool_context: ToolContext = None
) -> str:
    """Generates an image for a workout, race goal, or triathlon scene using gemini-3.1-flash-lite-image model in global region. Saves the image as an artifact and uploads it to Cloud Storage, returning its public HTTPS URL.

    Args:
        prompt: Detailed visual prompt describing the workout or triathlon scene (e.g. 'A triathlete cycling on a scenic coastal road').

    Returns:
        Public HTTPS URL of the uploaded image.
    """
    client = genai.Client(
        vertexai=True, project=FIRESTORE_PROJECT_ID, location="global"
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=GenerateContentConfig(response_modalities=["IMAGE"]),
    )

    image_bytes = None
    mime_type = "image/jpeg"
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

    if not image_bytes:
        return "Failed to generate image: No image data returned from model."

    filename = f"workout-visual-{uuid.uuid4().hex[:8]}.jpg"

    if tool_context:
        artifact_part = types.Part.from_bytes(
            data=image_bytes, mime_type=mime_type
        )
        await tool_context.save_artifact(filename, artifact_part)

    if os.path.exists(KEY_PATH):
        creds = service_account.Credentials.from_service_account_file(KEY_PATH)
        gcs_client = storage.Client(
            project=FIRESTORE_PROJECT_ID, credentials=creds
        )
    else:
        gcs_client = storage.Client(project=FIRESTORE_PROJECT_ID)

    bucket = gcs_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"


async def generate_workout_video(
    prompt: str, tool_context: ToolContext = None
) -> str:
    """Generates a short video for a workout, race goal, or triathlon technique using Google's Omni model (gemini-omni-flash-preview) in the global region. Saves the video as an artifact and uploads it to Cloud Storage, returning its public HTTPS URL.

    Args:
        prompt: Detailed visual prompt describing the triathlon or workout scene (e.g. 'A short video of a triathlete sprinting across the finish line').

    Returns:
        Public HTTPS URL of the uploaded video.
    """
    import base64

    client = genai.Client(
        vertexai=True, project=FIRESTORE_PROJECT_ID, location="global"
    )

    try:
        response = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt
        )
    except Exception as e:
        return f"Failed to generate video: {str(e)}"

    video_bytes = None
    mime_type = "video/mp4"

    if hasattr(response, "output_video") and response.output_video:
        if getattr(response.output_video, "mime_type", None):
            mime_type = response.output_video.mime_type
        if getattr(response.output_video, "data", None):
            raw_data = response.output_video.data
            if isinstance(raw_data, bytes):
                video_bytes = raw_data
            elif isinstance(raw_data, str):
                video_bytes = base64.b64decode(raw_data)

    if not video_bytes:
        return "Failed to generate video: No video data returned from model."

    filename = f"workout-video-{uuid.uuid4().hex[:8]}.mp4"

    if tool_context:
        artifact_part = types.Part.from_bytes(
            data=video_bytes, mime_type=mime_type
        )
        await tool_context.save_artifact(filename, artifact_part)

    if os.path.exists(KEY_PATH):
        creds = service_account.Credentials.from_service_account_file(KEY_PATH)
        gcs_client = storage.Client(
            project=FIRESTORE_PROJECT_ID, credentials=creds
        )
    else:
        gcs_client = storage.Client(project=FIRESTORE_PROJECT_ID)

    bucket = gcs_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
