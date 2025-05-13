from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import logging
import sys

from ..services.statement_service import StatementService
from ..models.statement_models import StatementResponse

# Configure logging with more details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

router = APIRouter()


def get_statement_service() -> StatementService:
    """Creates a StatementService instance."""
    logger.debug("Creating StatementService instance")
    return StatementService()


@router.post("/upload-statement", response_model=StatementResponse)
async def upload_statement(
    file: UploadFile = File(...),
    service: StatementService = Depends(get_statement_service)
) -> StatementResponse:
    """
    Processes an uploaded bank statement.

    Args:
        file: Uploaded PDF file
        service: Statement processing service

    Returns:
        StatementResponse: Processed statement data and metadata
    """
    logger.info(f"Received file upload: {file.filename}")

    if not file.filename.endswith('.pdf'):
        logger.error(f"Invalid file type: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    try:
        content = await file.read()
        logger.info("Successfully read file content")

        if len(content) == 0:
            logger.error("Empty file uploaded")
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty"
            )

        return await service.process_statement(content)
    except ValueError as e:
        logger.error(f"Value error processing statement: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing statement: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing statement: {str(e)}"
        )
