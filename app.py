import base64
import json
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

app = FastAPI(title="JanSetu AI", version="2.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if genai and GEMINI_API_KEY else None

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

SYSTEM_PROMPT = """
You are JanSetu AI, a civic-service copilot prototype for India.

MISSION
Transform a citizen's plain-language civic problem into a clear, neutral,
human-reviewable public-service request.

IMPORTANT BOUNDARIES
- You are NOT a government authority and must never claim official routing,
  entitlement, resolution time, legal status, or guaranteed action.
- Do not invent government phone numbers, URLs, laws, fees, deadlines,
  complaint IDs, offices, or official schemes.
- Department and urgency are suggestions only.
- Never infer a person's identity, caste, religion, health status, income,
  political affiliation, or other sensitive personal attributes.
- Never identify people in an uploaded image.
- If an image is unclear, say so rather than guessing.
- Prefer useful missing-information requests over invented facts.

TEXT + IMAGE REASONING
- Use the citizen's text as the primary context.
- If a photo is supplied, describe only visible civic/infrastructure evidence
  that is relevant to the issue (for example: visible garbage accumulation,
  pothole-like road damage, fallen tree, standing water, damaged streetlight).
- Do not claim measurements, exact locations, causes, or hazards that cannot
  be established from the supplied information.
- If the photo and text disagree, flag the mismatch for human review.

URGENCY
Choose only Low, Medium, or High. Use High only when the described situation
suggests an immediate public-safety, access, sanitation, or essential-service
concern. This is a prototype suggestion, not an emergency classification.

LANGUAGE
Understand English, Hindi, Odia, and Hinglish. The complaint draft should be
clear and professional in the citizen's selected language where practical.

OUTPUT
Return ONLY valid JSON with exactly these keys:
intent, department, category, urgency, summary, missing_information,
suggested_actions, complaint_draft, visual_observations, evidence_note, disclaimer

Rules for fields:
- intent: short label.
- department: likely public-service department/category, not a named official.
- category: concise service category.
- urgency: Low, Medium, or High.
- summary: one or two sentences.
- missing_information: array of short strings.
- suggested_actions: array of short strings, focused on safe human review.
- complaint_draft: editable, professional request; do not add facts not supplied.
- visual_observations: array of visible observations from the photo; empty if no photo.
- evidence_note: one short sentence explaining how the photo supports or does
  not support the request; explicitly say when no photo was supplied.
- disclaimer: short prototype disclaimer.
""".strip()


class CivicAnalysis(BaseModel):
    intent: str
    department: str
    category: str
    urgency: str
    summary: str
    missing_information: list[str]
    suggested_actions: list[str]
    complaint_draft: str
    visual_observations: list[str]
    evidence_note: str
    disclaimer: str


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_result(data: dict) -> dict:
    required_defaults = {
        "intent": "Report / Service Request",
        "department": "Citizen Services",
        "category": "General Public Service",
        "urgency": "Medium",
        "summary": "The citizen reported a public-service issue.",
        "missing_information": [],
        "suggested_actions": [
            "Review the generated request before submitting it.",
            "Attach supporting evidence if available.",
            "Verify the suggested department before any real submission.",
        ],
        "complaint_draft": "Please review the reported public-service issue and take the appropriate action.",
        "visual_observations": [],
        "evidence_note": "No photo was supplied; the result is based on the citizen's text.",
        "disclaimer": "Prototype result. Department routing and status are suggestions/simulations and must be verified before real submission.",
    }
    for key, default in required_defaults.items():
        if key not in data or data[key] is None:
            data[key] = default

    if data.get("urgency") not in {"Low", "Medium", "High"}:
        data["urgency"] = "Medium"

    for key in ("missing_information", "suggested_actions", "visual_observations"):
        if not isinstance(data[key], list):
            data[key] = [str(data[key])]
        data[key] = [clean_text(str(x)) for x in data[key] if clean_text(str(x))]

    return {key: data[key] for key in required_defaults}


def fallback(message: str, language: str, location: str, has_image: bool = False):
    text = message.lower()
    rules = [
        (["fallen tree", "tree fell", "tree has fallen", "blocked road"], "Municipal / Public Works", "Road Obstruction & Infrastructure", "High"),
        (["garbage", "waste", "trash", "dump"], "Municipal Sanitation", "Waste Management", "Medium"),
        (["water", "pipeline", "tap", "drinking water"], "Water Supply / Municipal Services", "Water Supply", "High"),
        (["street light", "streetlight", "lamp", "dark road"], "Municipal Electrical Services", "Street Lighting", "Medium"),
        (["road", "pothole", "broken road", "footpath"], "Municipal / Public Works", "Road & Footpath", "High"),
        (["pension", "ration", "certificate", "document", "scheme"], "Citizen Services / Welfare", "Public Service Assistance", "Medium"),
        (["electricity", "power cut", "transformer"], "Electricity Distribution", "Power Supply", "High"),
    ]
    department, category, urgency = "Citizen Services", "General Public Service", "Medium"
    for keys, d, c, u in rules:
        if any(k in text for k in keys):
            department, category, urgency = d, c, u
            break

    missing = []
    if not location:
        missing.append("Area/locality or landmark")
    if not any(ch.isdigit() for ch in message):
        missing.append("Approximate date/time of the issue")
    if has_image:
        visual = ["A photo was attached, but live visual analysis requires a Gemini API key."]
        evidence = "Photo attached; visual evidence is available for review when Gemini vision analysis is enabled."
    else:
        visual = []
        evidence = "No photo was supplied; the result is based on the citizen's text."

    summary = clean_text(message)
    draft = f"Subject: {category} Request\n\nI would like to report the following public-service issue: {summary.rstrip(".")}."
    if location:
        draft += f" The reported location is {location}."
    draft += " Please review the issue and take the appropriate action."

    return normalize_result({
        "intent": "Report / Service Request",
        "department": department,
        "category": category,
        "urgency": urgency,
        "summary": summary,
        "missing_information": missing,
        "suggested_actions": [
            "Review the generated request before submitting it.",
            "Attach a photo or supporting document if available.",
            "Keep the generated reference ID for follow-up.",
        ],
        "complaint_draft": draft,
        "visual_observations": visual,
        "evidence_note": evidence,
        "disclaimer": "Prototype result. Department routing and status are suggestions/simulations and must be verified before real submission.",
    })


def gemini_analyze(message: str, language: str, location: str, image_bytes: bytes | None = None, image_mime: str | None = None):
    text_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Citizen selected language: {language}\n"
        f"Citizen-supplied location: {location or 'Not supplied'}\n"
        f"Citizen message: {message}\n"
        f"Photo supplied: {'Yes' if image_bytes else 'No'}\n"
    )

    interaction_input = [{"type": "text", "text": text_prompt}]
    if image_bytes and image_mime:
        interaction_input.append({
            "type": "image",
            "data": base64.b64encode(image_bytes).decode("utf-8"),
            "mime_type": image_mime,
        })
        interaction_input.append({
            "type": "text",
            "text": "Analyze the supplied photo only for visible civic/infrastructure evidence relevant to the citizen's issue.",
        })

    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=interaction_input,
        response_format=[
            {
                "type": "text",
                "mime_type": "application/json",
                "schema": CivicAnalysis.model_json_schema(),
            }
        ],
    )
    raw = interaction.output_text or "{}"
    data = json.loads(raw)
    return normalize_result(data)


@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ai_connected": bool(client),
        "model": GEMINI_MODEL if client else "fallback",
        "vision_supported": bool(client),
        "max_image_mb": MAX_IMAGE_BYTES // (1024 * 1024),
    }


@app.post("/api/analyze")
async def analyze(
    message: str = Form(...),
    language: str = Form("English"),
    location: str = Form(""),
    image: UploadFile | None = File(default=None),
):
    message = clean_text(message)
    location = clean_text(location)
    if not message:
        return JSONResponse({"error": "Please describe your issue."}, status_code=400)

    image_bytes = None
    image_mime = None
    image_name = None
    if image:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            return JSONResponse({"error": "Please upload a JPG, PNG, or WEBP image."}, status_code=400)
        image_bytes = await image.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            return JSONResponse({"error": "Image is too large. Please keep it under 5 MB."}, status_code=400)
        image_mime = image.content_type
        image_name = image.filename or "civic-photo"

    try:
        if client:
            result = gemini_analyze(message, language, location, image_bytes, image_mime)
            source = "Gemini Vision" if image_bytes else "Gemini"
        else:
            result = fallback(message, language, location, bool(image_bytes))
            source = "Demo fallback"
    except Exception as exc:
        result = fallback(message, language, location, bool(image_bytes))
        result["disclaimer"] += " Gemini was unavailable for this request, so the deterministic demo fallback was used."
        source = "Demo fallback"

    result["source"] = source
    result["photo_attached"] = bool(image_bytes)
    result["photo_name"] = image_name if image_bytes else ""
    result["reference_id"] = "JS-" + uuid.uuid4().hex[:8].upper()
    result["created_at"] = datetime.now(timezone.utc).isoformat()
    return result
