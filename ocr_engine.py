# ocr_engine.py (Enhanced OCR Engine)
import os
import io
import logging
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import pytesseract
import easyocr
from doctr.models import ocr_predictor
from doctr.io import DocumentFile
from typing import Tuple, List, Optional, Dict
from config import settings
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

logger = logging.getLogger("OCREngine")

class OCRProcessor:
    """
    Advanced OCR Processor with multiple engines and automatic fallback
    Features:
    - Automatic model downloading
    - Engine-specific optimizations
    - Comprehensive error handling
    - Retry mechanisms
    - Resource management
    """
    
    def __init__(self):
        self.easyocr_reader = None
        self._doctr_model = None
        self._init_engines()
    
    def _init_engines(self):
        """Initialize OCR engines with configuration"""
        # EasyOCR initialization
        if settings.ocr_engines.get("easyocr", True):
            try:
                self.easyocr_reader = easyocr.Reader(
                    ['en'], 
                    gpu=False,
                    download_enabled=True,
                    model_storage_directory=os.path.join(settings.model_cache_dir, 'easyocr'),
                    user_network_directory=os.path.join(settings.model_cache_dir, 'easyocr_net')
                )
                logger.info("EasyOCR initialized successfully")
            except Exception as e:
                logger.error(f"EasyOCR initialization failed: {str(e)}")
                if settings.ocr_engines["easyocr"]:  # If required
                    raise
        
        # Doctr will be lazy-loaded
    
    @property
    def doctr_model(self):
        """Lazy-loaded Doctr model"""
        if settings.ocr_engines.get("doctr", True):
            if self._doctr_model is None:
                try:
                    logger.info("Initializing Doctr model...")
                    self._doctr_model = ocr_predictor(
                        det_arch='db_resnet50', 
                        reco_arch='crnn_vgg16_bn', 
                        pretrained=True
                    )
                    logger.info("Doctr model loaded successfully")
                except Exception as e:
                    logger.error(f"Doctr initialization failed: {str(e)}")
                    if settings.ocr_engines["doctr"]:  # If required
                        raise
        return self._doctr_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def process_file(self, file_bytes: bytes, filename: str, engine: str = None) -> Tuple[str, str]:
        """
        Process file with OCR with advanced features:
        - Automatic engine selection
        - Fallback mechanisms
        - Resource optimization
        - Detailed logging
        """
        engine = engine or settings.default_ocr_engine
        logger.info(f"Processing file with engine: {engine}")
        
        try:
            if engine == "auto":
                return self._auto_process(file_bytes, filename)
            elif engine == "doctr":
                return self._doctr_process(file_bytes, filename)
            elif engine == "easyocr":
                return self._easyocr_process(file_bytes, filename)
            elif engine == "tesseract":
                return self._tesseract_process(file_bytes, filename)
            else:
                raise ValueError(f"Unsupported OCR engine: {engine}")
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            raise

    def _auto_process(self, file_bytes: bytes, filename: str) -> Tuple[str, str]:
        """Smart auto-selection of OCR engine with fallback"""
        engines_order = ["doctr", "easyocr", "tesseract"]
        last_exception = None
        
        for engine in engines_order:
            if not settings.ocr_engines.get(engine, True):
                continue
                
            try:
                if engine == "doctr":
                    return self._doctr_process(file_bytes, filename)
                elif engine == "easyocr":
                    return self._easyocr_process(file_bytes, filename)
                elif engine == "tesseract":
                    return self._tesseract_process(file_bytes, filename)
            except Exception as e:
                last_exception = e
                logger.warning(f"{engine} failed: {str(e)}")
                continue
        
        raise Exception("All OCR engines failed") from last_exception

    def _doctr_process(self, file_bytes: bytes, filename: str) -> Tuple[str, str]:
        """Advanced Doctr processing with optimizations"""
        if not settings.ocr_engines.get("doctr", True):
            raise ValueError("Doctr engine is disabled")
        
        file_stream = io.BytesIO(file_bytes)
        
        try:
            if filename.lower().endswith(".pdf"):
                images = self._rasterize_pdf(file_stream)
                doc = DocumentFile.from_images(images)
            else:
                image = Image.open(file_stream).convert("RGB")
                doc = DocumentFile.from_images([image])
            
            result = self.doctr_model(doc)
            text = self._parse_doctr_result(result)
            return text, "doctr"
        except Exception as e:
            logger.error(f"Doctr processing failed: {str(e)}")
            raise

    def _easyocr_process(self, file_bytes: bytes, filename: str) -> Tuple[str, str]:
        """Optimized EasyOCR processing"""
        if not settings.ocr_engines.get("easyocr", True):
            raise ValueError("EasyOCR engine is disabled")
        if not self.easyocr_reader:
            raise Exception("EasyOCR not initialized")
        
        try:
            if filename.lower().endswith(".pdf"):
                images = self._rasterize_pdf(io.BytesIO(file_bytes))
                results = []
                for img_bytes in images:
                    img_array = np.frombuffer(img_bytes, np.uint8)
                    result = self.easyocr_reader.readtext(
                        img_array, 
                        detail=0, 
                        paragraph=True,
                        batch_size=4,
                        workers=0
                    )
                    results.append("\n".join(result))
                text = "\n".join(results)
            else:
                result = self.easyocr_reader.readtext(
                    file_bytes, 
                    detail=0, 
                    paragraph=True,
                    batch_size=4,
                    workers=0
                )
                text = "\n".join(result)
            
            return text, "easyocr"
        except Exception as e:
            logger.error(f"EasyOCR processing failed: {str(e)}")
            raise

    def _tesseract_process(self, file_bytes: bytes, filename: str) -> Tuple[str, str]:
        """Optimized Tesseract processing"""
        if not settings.ocr_engines.get("tesseract", True):
            raise ValueError("Tesseract engine is disabled")
        
        try:
            if filename.lower().endswith(".pdf"):
                images = self._rasterize_pdf(io.BytesIO(file_bytes))
                texts = []
                for img_bytes in images:
                    image = Image.open(io.BytesIO(img_bytes))
                    text = pytesseract.image_to_string(
                        image,
                        config='--psm 6 --oem 3'
                    )
                    texts.append(text)
                text = "\n".join(texts)
            else:
                image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
                text = pytesseract.image_to_string(
                    image,
                    config='--psm 6 --oem 3'
                )
            
            return text, "tesseract"
        except Exception as e:
            logger.error(f"Tesseract processing failed: {str(e)}")
            raise

    def _rasterize_pdf(self, file_stream, dpi: int = None) -> List[bytes]:
        """Optimized PDF rasterization with auto DPI adjustment"""
        dpi = dpi or settings.pdf_dpi
        images = []
        doc = fitz.open(stream=file_stream.read(), filetype="pdf")
        
        for page in doc:
            # Smart DPI adjustment based on page size
            page_dpi = min(dpi, int(300 * (11/page.rect.width * 72)))
            pix = page.get_pixmap(dpi=page_dpi)
            img_bytes = io.BytesIO(pix.tobytes("png"))
            images.append(img_bytes.getvalue())
        
        return images

    def _parse_doctr_result(self, result) -> str:
        """Enhanced Doctr result parsing"""
        lines = []
        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    words = [word.value for word in line.words]
                    if words:
                        lines.append(" ".join(words))
        return "\n".join(lines)

# Global instance with error handling
try:
    ocr_processor = OCRProcessor()
except Exception as e:
    logger.critical(f"OCR Processor initialization failed: {str(e)}")
    raise