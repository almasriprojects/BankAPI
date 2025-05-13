from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .routes.statement_routes import router as statement_router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Chase Bank Statement Parser",
    description="API for processing Chase Bank statements using OpenAI",
    version="1.0.0"
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
