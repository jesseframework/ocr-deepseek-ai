# OCR API with FastAPI

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)

A high-performance OCR API service supporting multiple OCR engines (Doctr, EasyOCR, Tesseract) with FastAPI backend.

## Features

- Multiple OCR engine support (Doctr, EasyOCR, Tesseract)
- PDF and image file processing
- Dockerized deployment
- Automatic text extraction with clean formatting
- Performance metrics in response
- Configurable via environment variables

## Prerequisites

- Docker 20.10+
- Docker Compose 1.29+ (optional)
- Python 3.10+ (for local development)

## Quick Start

### Using Docker

```bash
# Build the image
docker build -t ocr-api .

# Run the container
docker run -p 8000:8000 -e OCR_API_KEY=your_key_here ocr-api

# Create .env file
echo "OCR_API_KEY=your_key_here" > .env

# Start services
docker-compose up -d

The API will be available at http://localhost:8000

API Documentation
Once running, access the interactive docs at:
http://localhost:8000/docs

Endpoints
POST /ocr - Process document

Parameters:

file: The document to process

engine (optional): Specific OCR engine to use (doctr, easyocr, or tesseract)

Configuration
Environment variables:

Variable	Description	Default
OCR_API_KEY	API access key	(required)
DEFAULT_ENGINE	Preferred OCR engine	auto
MODELS_DIR	Path for model storage	/app/models

Development Setup
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn ocr_api:app --reload
Project Structure
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── app/
│   ├── ocr_api.py       # Main FastAPI application
│   ├── config.py        # Configuration settings
│   ├── ocr_engine.py    # OCR processing logic
│   └── ai_model.py      # AI processing (if applicable)
├── models/              # OCR model storage
└── static/              # Static files

Contributing
We welcome contributions! Please follow these steps:

Fork the repository

Create your feature branch (git checkout -b feature/amazing-feature)

Commit your changes (git commit -m 'Add some amazing feature')

Push to the branch (git push origin feature/amazing-feature)

Open a Pull Request



