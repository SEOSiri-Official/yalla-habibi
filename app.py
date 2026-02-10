import os
import google.generativeai as genai
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import uvicorn
import logging
import traceback
app = FastAPI(
    title="Yalla Habibi AI - The Global Host",
    description="Native Arabic AI Host for Global Foreigners by Momenul Ahmad (SEOSiri)",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


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

# ============================================================================
# SETUP LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================================
load_dotenv()

# Get API key from environment variables
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

# Validate API key exists and is not placeholder
if not API_KEY:
    logger.error("❌ NO API KEY FOUND!")
    logger.error("Please create a .env file with: GOOGLE_API_KEY=your_actual_key_here")
    logger.error("Get your API key from: https://aistudio.google.com/apikey")
    raise Exception("Missing API key. Please set GOOGLE_API_KEY in .env file")

if API_KEY == "PASTE_YOUR_FULL_KEY_HERE" or API_KEY == "your_api_key_here":
    logger.error("❌ PLACEHOLDER API KEY DETECTED!")
    logger.error("Please replace with your actual API key in .env file")
    logger.error("Get your API key from: https://aistudio.google.com/apikey")
    raise Exception("Please set a valid GOOGLE_API_KEY in .env file")

# Configure Gemini API
try:
    genai.configure(api_key=API_KEY)
    logger.info("✅ Gemini API configured successfully")
except Exception as e:
    logger.error(f"❌ Failed to configure Gemini API: {e}")
    raise

# ============================================================================
# SAFETY SETTINGS
# ============================================================================
# Balanced safety settings - not too strict, not too lenient
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
        if 'generateContent' in m.supported_generation_methods
    ]
    
    # Prefer Gemini 1.5 Flash, fallback to Pro, then any available
    if 'models/gemini-1.5-flash' in available_models:
        selected_model = 'models/gemini-1.5-flash'
    elif 'models/gemini-1.5-pro' in available_models:
        selected_model = 'models/gemini-1.5-pro'
    elif 'models/gemini-pro' in available_models:
        selected_model = 'models/gemini-pro'
    else:
        selected_model = available_models[0] if available_models else 'models/gemini-1.5-flash'
    
    logger.info(f"✅ Selected model: {selected_model}")
    logger.info(f"📋 Available models: {', '.join(available_models[:3])}...")
    
except Exception as e:
    logger.warning(f"⚠️ Error listing models: {e}")
    logger.info("Using default model: models/gemini-1.5-flash")
    selected_model = "models/gemini-1.5-flash"

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

    logger.info("✅ Static files and templates loaded")
except Exception as e:
    logger.error(f"❌ Error loading static files or templates: {e}")
    logger.error("Make sure 'static' and 'templates' directories exist")

# ============================================================================
# LANGUAGE MAPPING
# ============================================================================
LANG_MAP = {
    "bn-BD": "Bengali (বাংলা)",
    "ar-SA": "Arabic (العربية)", 
    "en-US": "English",
    "hi-IN": "Hindi (हिन्दी)",
    "es-ES": "Spanish (Español)",
    "pt-BR": "Brazilian Portuguese (Português)",
    "ur-PK": "Urdu (اردو)",
    "tl-PH": "Tagalog (Filipino)"
}

# Map trigger words for map feature
MAP_TRIGGER_WORDS = [
    "find", "where", "map", "location", "direction", "navigate",
    "মসজিদ", "কোথায়", "মানচিত্র",  # Bengali
    "مطعم", "أين", "خريطة",  # Arabic
    "donde", "mapa", "ubicación",  # Spanish
    "onde", "mapa", "localização",  # Portuguese
]

# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def home(request: Request):
    """Serve the main HTML page"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error serving home page: {e}")
        raise HTTPException(status_code=500, detail="Error loading page")


@app.get("/api/chat")
async def chat(user_input: str = Query(...), pref: str = Query("en-US")):
    """
    Main chat endpoint for Yalla Habibi AI
    
    Args:
        user_input: The user's message/question
        pref: Language preference code (e.g., 'en-US', 'bn-BD')
    
    Returns:
        JSON with reply, voice_lang, and optional map_link
    """
    
    # Log incoming request
    logger.info(f"📥 Received: '{user_input[:50]}...' | Language: {pref}")
    
    # ========================================================================
    # INPUT VALIDATION
    # ========================================================================
    if not user_input or len(user_input.strip()) == 0:
        logger.warning("Empty input received")
        return {
            "reply": "Marhaba! Please ask me something, Habibi.",
            "voice_lang": pref,
            "map_link": None
        }
    
    # Sanitize input
    user_input = user_input.strip()
    
    # Validate language preference
    if pref not in LANG_MAP:
        logger.warning(f"Invalid language preference: {pref}, defaulting to en-US")
        pref = "en-US"
    
    try:
        target_lang = LANG_MAP.get(pref, "English")
        
        # ====================================================================
        # SYSTEM INSTRUCTION
        # ====================================================================
        system_instruction = (
            f"You are 'Yalla Habibi', a friendly and warm Arabic AI assistant created by Momenul Ahmad (SEOSiri). "
            f"You are a native Arabic host helping foreigners in the Arabian Peninsula. "
            f"\n\nYour communication style:\n"
            f"1. ALWAYS start with a brief Arabic greeting (Marhaba, Salam, Ahlan, etc.)\n"
            f"2. Then provide your full response in {target_lang}\n"
            f"3. Be helpful, warm, and culturally respectful\n"
            f"4. ALWAYS end with '--- Wisdom: ' followed by a helpful tip (moral, environmental, educational, or cultural)\n"
            f"\n\nGuidelines:\n"
            f"- Keep responses concise and helpful\n"
            f"- If someone is rude, politely redirect: 'Habibi, let us stay respectful.'\n"
            f"- Focus on being a helpful bridge between cultures\n"
            f"- Mention that you were created by Momenul Ahmad (SEOSiri) if relevant\n"
        )
        
        # ====================================================================
        # CREATE MODEL WITH CONFIGURATION
        # ====================================================================
        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction,
            safety_settings=safety_settings,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
        )
        
        # ====================================================================
        # GENERATE RESPONSE
        # ====================================================================
        logger.info(f"🤖 Generating response with {selected_model}...")
        response = model.generate_content(user_input)
        
        # ====================================================================
        # RESPONSE VALIDATION
        # ====================================================================
        
        # Check if response object exists
        if not response:
            logger.error("❌ No response object returned from API")
            return {
                "reply": "Marhaba! I encountered a technical issue. Please try again, Habibi.",
                "voice_lang": pref,
                "map_link": None
            }
        
        # Check for blocked content
        if hasattr(response, 'prompt_feedback'):
            feedback = response.prompt_feedback
            if hasattr(feedback, 'block_reason') and feedback.block_reason:
                logger.warning(f"⚠️ Content blocked: {feedback.block_reason}")
                return {
                    "reply": "Habibi, let us stay respectful. Please rephrase your question in a kind way.",
                    "voice_lang": pref,
                    "map_link": None
                }
        
        # Extract response text
        try:
            ai_reply = response.text
            logger.info(f"✅ Response generated: {ai_reply[:100]}...")
        except ValueError as e:
            logger.error(f"❌ Cannot access response.text: {e}")
            if hasattr(response, 'candidates'):
                logger.error(f"Response candidates: {response.candidates}")
            return {
                "reply": "Habibi, I cannot respond to this request. Please try a different question.",
                "voice_lang": pref,
                "map_link": None
            }
        
        # Check if response is empty
        if not ai_reply or len(ai_reply.strip()) == 0:
            logger.error("❌ Empty response text received")
            return {
                "reply": "Marhaba! I had trouble forming a response. Please try again, Habibi.",
                "voice_lang": pref,
                "map_link": None
            }
        
        # ====================================================================
        # MAP FEATURE
        # ====================================================================
        map_link = None
        user_lower = user_input.lower()
        
        # Check if user is asking for directions/locations
        if any(word in user_lower for word in MAP_TRIGGER_WORDS):
            # Create Google Maps embed link
            encoded_query = user_input.replace(' ', '+')
            map_link = f"https://maps.google.com/maps?q={encoded_query}&t=&z=15&ie=UTF8&iwloc=&output=embed"
            logger.info(f"🗺️ Map generated for query: {user_input[:30]}...")
        
        # ====================================================================
        # RETURN RESPONSE
        # ====================================================================
        return {
            "reply": ai_reply,
            "voice_lang": pref,
            "map_link": map_link
        }
    
    except Exception as e:
        # ====================================================================
        # ERROR HANDLING
        # ====================================================================
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Log detailed error information
        logger.error(f"❌ EXCEPTION: {error_type}: {error_msg}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        
        # Return user-friendly error message
        return {
            "reply": f"Marhaba! I encountered a technical issue ({error_type}). Please try again, Habibi.",
            "voice_lang": pref,
            "map_link": None
        }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "model": selected_model,
        "api_configured": True
    }

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🚀 Starting Yalla Habibi AI")
    logger.info("=" * 70)
    logger.info(f"📍 Server: http://0.0.0.0:8010")
    logger.info(f"🤖 Model: {selected_model}")
    logger.info(f"🌍 Languages: {len(LANG_MAP)} supported")
    logger.info("=" * 70)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8010,
        log_level="info"
    )