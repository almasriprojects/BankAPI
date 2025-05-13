from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path
from dotenv import load_dotenv

from .routes.statement_routes import router as statement_router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Chase Bank Statement Parser",
    description="""
    A powerful API service that processes Chase Bank statements (PDF) 
    using OpenAI, converting them into structured JSON data.
    
    ## Features
    - PDF statement upload and processing
    - OpenAI-powered document parsing
    - Structured JSON output
    - Organized file storage system
    - Transaction categorization
    - Spending analysis
    - Balance validation
    
    ## API Endpoints
    - POST `/upload-statement`: Upload and process a bank statement
    - GET `/health`: Check API health status
    
    ## Authentication
    Currently, this API requires an OpenAI API key to be set in the 
    environment variables.
    
    ## Rate Limits
    - Standard rate limits apply
    - File size limit: 20MB
    - Supported formats: PDF
    
    ## Response Format
    The API returns structured JSON data including:
    - Transaction details
    - Account summary
    - Spending analysis
    - Validation results
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(statement_router, tags=["Statement Processing"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint providing project information and documentation links.
    """
    template_path = Path(__file__).parent / "templates" / "index.html"
    return template_path.read_text()


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status information
    """
    return {
        "status": "healthy",
        "service": "chase-statement-parser",
        "version": "1.0.0"
    }
