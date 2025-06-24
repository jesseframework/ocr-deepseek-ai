# ai_model.py (Enhanced AI Integration)
import os
import json
import re
import requests
from typing import Dict, Any, List, Optional
from config import settings
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import logging
from pydantic import BaseModel

logger = logging.getLogger("AIModel")

# Define structured output model
class InvoiceDTO(BaseModel):
    InvoiceNumber: Optional[str] = None
    InvoiceDate: Optional[str] = None
    DueDate: Optional[str] = None
    InvoiceAmount: Optional[float] = None
    TaxAmount: Optional[float] = None
    NetAmount: Optional[float] = None
    Currency: Optional[str] = "USD"
    PaymentStatus: Optional[str] = None
    PONumber: Optional[str] = None
    Description: Optional[str] = None
    VendorName: Optional[str] = None
    ProductCategory: Optional[str] = None
    AIAccuracyScore: Optional[float] = None

class AIResponse(BaseModel):
    dto: InvoiceDTO
    raw_response: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def process_with_ai(ocr_text: str) -> Dict[str, Any]:
    """
    Enhanced AI processing with:
    - Model-specific prompts
    - Structured output validation
    - Streaming support
    - Comprehensive error handling
    """
    if not settings.ai_api_key:
        raise ValueError("AI processing disabled - no API key configured")
    
    prompt = _build_prompt(ocr_text)
    headers = _prepare_headers()
    payload = _prepare_payload(prompt)
    
    try:
        response = _call_ai_api(headers, payload)
        processed_response = _process_ai_response(response)
        validated_response = _validate_response(processed_response)
        
        return validated_response.dict()
    except Exception as e:
        logger.error(f"AI processing failed: {str(e)}")
        raise

def _build_prompt(ocr_text: str) -> str:
    """Model-specific prompt engineering"""
    example = InvoiceDTO(
        InvoiceNumber="INV-123456",
        InvoiceDate="2024-06-19",
        DueDate="2024-07-19",
        InvoiceAmount=100.0,
        TaxAmount=15.0,
        NetAmount=85.0,
        PaymentStatus="PAID",
        VendorName="Vendor ABC Ltd.",
        ProductCategory="Office Supplies",
        AIAccuracyScore=97.5
    )
    
    if settings.ai_model_type.lower() == "llama":
        return f"""
Extract invoice data from OCR text into this JSON format:
{example.json(indent=2)}

OCR Text:
{ocr_text}

Respond ONLY with valid JSON matching this format.
"""
    elif settings.ai_model_type.lower() == "anthropic":
        return f"""
Extract invoice data into this exact JSON format:
{example.json(indent=2)}

From this OCR text:
{ocr_text}

Respond ONLY with valid JSON.
"""
    else:  # Default GPT-style
        return f"""
Extract invoice data from OCR text into this JSON format:
{example.json(indent=2)}

Rules:
- Use exact values from OCR when possible
- Missing fields = null
- Combine descriptions
- Estimate AIAccuracyScore 0-100
- STRICT valid JSON only

OCR Text:
{ocr_text}
"""

def _prepare_headers() -> Dict[str, str]:
    """Prepare request headers"""
    return {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def _prepare_payload(prompt: str) -> Dict[str, Any]:
    """Prepare request payload with model-specific settings"""
    payload = {
        "model": settings.ai_model_name,
        "messages": [
            {"role": "system", "content": "You are a strict data extractor. Respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": settings.ai_temperature,
        "max_tokens": 2000
    }
    
    if settings.ai_model_type.lower() in ["gpt", "anthropic"]:
        payload["response_format"] = {"type": "json_object"}
    
    return payload

def _call_ai_api(headers: Dict[str, str], payload: Dict[str, Any]):
    """Make the API call with timeout handling"""
    try:
        response = requests.post(
            settings.ai_api_base_url,
            headers=headers,
            json=payload,
            timeout=settings.ai_timeout,
            stream=settings.ai_stream
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"AI API request failed: {str(e)}")
        raise

def _process_ai_response(response) -> str:
    """Process streaming or non-streaming response"""
    if settings.ai_stream:
        full_content = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    if "choices" in data and data["choices"][0]["delta"].get("content"):
                        full_content += data["choices"][0]["delta"]["content"]
                except json.JSONDecodeError:
                    continue
        return full_content
    else:
        return response.json()["choices"][0]["message"]["content"]

def _validate_response(content: str) -> AIResponse:
    """Validate and clean the AI response"""
    content = content.strip()
    
    # Extract JSON
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if not json_match:
        raise ValueError("No JSON found in AI response")
    
    try:
        raw_data = json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from AI: {str(e)}")
    
    # Validate against our model
    try:
        return AIResponse(
            dto=InvoiceDTO(**raw_data.get("dto", {})),
            raw_response=raw_data
        )
    except Exception as e:
        raise ValueError(f"Response validation failed: {str(e)}")