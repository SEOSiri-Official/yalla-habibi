import os
import logging
import traceback

import uvicorn
import google.generativeai as genai
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
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
# MODEL SELECTION
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
# SIMPLIFIED LANGUAGE MAP
# ============================================================================
LANG_MAP = {
    "bn-BD": "Bengali (বাংলা)",
    "ar-SA": "Arabic (العربية)",
    "en-US": "English",
    "hi-IN": "Hindi (हिंदी)",
    "es-ES": "Spanish (Español)",
    "pt-BR": "Portuguese (Português)",
    "fr-FR": "French (Français)",
    "de-DE": "German (Deutsch)",
    "it-IT": "Italian (Italiano)",
    "ru-RU": "Russian (Русский)",
    "ja-JP": "Japanese (日本語)",
    "ko-KR": "Korean (한국어)",
    "zh-CN": "Chinese (中文)",
    "tr-TR": "Turkish (Türkçe)",
    "ur-PK": "Urdu (اردو)",
    "fa-IR": "Persian (فارسی)",
    "id-ID": "Indonesian (Bahasa Indonesia)",
    "ms-MY": "Malay (Bahasa Melayu)",
    "th-TH": "Thai (ไทย)",
    "vi-VN": "Vietnamese (Tiếng Việt)",
    "nl-NL": "Dutch (Nederlands)",
    "pl-PL": "Polish (Polski)",
    "sv-SE": "Swedish (Svenska)",
    "no-NO": "Norwegian (Norsk)",
    "da-DK": "Danish (Dansk)",
    "fi-FI": "Finnish (Suomi)",
    "el-GR": "Greek (Ελληνικά)",
    "he-IL": "Hebrew (עברית)",
    "cs-CZ": "Czech (Čeština)",
    "hu-HU": "Hungarian (Magyar)",
    "ro-RO": "Romanian (Română)",
    "uk-UA": "Ukrainian (Українська)",
    "sw-KE": "Swahili (Kiswahili)",
    "am-ET": "Amharic (አማርኛ)",
    "ta-IN": "Tamil (தமிழ்)",
    "te-IN": "Telugu (తెలుగు)",
    "ml-IN": "Malayalam (മലയാളം)",
    "mr-IN": "Marathi (मराठी)",
    "gu-IN": "Gujarati (ગુજરાતી)",
    "kn-IN": "Kannada (ಕನ್ನಡ)",
    "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
}

MAP_TRIGGER_WORDS = [
    "find", "where", "map", "location", "direction", "navigate", "address", "route", "near", "nearby",
    "কোথায়", "মানচিত্র", "খুঁজুন", "ঠিকানা", "أين", "خريطة", "موقع", "कहाँ", "नक्शा",
    "dónde", "mapa", "où", "carte", "wo", "karte", "کہاں", "نقشہ", "nerede", "harita",
    "dimana", "peta", "где", "карта", "どこ", "地図", "어디", "지도", "哪里", "地图",
]

SUPPORTED_LANGS = [
    "en", "bn", "ar", "hi", "es", "fr", "de", "pt", "it", "ru", 
    "ja", "ko", "zh", "tr", "ur", "fa", "id", "ms", "th", "vi",
    "nl", "pl", "sv", "no", "da", "fi", "el", "he", "cs", "hu",
    "ro", "uk", "sw", "am", "ta", "te", "ml", "mr", "gu", "kn", "pa"
]

def get_lang_from_request(request: Request) -> str:
    """Enhanced language detection from Accept-Language header"""
    header = (request.headers.get("accept-language") or "").lower()
    
    lang_priorities = [
        ("bn", ["bn-bd", "bn"]), ("ar", ["ar-sa", "ar"]), ("hi", ["hi-in", "hi"]),
        ("es", ["es-es", "es"]), ("fr", ["fr-fr", "fr"]), ("de", ["de-de", "de"]),
        ("pt", ["pt-br", "pt"]), ("it", ["it-it", "it"]), ("ru", ["ru-ru", "ru"]),
        ("ja", ["ja-jp", "ja"]), ("ko", ["ko-kr", "ko"]), ("zh", ["zh-cn", "zh"]),
        ("tr", ["tr-tr", "tr"]), ("ur", ["ur-pk", "ur"]), ("fa", ["fa-ir", "fa"]),
        ("id", ["id-id", "id"]), ("ms", ["ms-my", "ms"]), ("th", ["th-th", "th"]),
        ("vi", ["vi-vn", "vi"]), ("nl", ["nl-nl", "nl"]), ("pl", ["pl-pl", "pl"]),
        ("sv", ["sv-se", "sv"]), ("no", ["no-no", "no"]), ("da", ["da-dk", "da"]),
        ("fi", ["fi-fi", "fi"]), ("el", ["el-gr", "el"]), ("he", ["he-il", "he"]),
        ("cs", ["cs-cz", "cs"]), ("hu", ["hu-hu", "hu"]), ("ro", ["ro-ro", "ro"]),
        ("uk", ["uk-ua", "uk"]), ("sw", ["sw-ke", "sw"]), ("am", ["am-et", "am"]),
        ("ta", ["ta-in", "ta"]), ("te", ["te-in", "te"]), ("ml", ["ml-in", "ml"]),
        ("mr", ["mr-in", "mr"]), ("gu", ["gu-in", "gu"]), ("kn", ["kn-in", "kn"]),
        ("pa", ["pa-in", "pa"]),
    ]

    for lang_code, patterns in lang_priorities:
        for pattern in patterns:
            if header.startswith(pattern):
                return lang_code
    return "en"


# ============================================================================
# GET AVAILABLE LANGUAGES
# ============================================================================
@app.get("/api/languages")
async def get_languages():
    """Return all available languages"""
    return {
        "languages": [
            {"code": code, "name": name}
            for code, name in LANG_MAP.items()
        ],
        "supported_page_langs": SUPPORTED_LANGS
    }


# ============================================================================
# STATIC PAGES
# ============================================================================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("index.html", {"request": request, "active_lang": active_lang})

@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("legal/terms.html", {"request": request, "active_lang": active_lang})

@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("legal/privacy.html", {"request": request, "active_lang": active_lang})

@app.get("/ai-policy", response_class=HTMLResponse)
async def ai_policy(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("legal/ai-policy.html", {"request": request, "active_lang": active_lang})

@app.get("/cookies", response_class=HTMLResponse)
async def cookies(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("legal/cookies.html", {"request": request, "active_lang": active_lang})

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("about.html", {"request": request, "active_lang": active_lang})

@app.get("/security", response_class=HTMLResponse)
async def security(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("security.html", {"request": request, "active_lang": active_lang})

@app.get("/manual", response_class=HTMLResponse)
async def manual_page(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("manual.html", {"request": request, "active_lang": active_lang})

@app.get("/donate", response_class=HTMLResponse)
async def donate(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("donate.html", {"request": request, "active_lang": active_lang})

@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("faq.html", {"request": request, "active_lang": active_lang})

@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse("contact.html", {"request": request, "active_lang": active_lang})

@app.get("/robots.txt")
async def robots():
    return FileResponse("static/robots.txt", media_type="text/plain")


# ============================================================================
# LOCALIZED ROUTES
# ============================================================================
@app.get("/{lang}", response_class=HTMLResponse)
async def localized_home(request: Request, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    return templates.TemplateResponse("index.html", {"request": request, "active_lang": lang})

@app.get("/{lang}/faq", response_class=HTMLResponse)
async def localized_faq(request: Request, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    return templates.TemplateResponse("faq.html", {"request": request, "active_lang": lang})

@app.get("/{lang}/about", response_class=HTMLResponse)
async def localized_about(request: Request, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    return templates.TemplateResponse("about.html", {"request": request, "active_lang": lang})

@app.get("/{lang}/contact", response_class=HTMLResponse)
async def localized_contact(request: Request, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    return templates.TemplateResponse("contact.html", {"request": request, "active_lang": lang})

@app.get("/{lang}/donate", response_class=HTMLResponse)
async def localized_donate(request: Request, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    return templates.TemplateResponse("donate.html", {"request": request, "active_lang": lang})

@app.get("/{lang}/security", response_class=HTMLResponse)
async def localized_security(request: Request, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    return templates.TemplateResponse("security.html", {"request": request, "active_lang": lang})

@app.get("/{lang}/terms", response_class=HTMLResponse)
async def localized_terms(request: Request, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    return templates.TemplateResponse("legal/terms.html", {"request": request, "active_lang": lang})

@app.get("/{lang}/privacy", response_class=HTMLResponse)
async def localized_privacy(request: Request, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    return templates.TemplateResponse("legal/privacy.html", {"request": request, "active_lang": lang})


# ============================================================================
# SIMPLIFIED CHAT API - AUTO LANGUAGE MODE
# ============================================================================
@app.get("/api/chat")
async def chat(
    user_input: str = Query(...), 
    pref: str = Query(None),  # Optional: only if user wants different language
    detected_lang: str = Query(None)  # What language user spoke
):
    """
    Simplified chat with auto-language:
    - If no pref given, respond in detected language
    - If pref given, translate to that language
    """
    
    if not user_input or not user_input.strip():
        return {
            "reply": "Marhaba! Please speak to me.",
            "voice_lang": "en-US",
            "map_link": None,
        }

    try:
        # AUTO MODE: Use detected language for response if no preference
        if not pref or pref == "auto":
            response_lang = detected_lang if detected_lang and detected_lang in LANG_MAP else "en-US"
        else:
            response_lang = pref if pref in LANG_MAP else "en-US"

        target_lang_name = LANG_MAP.get(response_lang, "English")

        # Build smart system instruction
        if detected_lang and pref and detected_lang != pref:
            # Translation mode: different input and output language
            system_instruction = (
                f"You are Yalla Habibi, a warm Arabic AI assistant. "
                f"The user spoke in {LANG_MAP.get(detected_lang, 'their language')} but wants response in {target_lang_name}. "
                f"Provide accurate translation and helpful response in {target_lang_name}. "
                f"Be natural, clear, and culturally sensitive. "
                f"End with '--- Wisdom:' followed by a practical tip in {target_lang_name}."
            )
        else:
            # Same language mode
            system_instruction = (
                f"You are Yalla Habibi, a warm, culturally-aware Arabic AI assistant. "
                f"Respond naturally in {target_lang_name}. "
                f"Greet briefly in Arabic if appropriate, then answer clearly in {target_lang_name}. "
                f"Be helpful, friendly, and respectful. "
                f"End with '--- Wisdom:' followed by a practical tip."
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

        # Map detection
        map_link = None
        if any(word.lower() in user_input.lower() for word in MAP_TRIGGER_WORDS):
            q = user_input.replace(" ", "+")
            map_link = f"https://maps.google.com/maps?q={q}&output=embed"

        return {
            "reply": reply,
            "voice_lang": response_lang,
            "map_link": map_link,
            "detected_input": detected_lang,
            "mode": "translation" if (detected_lang and pref and detected_lang != pref) else "same_language"
        }

    except Exception as e:
        logger.error(f"Chat error: {traceback.format_exc()}")
        return {
            "reply": "Marhaba! Something went wrong. Please try again.",
            "voice_lang": "en-US",
            "map_link": None,
            "error": True
        }


# ============================================================================
# HEALTH CHECK
# ============================================================================
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": selected_model,
        "supported_languages": len(LANG_MAP),
        "version": "1.0.0"
    }


# ============================================================================
# API INFO
# ============================================================================
@app.get("/api/info")
async def api_info():
    return {
        "app_name": "Yalla Habibi AI",
        "version": "1.0.0",
        "description": "Multilingual Arabic-first AI Voice Assistant",
        "features": [
            "40+ Languages Support",
            "Auto Language Detection",
            "Voice Recognition & TTS",
            "Real-time Translation",
            "Location/Map Integration"
        ],
        "supported_languages": len(LANG_MAP),
        "model": selected_model
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "active_lang": active_lang},
        status_code=404
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    active_lang = get_lang_from_request(request)
    logger.error(f"Internal server error: {exc}")
    return templates.TemplateResponse(
        "500.html",
        {"request": request, "active_lang": active_lang},
        status_code=500
    )


# ============================================================================
# ENTRY
# ============================================================================
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8010,
        log_level="info",
        access_log=True
    )