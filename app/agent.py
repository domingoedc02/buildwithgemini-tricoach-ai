# ruff: noqa
import datetime
import json
import os
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    add_workout,
    calculate_training_zones,
    find_nearby_training_places,
    generate_workout_video,
    generate_workout_visual,
    geocode_address,
    get_outdoor_workout_weather,
    get_workout,
    list_workouts,
)

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-199c3cdcc0c5"
LOCATION = "us-east1"
MEMORY_BANK_ID = "2830923583151144960"

# Retrieve Agent Engine resource name from deployment_metadata.json if available
DEPLOYMENT_METADATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json"
)

agent_engine_resource_name = None
if os.path.exists(DEPLOYMENT_METADATA_PATH):
    try:
        with open(DEPLOYMENT_METADATA_PATH, "r") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are TriCoach AI, an expert fitness and triathlon coach assistant. "
        "You help endurance athletes plan workouts, calculate personalized HR and power training zones, "
        "check outdoor training weather, geocode addresses, find nearby gyms/parks, generate workout visuals and videos, "
        "look up training sessions from their Firestore catalog, and add new workouts. "
        "You remember athlete preferences, health conditions, dietary restrictions, and ALL user allergies (e.g., food, medication, pollen/environmental) across conversations using your memory tool. "
        "Whenever a user mentions any allergy, explicitly acknowledge and record it, and strictly ensure that all future advice, nutrition recommendations, and training plans respect their allergies. "
        "You can also write and execute Python code in a secure sandbox when needed. "
        "Use the available tools whenever asked."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends session turn data to Vertex AI Memory Bank for extraction after each turn."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        # Ignore if memory service is not initialized on the deployment runtime
        pass
    return None


def memory_bank_service_builder():
    """Returns a VertexAiMemoryBankService configured for this agent's Memory Bank instance."""
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        vertexai=True,
        project=FIRESTORE_PROJECT_ID,
        location=LOCATION,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        get_weather,
        get_current_time,
        list_workouts,
        get_workout,
        add_workout,
        calculate_training_zones,
        get_outdoor_workout_weather,
        geocode_address,
        find_nearby_training_places,
        generate_workout_visual,
        generate_workout_video,
        PreloadMemoryTool(),
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

