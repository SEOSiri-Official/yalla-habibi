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
# COMPREHENSIVE LANGUAGE MAP
# ============================================================================
LANG_MAP = {
    # Well-supported languages (Good browser + TTS support)
    "en-US": {"name": "English", "native": "English", "support": "excellent"},
    "es-ES": {"name": "Spanish", "native": "Español", "support": "excellent"},
    "fr-FR": {"name": "French", "native": "Français", "support": "excellent"},
    "de-DE": {"name": "German", "native": "Deutsch", "support": "excellent"},
    "it-IT": {"name": "Italian", "native": "Italiano", "support": "excellent"},
    "pt-BR": {"name": "Portuguese", "native": "Português", "support": "excellent"},
    "ru-RU": {"name": "Russian", "native": "Русский", "support": "excellent"},
    "ja-JP": {"name": "Japanese", "native": "日本語", "support": "excellent"},
    "ko-KR": {"name": "Korean", "native": "한국어", "support": "excellent"},
    "zh-CN": {"name": "Chinese", "native": "中文", "support": "excellent"},
    
    # Good support but may vary by browser
    "ar-SA": {"name": "Arabic", "native": "العربية", "support": "good"},
    "hi-IN": {"name": "Hindi", "native": "हिंदी", "support": "good"},
    "bn-BD": {"name": "Bengali", "native": "বাংলা", "support": "good"},
    "tr-TR": {"name": "Turkish", "native": "Türkçe", "support": "good"},
    "nl-NL": {"name": "Dutch", "native": "Nederlands", "support": "good"},
    "pl-PL": {"name": "Polish", "native": "Polski", "support": "good"},
    "sv-SE": {"name": "Swedish", "native": "Svenska", "support": "good"},
    "no-NO": {"name": "Norwegian", "native": "Norsk", "support": "good"},
    "da-DK": {"name": "Danish", "native": "Dansk", "support": "good"},
    "fi-FI": {"name": "Finnish", "native": "Suomi", "support": "good"},
    "el-GR": {"name": "Greek", "native": "Ελληνικά", "support": "good"},
    "cs-CZ": {"name": "Czech", "native": "Čeština", "support": "good"},
    "hu-HU": {"name": "Hungarian", "native": "Magyar", "support": "good"},
    "ro-RO": {"name": "Romanian", "native": "Română", "support": "good"},
    "uk-UA": {"name": "Ukrainian", "native": "Українська", "support": "good"},
    "id-ID": {"name": "Indonesian", "native": "Bahasa Indonesia", "support": "good"},
    "ms-MY": {"name": "Malay", "native": "Bahasa Melayu", "support": "good"},
    "th-TH": {"name": "Thai", "native": "ไทย", "support": "good"},
    "vi-VN": {"name": "Vietnamese", "native": "Tiếng Việt", "support": "good"},
    
    # Limited support (may need fallback)
    "ur-PK": {"name": "Urdu", "native": "اردو", "support": "limited"},
    "fa-IR": {"name": "Persian", "native": "فارسی", "support": "limited"},
    "he-IL": {"name": "Hebrew", "native": "עברית", "support": "limited"},
    "ta-IN": {"name": "Tamil", "native": "தமிழ்", "support": "limited"},
    "te-IN": {"name": "Telugu", "native": "తెలుగు", "support": "limited"},
    "ml-IN": {"name": "Malayalam", "native": "മലയാളം", "support": "limited"},
    "mr-IN": {"name": "Marathi", "native": "मराठी", "support": "limited"},
    "gu-IN": {"name": "Gujarati", "native": "ગુજરાતી", "support": "limited"},
    "kn-IN": {"name": "Kannada", "native": "ಕನ್ನಡ", "support": "limited"},
    "pa-IN": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "support": "limited"},
    "sw-KE": {"name": "Swahili", "native": "Kiswahili", "support": "limited"},
    "am-ET": {"name": "Amharic", "native": "አማርኛ", "support": "limited"},
}

# ============================================================================
# MAP TRIGGER WORDS (Multilingual)
# ============================================================================
MAP_TRIGGER_WORDS = [
    # English
    "find", "where", "map", "location", "direction", "navigate", "address", "route", "near", "nearby",
    # Bengali
    "কোথায়", "মানচিত্র", "খুঁজুন", "ঠিকানা",
    # Arabic
    "أين", "خريطة", "موقع", "عنوان",
    # Hindi
    "कहाँ", "नक्शा", "स्थान",
    # Spanish
    "dónde", "mapa", "ubicación",
    # French
    "où", "carte", "lieu",
    # German
    "wo", "karte", "ort",
    # Urdu
    "کہاں", "نقشہ",
    # Turkish
    "nerede", "harita",
    # Indonesian/Malay
    "dimana", "peta",
    # Russian
    "где", "карта",
    # Japanese
    "どこ", "地図",
    # Korean
    "어디", "지도",
    # Chinese
    "哪里", "地图",
]

SUPPORTED_LANGS = [
    "en", "bn", "ar", "hi", "es", "fr", "de", "pt", "it", "ru", 
    "ja", "ko", "zh", "tr", "ur", "fa", "id", "ms", "th", "vi",
    "nl", "pl", "sv", "no", "da", "fi", "el", "he", "cs", "hu",
    "ro", "uk", "sw", "am", "ta", "te", "ml", "mr", "gu", "kn", "pa"
]

LANG_TO_LOCALE = {
    "en": "en-US", "bn": "bn-BD", "ar": "ar-SA", "hi": "hi-IN",
    "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "pt": "pt-BR",
    "it": "it-IT", "ru": "ru-RU", "ja": "ja-JP", "ko": "ko-KR",
    "zh": "zh-CN", "tr": "tr-TR", "ur": "ur-PK", "fa": "fa-IR",
    "id": "id-ID", "ms": "ms-MY", "th": "th-TH", "vi": "vi-VN",
    "nl": "nl-NL", "pl": "pl-PL", "sv": "sv-SE", "no": "no-NO",
    "da": "da-DK", "fi": "fi-FI", "el": "el-GR", "he": "he-IL",
    "cs": "cs-CZ", "hu": "hu-HU", "ro": "ro-RO", "uk": "uk-UA",
    "sw": "sw-KE", "am": "am-ET", "ta": "ta-IN", "te": "te-IN",
    "ml": "ml-IN", "mr": "mr-IN", "gu": "gu-IN", "kn": "kn-IN",
    "pa": "pa-IN",
}

# ============================================================================
# LANGUAGE DETECTION FOR UI
# ============================================================================
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
# GET AVAILABLE LANGUAGES WITH SUPPORT LEVEL
# ============================================================================
@app.get("/api/languages")
async def get_languages():
    """Return all available languages with support information"""
    return {
        "languages": [
            {
                "code": code,
                "name": info["name"],
                "native": info["native"],
                "support_level": info["support"]
            }
            for code, info in LANG_MAP.items()
        ],
        "supported_page_langs": SUPPORTED_LANGS,
        "note": "excellent = Full browser support | good = Most browsers | limited = May need fallback"
    }


# ============================================================================
# BROWSER COMPATIBILITY CHECK
# ============================================================================
@app.get("/api/browser-check")
async def browser_check(request: Request):
    """Check browser capabilities"""
    user_agent = request.headers.get("user-agent", "").lower()
    
    is_chrome = "chrome" in user_agent and "edge" not in user_agent
    is_edge = "edge" in user_agent or "edg" in user_agent
    is_safari = "safari" in user_agent and "chrome" not in user_agent
    is_firefox = "firefox" in user_agent
    
    return {
        "browser": {
            "chrome": is_chrome,
            "edge": is_edge,
            "safari": is_safari,
            "firefox": is_firefox
        },
        "speech_recognition_support": is_chrome or is_edge or is_safari,
        "recommended_browser": "Chrome or Edge for best speech recognition support",
        "note": "Firefox has limited speech recognition support"
    }


# ============================================================================
# STATIC PAGES
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
# ENHANCED CHAT API - BETTER LANGUAGE HANDLING
# ============================================================================
@app.get("/api/chat")
async def chat(
    user_input: str = Query(...), 
    pref: str = Query("en-US"),
    input_lang: str = Query(None)  # NEW: Optional detected input language
):
    """
    Enhanced chat endpoint with better language handling
    
    Args:
        user_input: The text input from user
        pref: Preferred output language (what language to respond in)
        input_lang: Detected input language (what language user spoke in)
    """
    
    if not user_input or not user_input.strip():
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
            "support_level": LANG_MAP.get(pref, {}).get("support", "unknown")
        }

    # Validate preference language
    if pref not in LANG_MAP:
        logger.warning(f"Invalid pref language: {pref}, falling back to en-US")
        pref = "en-US"

    try:
        lang_info = LANG_MAP[pref]
        target_lang_name = lang_info["name"]
        target_lang_native = lang_info["native"]
        support_level = lang_info["support"]

        # Build context-aware prompt
        if input_lang and input_lang != pref:
            # User spoke in one language but wants response in another (translation scenario)
            system_instruction = (
                f"You are Yalla Habibi, a warm Arabic AI host. "
                f"The user spoke in {input_lang} but wants your response in {target_lang_name} ({target_lang_native}). "
                f"Greet briefly in Arabic, then respond naturally in {target_lang_name}. "
                f"If they're asking for translation, translate accurately. "
                f"End with '--- Wisdom:' followed by a practical, culturally-appropriate tip. "
                f"Keep responses clear and helpful."
            )
        else:
            # Same language for input and output
            system_instruction = (
                f"You are Yalla Habibi, a warm, culturally-aware Arabic AI host. "
                f"Respond naturally in {target_lang_name} ({target_lang_native}). "
                f"Greet briefly in Arabic first if appropriate. "
                f"Be helpful, friendly, and respectful of cultural nuances. "
                f"End with '--- Wisdom:' followed by a practical tip. "
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

        # Map detection
        map_link = None
        user_input_lower = user_input.lower()
        if any(word.lower() in user_input_lower for word in MAP_TRIGGER_WORDS):
            q = user_input.replace(" ", "+")
            map_link = f"https://maps.google.com/maps?q={q}&output=embed"

        return {
            "reply": reply,
            "voice_lang": pref,
            "map_link": map_link,
            "detected_input_lang": input_lang,
            "support_level": support_level,
            "supported": True
        }

    except Exception as e:
        logger.error(f"Chat error: {traceback.format_exc()}")
        
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
            "error": True,
            "error_message": str(e)
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
        "supported_page_languages": len(SUPPORTED_LANGS),
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
            "Voice Recognition & TTS",
            "Location/Map Integration",
            "Cultural Awareness",
            "Real-time Translation",
            "Browser Compatibility Check"
        ],
        "supported_languages": len(LANG_MAP),
        "supported_locales": len(SUPPORTED_LANGS),
        "model": selected_model,
        "recommended_browsers": ["Chrome", "Edge", "Safari"]
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