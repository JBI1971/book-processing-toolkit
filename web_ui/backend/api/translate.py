"""
Translation API endpoint - on-demand translation via OpenAI
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from models import TranslateRequest, TranslateResponse
from dotenv import load_dotenv

router = APIRouter()

# Force reload .env file to override system environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path, override=True)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """
    Translate text using OpenAI API

    Request Body:
        text: The text to translate
        source_lang: Source language code (default: "zh" for Chinese)
        target_lang: Target language code (default: "en" for English)

    Returns:
        Translated text with original and language information
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # Construct translation prompt
        lang_names = {
            "zh": "Chinese",
            "en": "English",
            "ja": "Japanese",
            "ko": "Korean"
        }

        source_lang_name = lang_names.get(request.source_lang, request.source_lang)
        target_lang_name = lang_names.get(request.target_lang, request.target_lang)

        system_prompt = f"""You are a professional literary translator specializing in Classical Chinese literature and wuxia novels.

Translate the given {source_lang_name} text to {target_lang_name} with these requirements:

1. ACCURACY: Maintain precise meaning, tone, and cultural nuances
2. LITERARY QUALITY: Use appropriate literary English for classical/wuxia content
3. PROPER NOUNS: Romanize Chinese names using Pinyin (e.g., 金庸 → Jin Yong)
4. TITLES: Translate book/chapter titles poetically but accurately
5. CULTURAL CONTEXT: Preserve historical and martial arts terminology appropriately
6. NO ADDITIONS: Return ONLY the translation, no explanations, notes, or romanization in parentheses

Be scrupulous and precise. Double-check accuracy before responding."""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.text}
            ],
            temperature=0.3,  # Low temperature for consistent translations
        )

        translated = response.choices[0].message.content.strip()

        return TranslateResponse(
            original=request.text,
            translated=translated,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )
