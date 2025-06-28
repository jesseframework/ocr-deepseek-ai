# ai_model.py (Enhanced AI Integration)
import os
import json
import re
import requests
from typing import Dict, Any, List, Optional
from config import settings
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import logging
from pydantic import BaseModel, ValidationError

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
    if not settings.ai_api_key:
        logger.warning("AI processing disabled - no API key configured")
        return {"error": "AI processing disabled - no API key configured"}
    
    prompt = _build_prompt(ocr_text)
    headers = _prepare_headers()
    payload = _prepare_payload(prompt)

    logger.info("----- AI PROMPT -----")
    logger.info(prompt)

    logger.info("----- AI PAYLOAD -----")
    logger.info(json.dumps(payload, indent=2))
    
    try:
        response = _call_ai_api(headers, payload)
        content = _process_ai_response(response)

        json_data = None
        for extractor in [_extract_json_strict, _extract_json_relaxed, _extract_json_fallback]:
            try:
                json_data = extractor(content)
                if json_data:
                    break
            except Exception as e:
                logger.debug(f"JSON extraction attempt failed: {str(e)}")
        
        if not json_data:
            raise ValueError("All JSON extraction attempts failed")

        try:
            validated = AIResponse(
                #dto=InvoiceDTO(**json_data.get("dto", {})),
                dto=InvoiceDTO(**json_data),
                #raw_response=json_data
            )
            return validated.dict()
        except ValidationError as ve:
            logger.warning(f"Response validation failed: {str(ve)}")
            return {
                "partial_result": json_data,
                "validation_errors": str(ve),
                "warning": "Response validation failed"
            }

    except Exception as e:
        logger.error(f"AI processing failed: {str(e)}")
        return {
            "error": str(e),
            "original_prompt": prompt[:200] + "..." if prompt else None,
            "suggestion": "Check the API response format"
        }

def _build_prompt(ocr_text: str) -> str:
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
        return f"""Extract invoice data from OCR text into this JSON format:
{example.json(indent=2)}

OCR Text:
{ocr_text}

Respond ONLY with valid JSON matching this format.
"""
    elif settings.ai_model_type.lower() == "anthropic":
        return f"""Extract invoice data into this exact JSON format:
{example.json(indent=2)}

From this OCR text:
{ocr_text}

Respond ONLY with valid JSON.
"""
    else:
        return f"""Extract invoice data from OCR text into this JSON format:
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
    return {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def _prepare_payload(prompt: str) -> Dict[str, Any]:
    if not settings.ai_model_name:
        raise ValueError("AI model name not configured")

    # Safely handle ai_max_tokens
    try:
        max_tokens = int(getattr(settings, "ai_max_tokens", 2000))
        if not (100 <= max_tokens <= 4000):
            logger.warning(f"Invalid ai_max_tokens value ({max_tokens}), using fallback 2000")
            max_tokens = 2000
    except Exception as e:
        logger.warning(f"ai_max_tokens access failed: {str(e)} — using fallback 2000")
        max_tokens = 2000

    payload = {
        "model": settings.ai_model_name,
        "messages": [
            {"role": "system", "content": "You are a strict data extractor. Respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": max(0, min(float(settings.ai_temperature), 2)),
        "max_tokens": min(4000, max_tokens)
    }

    if settings.ai_model_type.lower() in ["gpt"]:
        payload["response_format"] = {"type": "json_object"}

    return payload

def _call_ai_api(headers: Dict[str, str], payload: Dict[str, Any]):
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
        logger.error(f"AI API request failed. Status: {e.response.status_code if hasattr(e, 'response') else 'No response'}")
        logger.error(f"Response text: {e.response.text if hasattr(e, 'response') else ''}")
        raise

def _process_ai_response(response) -> str:
    try:
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
            response_json = response.json()
            if "choices" not in response_json:
                raise ValueError("Invalid response format: missing 'choices'")
            return response_json["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Failed to process AI response: {str(e)}")
        logger.error(f"Raw response: {response.text[:500]}")
        raise

def _extract_json_strict(content: str) -> Dict:
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        raise ValueError("No valid JSON found in strict mode")

def _extract_json_relaxed(content: str) -> Dict:
    try:
        clean_content = content.strip()
        if clean_content.startswith('```json'):
            clean_content = clean_content[7:-3].strip()
        elif clean_content.startswith('```'):
            clean_content = clean_content[3:-3].strip()
        return json.loads(clean_content)
    except json.JSONDecodeError:
        lines = [line for line in content.split('\n') if line.strip()]
        for line in lines:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        raise ValueError("No valid JSON found in relaxed mode")

def _extract_json_fallback(content: str) -> Dict:
    try:
        start = content.find('{')
        end = content.rfind('}')
        if start >= 0 and end > start:
            return json.loads(content[start:end+1])
        raise ValueError("No JSON structure found")
    except json.JSONDecodeError as e:
        raise ValueError(f"Fallback extraction failed: {str(e)}")

def _validate_response(content: str) -> AIResponse:
    content = content.strip()
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if not json_match:
        raise ValueError("No JSON found in AI response")
    
    try:
        raw_data = json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from AI: {str(e)}")
    
    try:
        return AIResponse(
            dto=InvoiceDTO(**raw_data.get("dto", {})),
            raw_response=raw_data
        )
    except Exception as e:
        raise ValueError(f"Response validation failed: {str(e)}")
