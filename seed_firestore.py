import os
from google.cloud import firestore
from google.oauth2 import service_account

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-199c3cdcc0c5"
COLLECTION_NAME = "workouts"
KEY_PATH = "/tmp/sa-key.json"


def seed_database():
    if os.path.exists(KEY_PATH):
        creds = service_account.Credentials.from_service_account_file(KEY_PATH)
        db = firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=creds)
    else:
        db = firestore.Client(project=FIRESTORE_PROJECT_ID)

    workouts = [
        {
            "id": "workout-swim-01",
            "title": "Threshold CSS Intervals",
            "discipline": "swimming",
            "duration_minutes": 45,
            "target_zone": "Zone 4 (Threshold)",
            "description": "400m warmup, 10x100m at Critical Swim Speed with 15s rest, 200m cooldown.",
            "difficulty": "Intermediate",
        },
        {
            "id": "workout-bike-01",
            "title": "Zone 2 Base Builder Ride",
            "discipline": "cycling",
            "duration_minutes": 90,
            "target_zone": "Zone 2 (Aerobic)",
            "description": "Steady endurance spin keeping heart rate strictly in Zone 2, CAD 85-95 rpm.",
            "difficulty": "Beginner",
        },
        {
            "id": "workout-bike-02",
            "title": "FTP Sweet Spot Over-Unders",
            "discipline": "cycling",
            "duration_minutes": 60,
            "target_zone": "Zone 4/5 (Threshold/VO2)",
            "description": "15m warmup, 3x(2m @ 105% FTP / 2m @ 90% FTP x 3), 15m cooldown.",
            "difficulty": "Advanced",
        },
        {
            "id": "workout-run-01",
            "title": "Olympic Pace Tempo Run",
            "discipline": "running",
            "duration_minutes": 50,
            "target_zone": "Zone 3/4 (Tempo)",
            "description": "10m jog warmup, 30m steady tempo at target 10k race pace, 10m cooldown.",
            "difficulty": "Intermediate",
        },
        {
            "id": "workout-brick-01",
            "title": "Race Simulation Brick",
            "discipline": "brick",
            "duration_minutes": 75,
            "target_zone": "Zone 3 (Race Pace)",
            "description": "60m hard ride at race pace immediately followed by 15m transition run off the bike.",
            "difficulty": "Advanced",
        },
    ]

    print(
        f"Seeding Firestore collection '{COLLECTION_NAME}' in project '{FIRESTORE_PROJECT_ID}'..."
    )
    for item in workouts:
        doc_id = item.pop("id")
        db.collection(COLLECTION_NAME).document(doc_id).set(item)
        print(f"  Added document: {doc_id} -> {item['title']}")

    print("Database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
