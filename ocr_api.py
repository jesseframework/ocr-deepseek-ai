# ocr_api.py (Enhanced with reliable AI processing)
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from typing import Optional, Dict, Any
import os
from pathlib import Path
from config import settings
from invoice_parser import InvoiceParser
from dynamic_invoice_parser import DynamicInvoiceParser
from ocr_engine import ocr_processor
from ai_model import process_with_ai
import logging
import time
from datetime import datetime
from parsers.adaptive_invoice_parser import AdaptiveInvoiceParser
from template_routes import router as template_router


logger = logging.getLogger("OCRAPI")

app = FastAPI(
    title="Enhanced OCR Pipeline API",
    description="Multi-engine OCR with AI processing and advanced features",
    version="2.1.0",  # Updated version
    docs_url="/docs",
    redoc_url=None
)

# Enhanced CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-OCR-Engine", "X-Structure-Parsed", "X-AI-Processed"]
)

# Static files with cache control
app.mount("/static", StaticFiles(directory=settings.static_files_dir), name="static")
app.include_router(template_router)
@app.on_event("startup")
async def startup_event():
    """Enhanced startup with health checks"""
    logger.info("Starting Enhanced OCR API Service")
    logger.info(f"Configuration: {settings.json(indent=2)}")
    
    # Verify directories
    os.makedirs(settings.model_cache_dir, exist_ok=True)
    os.makedirs(settings.static_files_dir, exist_ok=True)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware for request timing"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    """Enhanced global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
    
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "error": str(exc),
            "type": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "suggestion": "Please check the file and try again",
            "supported_formats": ["pdf", "png", "jpg", "jpeg"]
        })
    )

@app.get("/health", include_in_schema=False)
async def health_check():
    """Enhanced health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "ocr_engines": settings.ocr_engines,
            "ai_enabled": bool(settings.ai_api_key),
            "structured_parsing": True
        }
    }

@app.post("/api/v2/process")
async def process_document(
    request: Request,
    file: UploadFile = File(...),
    x_api_key: str = Header(...),
    engine: Optional[str] = None,
    ai_processing: Optional[bool] = True,
    detailed: Optional[bool] = False,
    parse_structure: Optional[bool] = False
):
    """
    Enhanced document processing endpoint with:
    - Authentication
    - File validation
    - Engine selection
    - AI integration (when enabled)
    - Detailed metadata
    - Optional structured parsing
    """
    # Authentication
    if x_api_key != settings.ocr_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # File validation
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )
    
    # Read file with size limit
    try:
        start_read = time.time()
        file_bytes = await file.read()
        read_time = time.time() - start_read
        
        if len(file_bytes) > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {settings.max_file_size} bytes"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Process with OCR
    try:
        start_ocr = time.time()
        text, engine_used = ocr_processor.process_file(
            file_bytes,
            file.filename,
            engine or settings.default_ocr_engine
        )
        ocr_time = time.time() - start_ocr
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OCR processing failed: {str(e)}"
        )

    # Initialize result containers
    ai_result = None
    ai_time = 0
    ai_status = "disabled"
    ai_error = None
    structured_data = None
    parse_time = 0
    analysis = {
        "field_completeness": "0%",
        "contains_vendor": False,
        "contains_items": False
    }

    # AI Processing (enhanced with proper error handling)
    if ai_processing and settings.ai_api_key:
        try:
            start_ai = time.time()
            raw_ai_result = process_with_ai(text)
            ai_time = time.time() - start_ai

            if "error" in raw_ai_result:
                ai_status = "failed"
                logger.error(f"AI processing failed: {raw_ai_result['error']}")
                ai_result = {
                    "error": raw_ai_result["error"],
                    "type": "ai_processing_error",
                    "suggestion": raw_ai_result.get("suggestion", "Check your API configuration"),
                    "original_prompt": raw_ai_result.get("original_prompt", None)
                }
            else:
                ai_status = "success"
                ai_result = raw_ai_result
                logger.info(f"AI processing completed in {ai_time:.2f}s")
                
        except Exception as e:
            ai_status = "error"
            ai_result = {
                "error": str(e),
                "type": "unexpected_error",
                "suggestion": "Check the API connection and configuration"
            }
            logger.error(f"AI processing critical error: {str(e)}", exc_info=True)

    # Structured Data Parsing
    if parse_structure:
        try:
            start_parse = time.time()
            # parser = DynamicInvoiceParser()
            # structured_data = parser.parse(text)

            try:
                start_parse = time.time()
                adaptive_parser = AdaptiveInvoiceParser()
                structured_data = adaptive_parser.parse(text)
                parse_time = time.time() - start_parse

                if isinstance(structured_data, dict):
                    if "error" in structured_data:
                        analysis.update({
                            "error": structured_data.get("error"),
                            "field_completeness": "0%",
                            "contains_vendor": False,
                            "contains_items": False
                        })
                    else:
                        analysis.update({
                            "field_completeness": structured_data.get("_completeness", "0%"),
                            "contains_vendor": bool(structured_data.get("vendor", {}).get("name")),
                            "contains_items": len(structured_data.get("items", [])) > 0
                        })

                # Optional fallback: Dynamic parser if low confidence
                if structured_data.get("_confidence_score", 0) < 0.6:
                    logger.info("Low confidence from AdaptiveParser. Falling back to DynamicInvoiceParser.")
                    structured_data.update({
                        "_parser_fallback_used": True
                    })
                    fallback_data = DynamicInvoiceParser().parse(text)
                    structured_data.update(fallback_data)
                    analysis["fallback_parser"] = "DynamicInvoiceParser"

            except Exception as e:
                logger.error(f"Structured parsing failed: {str(e)}")
                structured_data = {
                    "error": f"Parsing error: {str(e)}",
                    "original_text_sample": text[:200] + "..." if text else None
                }
                analysis.update({
                    "error": "Parsing failed",
                    "field_completeness": "0%",
                    "contains_vendor": False,
                    "contains_items": False
                })


            parse_time = time.time() - start_parse

            if isinstance(structured_data, dict):
                if "error" in structured_data:
                    analysis.update({
                        "error": structured_data.get("error"),
                        "field_completeness": "0%",
                        "contains_vendor": False,
                        "contains_items": False
                    })
                else:
                    analysis.update({
                        "field_completeness": structured_data.get("_completeness", "0%"),
                        "contains_vendor": bool(structured_data.get("vendor", {}).get("name")),
                        "contains_items": len(structured_data.get("items", [])) > 0
                    })

            # Optional fallback: AI if confidence is too low
            if structured_data.get("_fallback_needed") and ai_processing and settings.ai_api_key:
                logger.info("Low confidence detected. Fallback to AI enabled.")
                structured_data = process_with_ai(text)

        except Exception as e:
            logger.error(f"Structured parsing failed: {str(e)}")
            structured_data = {
                "error": f"Parsing error: {str(e)}",
                "original_text_sample": text[:200] + "..." if text else None
            }
            analysis.update({
                "error": "Parsing failed",
                "field_completeness": "0%",
                "contains_vendor": False,
                "contains_items": False
            })


    # Prepare comprehensive response
    response_data = {
        "status": "success",
        "engine_used": engine_used,
        "ocr_text": text,
        "timing": {
            "file_read": read_time,
            "ocr_processing": ocr_time,
            "ai_processing": ai_time,
            "structure_parsing": parse_time,
            "total": time.time() - start_read
        }
    }

    # Include AI results if processing was attempted
    if ai_processing:
        if ai_result:
            response_data["ai_result"] = ai_result
        if ai_error:
            response_data["ai_error"] = ai_error

    # Include structured data if requested
    if parse_structure:
        response_data["structured_data"] = structured_data
        response_data["analysis"] = analysis

    # Add detailed metadata if requested
    if detailed:
        response_data["metadata"] = {
            "filename": file.filename,
            "size": len(file_bytes),
            "content_type": file.content_type,
            "ocr_engine_config": {
                "default_engine": settings.default_ocr_engine,
                "available_engines": [k for k, v in settings.ocr_engines.items() if v]
            },
            "processing_capabilities": {
                "ai_processing": bool(settings.ai_api_key),
                "ai_model": settings.ai_model_name if settings.ai_api_key else None,
                "structure_parsing": True,
                "parser_version": "2.1"
            }
        }

    # Set response headers
    response = JSONResponse(content=response_data)
    response.headers["X-OCR-Engine"] = engine_used
    if parse_structure:
        response.headers["X-Structure-Parsed"] = "true"
    if ai_processing and settings.ai_api_key:
        response.headers["X-AI-Processed"] = "true" if not ai_error else "false"
    
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
        access_log=False,
        timeout_keep_alive=120
    )