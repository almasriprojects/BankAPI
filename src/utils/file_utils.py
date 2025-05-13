import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def create_output_directory(bank_name: str, account_number: str, date: datetime) -> str:
    """
    Creates the output directory structure and returns the path.

    Args:
        bank_name: Name of the bank
        account_number: Account number
        date: Statement date

    Returns:
        str: Path to the output directory
    """
    output_path = Path("output") / bank_name / account_number / \
        str(date.year) / f"{date.month:02d}"
    output_path.mkdir(parents=True, exist_ok=True)
    return str(output_path)


def save_statement_json(data: Dict[str, Any], output_path: str, filename: str = "statement.json") -> str:
    """
    Saves the statement data as JSON.

    Args:
        data: Statement data to save
        output_path: Directory to save the file in
        filename: Name of the output file

    Returns:
        str: Full path to the saved file
    """
    file_path = Path(output_path) / filename
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    return str(file_path)


def extract_date_from_period(period: str) -> datetime:
    """
    Extracts a date from a statement period string.

    Args:
        period: Statement period string (e.g., "January 1, 2024 to January 31, 2024")

    Returns:
        datetime: Extracted date (uses the end date of the period)
    """
    # Simple parsing - assumes format "Month DD, YYYY to Month DD, YYYY"
    end_date_str = period.split(" to ")[-1]
    return datetime.strptime(end_date_str, "%B %d, %Y")
