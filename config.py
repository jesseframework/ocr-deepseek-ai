# config.py (Enhanced Configuration Management)
from pydantic import BaseSettings, Field, validator
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

class Settings(BaseSettings):
    # OCR Configuration
    ocr_api_key: str = Field(..., env="OCR_API_KEY")
    default_ocr_engine: str = Field("auto", env="DEFAULT_OCR_ENGINE")
    pdf_dpi: int = Field(300, env="PDF_DPI")
    max_file_size: int = Field(10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    ocr_engines: Dict[str, bool] = Field({
        "doctr": True,
        "easyocr": True,
        "tesseract": True
    }, env="OCR_ENGINES")
    
    # AI Configuration
    ai_api_key: Optional[str] = Field(None, env="AI_API_KEY")
    ai_api_base_url: str = Field("https://api.openai.com/v1/chat/completions", env="AI_API_BASE_URL")
    ai_model_name: str = Field("gpt-4", env="AI_MODEL_NAME")
    ai_model_type: str = Field("gpt", env="AI_MODEL_TYPE")  # gpt, llama, anthropic
    ai_temperature: float = Field(0.1, env="AI_TEMPERATURE")
    ai_stream: bool = Field(False, env="AI_STREAM")
    ai_timeout: int = Field(120, env="AI_TIMEOUT")
    
    # Path Configuration
    model_cache_dir: str = Field(str(Path.home() / ".cache" / "ocr_models"), env="MODEL_CACHE_DIR")
    static_files_dir: str = Field(str(Path(__file__).parent / "static"), env="STATIC_FILES_DIR")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Validation
    @validator("default_ocr_engine")
    def validate_engine(cls, v):
        if v not in ["auto", "doctr", "easyocr", "tesseract"]:
            raise ValueError("Invalid OCR engine specified")
        return v
    
    @validator("pdf_dpi")
    def validate_dpi(cls, v):
        if not 72 <= v <= 600:
            raise ValueError("DPI must be between 72 and 600")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False

# Initialize settings
try:
    settings = Settings()
except Exception as e:
    logging.error(f"Configuration error: {str(e)}")
    raise

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)