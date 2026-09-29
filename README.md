# JanSetu AI — Civic Service Copilot

**Build with AI: Code for Communities 2.0 · Track 1 — AI for Digital Public Infrastructure & Governance**

JanSetu is a human-review-first civic copilot. A citizen describes a public-service problem in natural language and can optionally attach a photo. Gemini analyzes the text and visible civic evidence, suggests a likely service category/department and urgency, identifies useful missing information, and prepares an editable request.

## Prototype features

- Natural-language civic issue intake
- English / Hindi / Odia / Hinglish-ready UI
- Gemini structured civic analysis
- Optional **photo-based civic evidence analysis** using Gemini multimodal input
- Suggested department, category and urgency
- Missing-information detection
- Visual observations + evidence note when a photo is attached
- Editable complaint/request draft
- Copy-to-clipboard
- Simulated tracking lifecycle for the hackathon demo
- Deterministic fallback when Gemini is unavailable
- Explicit human-review and prototype-status disclaimers
- Cloud Run-ready container

## Responsible AI boundary

JanSetu does **not** claim to be a government authority, does not make official decisions, and does not submit complaints to a real government system. Department routing, urgency and tracking are prototype suggestions/simulations. Uploaded photos are processed for the current request and are not stored by this prototype.

## Google technology

- Gemini API through Google's `google-genai` Python SDK
- Gemini multimodal image understanding for optional civic photos
- FastAPI backend
- Google Cloud Run deployment target

## Run locally

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt

# Optional live Gemini mode
$env:GEMINI_API_KEY="YOUR_KEY"
$env:GEMINI_MODEL="gemini-3.8-flash"

uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`.

Without `GEMINI_API_KEY`, the app uses a deterministic demo fallback. Photo upload still works in the UI, but live visual analysis requires Gemini.

## Test cases

### 1. Waste management
Location: `Patia, Bhubaneswar`

> Garbage has not been collected from our street for the last 4 days. The waste is piling up and there is a bad smell. Many people in the locality are worried about hygiene.

### 2. Road damage
Location: `Khandagiri, Bhubaneswar`

> There is a large pothole on the main road near our locality. It is dangerous for two-wheelers and cars, especially at night.

### 3. Water supply
Location: `Sahid Nagar, Bhubaneswar`

> There has been no proper water supply in our locality since yesterday morning. Water pressure is very low and residents are having difficulty getting enough water.

### 4. Photo evidence demo
Use a non-sensitive photo of a pothole, garbage pile, standing water, blocked road, damaged streetlight, or fallen tree. Add a short description and click **Analyze with JanSetu AI**. With Gemini configured, the result includes visible observations and an evidence note.

## Cloud Run

Google Cloud supports deploying a source directory directly with `gcloud run deploy --source .`. If a Dockerfile is present, Cloud Run source deployment uses it. A typical deployment is:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud run deploy jansetu-ai --source . --region asia-south1 --allow-unauthenticated
```

Set the Gemini key on the service rather than committing it:

```bash
gcloud run services update jansetu-ai \
  --region asia-south1 \
  --set-env-vars GEMINI_API_KEY=YOUR_KEY,GEMINI_MODEL=gemini-3.8-flash
```

## Architecture

```text
Citizen Browser
      |
      | text + optional civic photo
      v
+---------------------+
| JanSetu Web UI      |
| HTML/CSS/JavaScript |
+----------+----------+
           |
           v
+---------------------+
| FastAPI /api/analyze|
+----------+----------+
           |
      +----+----+
      |         |
      v         v
 Gemini API   Fallback
 text+vision  rule-based
      |         |
      +----+----+
           |
           v
 Structured Civic Analysis
           |
   +-------+-------+--------+
   |       |       |        |
 Intent Department Urgency Evidence
           |
           v
 Editable request + simulated tracking
           |
           v
       Human review
```

## Demo narrative

1. Start with a citizen problem in natural language.
2. Add a locality.
3. Optionally attach a civic photo.
4. Show Gemini/fallback source badge.
5. Show department, category and urgency suggestion.
6. Show visual evidence and missing information.
7. Edit/copy the generated request.
8. Use simulated tracking.
9. Explain that production would connect verified government APIs and authentication; this hackathon prototype deliberately does not pretend to do that.
