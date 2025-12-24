import os
import io
import sys
from PIL import Image
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable is not set.")
    print("Please create a .env file with your API key:")
    print("GEMINI_API_KEY=your_api_key_here")
    sys.exit(1)

_genai_client = genai.Client(api_key=GEMINI_API_KEY)

# Compatibility wrappers to preserve previous GenerativeModel-like interface
class _ResponseWrapper:
    def __init__(self, raw):
        self._raw = raw
        try:
            # Try to extract text using existing helper for robustness
            self.text = extract_text_from_genai_response(raw).strip()
        except Exception:
            # Fallback: best-effort string
            self.text = str(raw)

class _ModelWrapper:
    def __init__(self, model_name: str, client: genai.Client, generation_config: dict | None = None):
        self._client = client
        self._model_name = model_name
        self._config = generation_config or None

    def _to_contents(self, content):
        # Accept string or [prompt, image]
        from PIL import Image as PILImage
        from google.genai.types import Part
        if isinstance(content, (list, tuple)):
            parts = []
            for item in content:
                if isinstance(item, PILImage.Image):
                    buf = io.BytesIO()
                    item.save(buf, format="PNG")
                    parts.append(Part.from_bytes(mime_type="image/png", data=buf.getvalue()))
                else:
                    parts.append(str(item))
            return parts
        return str(content)

    def generate_content(self, content):
        contents = self._to_contents(content)
        try:
            raw = self._client.models.generate_content(
                model=self._model_name,
                contents=contents,
                generation_config=self._config
            )
        except TypeError:
            # Some versions may not support generation_config param
            raw = self._client.models.generate_content(
                model=self._model_name,
                contents=contents
            )
        return _ResponseWrapper(raw)

# Base models (wrapped to preserve previous API)
text_model = _ModelWrapper('gemini-2.5-flash', _genai_client)

# Deterministic config for classification
classification_generation_config = {
    "temperature": 0.1,
    "max_output_tokens": 4096,
}

classification_model = _ModelWrapper('gemini-2.0-flash', _genai_client, generation_config=classification_generation_config)

def process_math_problem(prompt: str, image_data=None) -> str:
    """Process a math problem using Gemini API.
    image_data can be PIL.Image.Image or bytes. When bytes are given, convert to PIL.Image.
    Returns model text.
    """
    try:
        if image_data:
            if isinstance(image_data, (bytes, bytearray)):
                img = Image.open(io.BytesIO(image_data))
            elif isinstance(image_data, Image.Image):
                img = image_data
            else:
                img = image_data  # attempt to pass-through
            vision_model = _ModelWrapper('gemini-2.0-flash', _genai_client)
            response = vision_model.generate_content([prompt, img])
        else:
            response = text_model.generate_content(prompt)
        # Prefer response.text
        return getattr(response, "text", "").strip() or str(response)
    except Exception as e:
        # re-raise; views will map to HTTP responses
        raise

def extract_text_from_genai_response(res) -> str:
    """Robust extraction for google.generativeai responses."""
    if isinstance(res, str):
        return res
    try:
        txt = getattr(res, "text", None)
        if isinstance(txt, str) and txt.strip():
            return txt
    except Exception:
        pass

    result = getattr(res, "result", None)
    if result is not None:
        parts = getattr(result, "parts", None)
        if parts:
            out = []
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    out.append(t)
            if out:
                return "".join(out)
        candidates = getattr(result, "candidates", None)
        if candidates:
            for cand in candidates:
                content = getattr(cand, "content", None)
                if content:
                    parts = getattr(content, "parts", None)
                    if parts:
                        out = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
                        if any(out):
                            return "".join(out)
                if getattr(cand, "text", None):
                    return cand.text

    candidates = getattr(res, "candidates", None) or getattr(res, "outputs", None) or getattr(res, "choices", None)
    if candidates:
        for cand in candidates:
            content = getattr(cand, "content", None)
            if content:
                parts = getattr(content, "parts", None)
                if parts:
                    out = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
                    if any(out):
                        return "".join(out)
            if getattr(cand, "text", None):
                return cand.text
            if getattr(cand, "output_text", None):
                return cand.output_text

    parts = getattr(res, "parts", None)
    if parts:
        out = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
        if any(out):
            return "".join(out)

    try:
        import logging
        logging.info("Unrecognized GenAI response shape; repr(response)=%s", repr(res))
    except Exception:
        pass
    return str(res)


import requests
from PIL import Image
import io

def process_math_problem_from_url(url: str, prompt: str = None) -> str:
    """
    Downloads an image from a given URL, analyzes it as a math problem using Gemini,
    and returns the AI-generated solution text.
    """
    try:
        # Download image from URL
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))

        # Default prompt if not given
        if not prompt or not str(prompt).strip():
            prompt = "Solve the math problem contained in this image."

        # Reuse the same process_math_problem function for uniform logic
        solution = process_math_problem(prompt, img)
        return solution
    except Exception as e:
        raise RuntimeError(f"Error processing math problem from URL: {str(e)}")