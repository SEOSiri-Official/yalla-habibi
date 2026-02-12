import os
import logging
import traceback

import uvicorn
import google.generativeai as genai
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ============================================================================
# FASTAPI INIT
# ============================================================================
app = FastAPI(
    title="Yalla Habibi AI - The Global Host",
    description="Native Arabic AI Host for Global Foreigners by Momenul Ahmad (SEOSiri)",
    version="1.0.0",
)

# Static + templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENVIRONMENT / GEMINI CONFIG
# ============================================================================
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not API_KEY:
    logger.error("❌ Missing GOOGLE_API_KEY / GEMINI_API_KEY in environment")
    raise Exception("Missing GOOGLE_API_KEY in environment")

if API_KEY.strip().lower().startswith("paste") or API_KEY.strip() == "your_api_key_here":
    logger.error("❌ Placeholder API key detected")
    raise Exception("Invalid API key placeholder detected")

try:
    genai.configure(api_key=API_KEY)
    logger.info("✅ Gemini API configured")
except Exception as e:
    logger.error(f"❌ Gemini configure failed: {e}")
    raise

# ============================================================================
# SAFETY SETTINGS
# ============================================================================
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# ============================================================================
# MODEL SELECTION (keeps your existing fallback behavior)
# ============================================================================
try:
    available_models = [
        m.name for m in genai.list_models()
        if "generateContent" in getattr(m, "supported_generation_methods", [])
    ]

    if "models/gemini-1.5-flash" in available_models:
        selected_model = "models/gemini-1.5-flash"
    elif "models/gemini-1.5-pro" in available_models:
        selected_model = "models/gemini-1.5-pro"
    elif available_models:
        selected_model = available_models[0]
    else:
        selected_model = "models/gemini-1.5-flash"

except Exception as e:
    logger.warning(f"⚠️ model listing failed, using default: {e}")
    selected_model = "models/gemini-1.5-flash"

logger.info(f"✅ Using model: {selected_model}")

# ============================================================================
# LANGUAGE MAP (keeps your existing features)
# ============================================================================
LANG_MAP = {
    "bn-BD": "Bengali (বাংলা)",
    "ar-SA": "Arabic (العربية)",
    "en-US": "English",
    "hi-IN": "Hindi",
    "es-ES": "Spanish",
    "pt-BR": "Portuguese",
    "fr-FR": "French",
    "de-DE": "German",
    "it-IT": "Italian",
    "ru-RU": "Russian",
    "ja-JP": "Japanese",
    "ko-KR": "Korean",
    "zh-CN": "Chinese",
    "tr-TR": "Turkish",
}

MAP_TRIGGER_WORDS = [
    "find", "where", "map", "location", "direction", "navigate",
    "কোথায়", "মানচিত্র",
    "أين", "خريطة",
]

# For language-based URLs: /en /bn /ar ...
SUPPORTED_LANGS = ["en", "bn", "ar", "hi", "es", "fr", "de"]

# ============================================================================
# LANGUAGE DETECTION FOR UI (active_lang) — FIXES your “about page error” cause
# (the templates expecting active_lang but routes not passing it)
# ============================================================================
def get_lang_from_request(request: Request) -> str:
    header = (request.headers.get("accept-language") or "").lower()

    # Simple + stable detection (no deps)
    if header.startswith("bn"):
        return "bn"
    if header.startswith("ar"):
        return "ar"
    if header.startswith("hi"):
        return "hi"
    if header.startswith("es"):
        return "es"
    if header.startswith("fr"):
        return "fr"
    if header.startswith("de"):
        return "de"

    return "en"


# ============================================================================
# ROUTES – STATIC PAGES (ALL pass active_lang now)
# ============================================================================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "legal/terms.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "legal/privacy.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/ai-policy", response_class=HTMLResponse)
async def ai_policy(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "legal/ai-policy.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/cookies", response_class=HTMLResponse)
async def cookies(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "legal/cookies.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/security", response_class=HTMLResponse)
async def security(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "security.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/manual", response_class=HTMLResponse)
async def manual_page(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "manual.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/donate", response_class=HTMLResponse)
async def donate(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "donate.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    return templates.TemplateResponse(
        "faq.html",
        {
            "request": request,
            "active_lang": "en"
        }
    )



@app.get("/robots.txt")
async def robots():
    # keep your existing behavior + correct content-type
    return FileResponse("static/robots.txt", media_type="text/plain")


# OPTIONAL: If you ever move sitemap to /sitemap.xml, enable this.
# For now you are using /static/sitemap.xml in robots.txt (keep as-is).
# @app.get("/sitemap.xml")
# async def sitemap():
#     return FileResponse("static/sitemap.xml", media_type="application/xml")


# ============================================================================
# LOCALIZED HOME (language-based URLs)
# ============================================================================
@app.get("/{lang}/faq", response_class=HTMLResponse)
async def localized_faq(request: Request, lang: str):

    if lang not in SUPPORTED_LANGS:
        lang = "en"

    return templates.TemplateResponse(
        "faq.html",
        {
            "request": request,
            "active_lang": lang
        }
    ) 



# ============================================================================
# CHAT API (keeps your existing features: pref, map trigger, wisdom format)
# ============================================================================
@app.get("/api/chat")
async def chat(user_input: str = Query(...), pref: str = Query("en-US")):
    if not user_input or not user_input.strip():
        return {
            "reply": "Marhaba! Please ask me something, Habibi.",
            "voice_lang": pref if pref in LANG_MAP else "en-US",
            "map_link": None,
        }

    if pref not in LANG_MAP:
        pref = "en-US"

    try:
        target_lang = LANG_MAP[pref]

        system_instruction = (
            f"You are Yalla Habibi, a warm Arabic AI host. "
            f"Always greet briefly in Arabic, reply in {target_lang}, "
            f"and end with '--- Wisdom:' followed by a helpful tip."
        )

        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction,
            safety_settings=safety_settings,
        )

        response = model.generate_content(user_input.strip())
        reply = getattr(response, "text", None)

        if not reply:
            raise HTTPException(status_code=502, detail="Empty reply from model")

        map_link = None
        if any(word in user_input.lower() for word in MAP_TRIGGER_WORDS):
            q = user_input.replace(" ", "+")
            map_link = f"https://maps.google.com/maps?q={q}&output=embed"

        return {
            "reply": reply,
            "voice_lang": pref,
            "map_link": map_link,
        }

    except Exception:
        logger.error(traceback.format_exc())
        return {
            "reply": "Marhaba! Something went wrong. Please try again, Habibi.",
            "voice_lang": pref,
            "map_link": None,
        }


# ============================================================================
# HEALTH
# ============================================================================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": selected_model}


# ============================================================================
# ENTRY
# ============================================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010, log_level="info")
