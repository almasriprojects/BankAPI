import io
import base64
from PIL import Image
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB in bytes
SUPPORTED_FORMATS = {'PNG', 'JPEG', 'WEBP', 'GIF'}
MAX_DIMENSION = 2048
OPTIMAL_DIMENSION = 768


def validate_and_optimize_image(image_bytes: bytes) -> Tuple[str, bool]:
    """
    Validates and optimizes an image for the OpenAI Vision API.

    Args:
        image_bytes: Raw image bytes

    Returns:
        Tuple[str, bool]: (base64 encoded image, is_valid)
    """
    try:
        # Check file size
        if len(image_bytes) > MAX_FILE_SIZE:
            logger.error(f"Image size {len(image_bytes)} exceeds maximum size of {MAX_FILE_SIZE}")
            return None, False

        # Open and validate image
        image = Image.open(io.BytesIO(image_bytes))

        # Check format
        if image.format not in SUPPORTED_FORMATS:
            logger.error(f"Unsupported image format: {image.format}")
            return None, False

        # Check if GIF is animated
        if image.format == 'GIF' and getattr(image, 'is_animated', False):
            logger.error("Animated GIFs are not supported")
            return None, False

        # Resize if needed
        width, height = image.size
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            # Calculate new dimensions maintaining aspect ratio
            ratio = min(MAX_DIMENSION/width, MAX_DIMENSION/height)
            new_size = (int(width * ratio), int(height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Resized image from {width}x{height} to {new_size[0]}x{new_size[1]}")

        # Optimize for vision API
        if width > OPTIMAL_DIMENSION or height > OPTIMAL_DIMENSION:
            ratio = OPTIMAL_DIMENSION / min(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to RGB if needed
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')

        # Save optimized image
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85, optimize=True)
        optimized_bytes = buffer.getvalue()

        # Convert to base64
        base64_image = base64.b64encode(optimized_bytes).decode('utf-8')

        return base64_image, True

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return None, False
