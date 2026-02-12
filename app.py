import os
import google.generativeai as genai
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import uvicorn
import logging
import traceback

# ============================================================================
# FASTAPI INIT
# ============================================================================
app = FastAPI(
    title="Yalla Habibi AI - The Global Host",
    description="Native Arabic AI Host for Global Foreigners by Momenul Ahmad (SEOSiri)",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ============================================================================
# ROUTES – STATIC PAGES
# ============================================================================
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/terms")
async def terms(request: Request):
    return templates.TemplateResponse("legal/terms.html", {"request": request})

@app.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse("legal/privacy.html", {"request": request})

@app.get("/ai-policy")
async def ai_policy(request: Request):
    return templates.TemplateResponse("legal/ai-policy.html", {"request": request})

@app.get("/cookies")
async def cookies(request: Request):
    return templates.TemplateResponse("legal/cookies.html", {"request": request})

@app.get("/about")
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/security")
async def security(request: Request):
    return templates.TemplateResponse("security.html", {"request": request})

@app.get("/manual", response_class=HTMLResponse)
async def manual_page(request: Request):
    return templates.TemplateResponse("manual.html", {"request": request})
@app.get("/robots.txt")
async def robots():
    return FileResponse("static/robots.txt")
@app.get("/donate", response_class=HTMLResponse)
async def donate(request: Request):
    return templates.TemplateResponse("donate.html", {"request": request})
@app.get("/faq")
async def faq_page(request: Request):
    return templates.TemplateResponse("faq.html", {"request": request})


# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENVIRONMENT
# ============================================================================
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise Exception("Missing GOOGLE_API_KEY in environment")

if API_KEY.lower().startswith("paste") or API_KEY == "your_api_key_here":
    raise Exception("Invalid API key placeholder detected")

genai.configure(api_key=API_KEY)
logger.info("✅ Gemini API configured")

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
# MODEL SELECTION
# ============================================================================
try:
    available_models = [
        m.name for m in genai.list_models()
        if "generateContent" in m.supported_generation_methods
    ]

    if "models/gemini-1.5-flash" in available_models:
        selected_model = "models/gemini-1.5-flash"
    elif "models/gemini-1.5-pro" in available_models:
        selected_model = "models/gemini-1.5-pro"
    else:
        selected_model = available_models[0]

except Exception:
    selected_model = "models/gemini-1.5-flash"

logger.info(f"✅ Using model: {selected_model}")

# ============================================================================
# LANGUAGE MAP
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
    "tr-TR": "Turkish"
}

MAP_TRIGGER_WORDS = [
    "find", "where", "map", "location", "direction", "navigate",
    "কোথায়", "মানচিত্র",
    "أين", "خريطة"
]

# ============================================================================
# CHAT API
# ============================================================================
@app.get("/api/chat")
async def chat(user_input: str = Query(...), pref: str = Query("en-US")):

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
            safety_settings=safety_settings
        )

        response = model.generate_content(user_input)
        reply = response.text

        map_link = None
        if any(word in user_input.lower() for word in MAP_TRIGGER_WORDS):
            q = user_input.replace(" ", "+")
            map_link = f"https://maps.google.com/maps?q={q}&output=embed"

        return {
            "reply": reply,
            "voice_lang": pref,
            "map_link": map_link
        }

    except Exception as e:
        logger.error(traceback.format_exc())
        return {
            "reply": "Marhaba! Something went wrong. Please try again, Habibi.",
            "voice_lang": pref,
            "map_link": None
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
    uvicorn.run(app, host="0.0.0.0", port=8010)
