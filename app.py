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
# EXPANDED LANGUAGE MAP (More Languages Added)
# ============================================================================
LANG_MAP = {
    # Original languages
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
    
    # Additional languages for better coverage
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

# ============================================================================
# EXPANDED MAP TRIGGER WORDS (Multilingual)
# ============================================================================
MAP_TRIGGER_WORDS = [
    # English
    "find", "where", "map", "location", "direction", "navigate", "address", "route", "near", "nearby",
    
    # Bengali
    "কোথায়", "মানচিত্র", "খুঁজুন", "ঠিকানা", "দিকনির্দেশ",
    
    # Arabic
    "أين", "خريطة", "موقع", "عنوان", "اتجاه", "ابحث", "قريب",
    
    # Hindi
    "कहाँ", "नक्शा", "स्थान", "पता", "दिशा", "खोजें",
    
    # Spanish
    "dónde", "mapa", "ubicación", "dirección", "buscar", "cerca",
    
    # French
    "où", "carte", "lieu", "adresse", "direction", "chercher", "près",
    
    # German
    "wo", "karte", "ort", "adresse", "richtung", "suchen", "nähe",
    
    # Urdu
    "کہاں", "نقشہ", "مقام", "پتہ", "سمت",
    
    # Turkish
    "nerede", "harita", "konum", "adres", "yön",
    
    # Indonesian/Malay
    "dimana", "peta", "lokasi", "alamat", "arah",
    
    # Russian
    "где", "карта", "местоположение", "адрес", "направление",
    
    # Japanese
    "どこ", "地図", "場所", "住所",
    
    # Korean
    "어디", "지도", "위치", "주소",
    
    # Chinese
    "哪里", "地图", "位置", "地址",
]

# For language-based URLs: /en /bn /ar ...
SUPPORTED_LANGS = [
    "en", "bn", "ar", "hi", "es", "fr", "de", "pt", "it", "ru", 
    "ja", "ko", "zh", "tr", "ur", "fa", "id", "ms", "th", "vi",
    "nl", "pl", "sv", "no", "da", "fi", "el", "he", "cs", "hu",
    "ro", "uk", "sw", "am", "ta", "te", "ml", "mr", "gu", "kn", "pa"
]

# Language to locale mapping for better voice/TTS support
LANG_TO_LOCALE = {
    "en": "en-US",
    "bn": "bn-BD",
    "ar": "ar-SA",
    "hi": "hi-IN",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "pt": "pt-BR",
    "it": "it-IT",
    "ru": "ru-RU",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "zh": "zh-CN",
    "tr": "tr-TR",
    "ur": "ur-PK",
    "fa": "fa-IR",
    "id": "id-ID",
    "ms": "ms-MY",
    "th": "th-TH",
    "vi": "vi-VN",
    "nl": "nl-NL",
    "pl": "pl-PL",
    "sv": "sv-SE",
    "no": "no-NO",
    "da": "da-DK",
    "fi": "fi-FI",
    "el": "el-GR",
    "he": "he-IL",
    "cs": "cs-CZ",
    "hu": "hu-HU",
    "ro": "ro-RO",
    "uk": "uk-UA",
    "sw": "sw-KE",
    "am": "am-ET",
    "ta": "ta-IN",
    "te": "te-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "pa": "pa-IN",
}

# ============================================================================
# ENHANCED LANGUAGE DETECTION FOR UI (active_lang)
# ============================================================================
def get_lang_from_request(request: Request) -> str:
    """Enhanced language detection from Accept-Language header"""
    header = (request.headers.get("accept-language") or "").lower()

    # Priority order language detection
    lang_priorities = [
        ("bn", ["bn-bd", "bn"]),
        ("ar", ["ar-sa", "ar"]),
        ("hi", ["hi-in", "hi"]),
        ("es", ["es-es", "es"]),
        ("fr", ["fr-fr", "fr"]),
        ("de", ["de-de", "de"]),
        ("pt", ["pt-br", "pt"]),
        ("it", ["it-it", "it"]),
        ("ru", ["ru-ru", "ru"]),
        ("ja", ["ja-jp", "ja"]),
        ("ko", ["ko-kr", "ko"]),
        ("zh", ["zh-cn", "zh"]),
        ("tr", ["tr-tr", "tr"]),
        ("ur", ["ur-pk", "ur"]),
        ("fa", ["fa-ir", "fa"]),
        ("id", ["id-id", "id"]),
        ("ms", ["ms-my", "ms"]),
        ("th", ["th-th", "th"]),
        ("vi", ["vi-vn", "vi"]),
        ("nl", ["nl-nl", "nl"]),
        ("pl", ["pl-pl", "pl"]),
        ("sv", ["sv-se", "sv"]),
        ("no", ["no-no", "no"]),
        ("da", ["da-dk", "da"]),
        ("fi", ["fi-fi", "fi"]),
        ("el", ["el-gr", "el"]),
        ("he", ["he-il", "he"]),
        ("cs", ["cs-cz", "cs"]),
        ("hu", ["hu-hu", "hu"]),
        ("ro", ["ro-ro", "ro"]),
        ("uk", ["uk-ua", "uk"]),
        ("sw", ["sw-ke", "sw"]),
        ("am", ["am-et", "am"]),
        ("ta", ["ta-in", "ta"]),
        ("te", ["te-in", "te"]),
        ("ml", ["ml-in", "ml"]),
        ("mr", ["mr-in", "mr"]),
        ("gu", ["gu-in", "gu"]),
        ("kn", ["kn-in", "kn"]),
        ("pa", ["pa-in", "pa"]),
    ]

    for lang_code, patterns in lang_priorities:
        for pattern in patterns:
            if header.startswith(pattern):
                return lang_code

    return "en"


# ============================================================================
# UTILITY: Get Available Languages List (for frontend dropdowns)
# ============================================================================
@app.get("/api/languages")
async def get_languages():
    """Return all available languages for UI dropdown"""
    return {
        "languages": [
            {"code": code, "name": name}
            for code, name in LANG_MAP.items()
        ],
        "supported_page_langs": SUPPORTED_LANGS
    }


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
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "faq.html",
        {"request": request, "active_lang": active_lang}
    )


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "contact.html",
        {"request": request, "active_lang": active_lang},
    )


@app.get("/robots.txt")
async def robots():
    return FileResponse("static/robots.txt", media_type="text/plain")


# ============================================================================
# LOCALIZED ROUTES (Enhanced for all pages)
# ============================================================================
@app.get("/{lang}", response_class=HTMLResponse)
async def localized_home(request: Request, lang: str):
    """Localized home page"""
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "active_lang": lang}
    )


@app.get("/{lang}/faq", response_class=HTMLResponse)
async def localized_faq(request: Request, lang: str):
    """Localized FAQ page"""
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    return templates.TemplateResponse(
        "faq.html",
        {"request": request, "active_lang": lang}
    )


@app.get("/{lang}/about", response_class=HTMLResponse)
async def localized_about(request: Request, lang: str):
    """Localized About page"""
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "active_lang": lang}
    )


@app.get("/{lang}/contact", response_class=HTMLResponse)
async def localized_contact(request: Request, lang: str):
    """Localized Contact page"""
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    
    return templates.TemplateResponse(
        "contact.html",
        {"request": request, "active_lang": lang}
    )


@app.get("/{lang}/donate", response_class=HTMLResponse)
async def localized_donate(request: Request, lang: str):
    """Localized Donate page"""
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    
    return templates.TemplateResponse(
        "donate.html",
        {"request": request, "active_lang": lang}
    )


@app.get("/{lang}/security", response_class=HTMLResponse)
async def localized_security(request: Request, lang: str):
    """Localized Security page"""
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    
    return templates.TemplateResponse(
        "security.html",
        {"request": request, "active_lang": lang}
    )


@app.get("/{lang}/terms", response_class=HTMLResponse)
async def localized_terms(request: Request, lang: str):
    """Localized Terms page"""
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    
    return templates.TemplateResponse(
        "legal/terms.html",
        {"request": request, "active_lang": lang}
    )


@app.get("/{lang}/privacy", response_class=HTMLResponse)
async def localized_privacy(request: Request, lang: str):
    """Localized Privacy page"""
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    
    return templates.TemplateResponse(
        "legal/privacy.html",
        {"request": request, "active_lang": lang}
    )


# ============================================================================
# ENHANCED CHAT API (Better multilingual support)
# ============================================================================
@app.get("/api/chat")
async def chat(user_input: str = Query(...), pref: str = Query("en-US")):
    """Enhanced chat endpoint with better language handling"""
    
    if not user_input or not user_input.strip():
        # Get appropriate greeting based on language
        greetings = {
            "ar-SA": "مرحبا! اسألني شيئًا يا حبيبي.",
            "bn-BD": "আসসালামু আলাইকুম! আমাকে কিছু জিজ্ঞাসা করুন।",
            "hi-IN": "नमस्ते! मुझसे कुछ पूछें।",
            "ur-PK": "السلام علیکم! مجھ سے کچھ پوچھیں۔",
            "es-ES": "¡Hola! Pregúntame algo.",
            "fr-FR": "Bonjour! Posez-moi une question.",
            "de-DE": "Hallo! Frag mich etwas.",
        }
        
        return {
            "reply": greetings.get(pref, "Marhaba! Please ask me something, Habibi."),
            "voice_lang": pref if pref in LANG_MAP else "en-US",
            "map_link": None,
        }

    if pref not in LANG_MAP:
        pref = "en-US"

    try:
        target_lang = LANG_MAP[pref]

        # Enhanced system instruction with cultural awareness
        system_instruction = (
            f"You are Yalla Habibi, a warm, culturally-aware Arabic AI host. "
            f"Always greet briefly in Arabic first, then respond naturally in {target_lang}. "
            f"Be helpful, friendly, and respectful of cultural nuances. "
            f"End your response with '--- Wisdom:' followed by a practical, culturally-appropriate tip or insight. "
            f"Keep responses conversational and engaging."
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

        # Enhanced map trigger detection (case-insensitive, multilingual)
        map_link = None
        user_input_lower = user_input.lower()
        if any(word.lower() in user_input_lower for word in MAP_TRIGGER_WORDS):
            q = user_input.replace(" ", "+")
            map_link = f"https://maps.google.com/maps?q={q}&output=embed"

        return {
            "reply": reply,
            "voice_lang": pref,
            "map_link": map_link,
            "detected_language": pref,
            "supported": True
        }

    except Exception as e:
        logger.error(f"Chat error: {traceback.format_exc()}")
        
        # Localized error messages
        error_messages = {
            "ar-SA": "مرحبا! حدث خطأ ما. يرجى المحاولة مرة أخرى يا حبيبي.",
            "bn-BD": "দুঃখিত! কিছু ভুল হয়েছে। আবার চেষ্টা করুন।",
            "hi-IN": "क्षमा करें! कुछ गलत हो गया। कृपया पुनः प्रयास करें।",
            "ur-PK": "معذرت! کچھ غلط ہو گیا۔ دوبارہ کوشش کریں۔",
        }
        
        return {
            "reply": error_messages.get(pref, "Marhaba! Something went wrong. Please try again, Habibi."),
            "voice_lang": pref,
            "map_link": None,
            "error": True
        }


# ============================================================================
# HEALTH CHECK (Enhanced)
# ============================================================================
@app.get("/health")
async def health_check():
    """Enhanced health check with more details"""
    return {
        "status": "healthy",
        "model": selected_model,
        "supported_languages": len(LANG_MAP),
        "supported_page_languages": len(SUPPORTED_LANGS),
        "version": "1.0.0"
    }


# ============================================================================
# API INFO ENDPOINT
# ============================================================================
@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return {
        "app_name": "Yalla Habibi AI",
        "version": "1.0.0",
        "description": "Multilingual Arabic-first AI Voice Assistant",
        "features": [
            "40+ Languages Support",
            "Voice Recognition & TTS",
            "Location/Map Integration",
            "Cultural Awareness",
            "Real-time Translation"
        ],
        "supported_languages": len(LANG_MAP),
        "supported_locales": len(SUPPORTED_LANGS),
        "model": selected_model
    }


# ============================================================================
# ERROR HANDLERS (Better UX)
# ============================================================================
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    active_lang = get_lang_from_request(request)
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "active_lang": active_lang},
        status_code=404
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 handler"""
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