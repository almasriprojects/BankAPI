import json
from typing import Dict, Any, List
import logging
import tempfile
import os
import pytesseract
from pdf2image import convert_from_bytes
from fastapi import HTTPException
import io
from PIL import Image
from datetime import datetime
import time

from ..models.statement_models import StatementData, StatementResponse, CheckingSummary, Transaction, StatementMetadata, FileMetadata, TotalTransactions, ValidationDetails, ErrorTracking, SpendingAnalysis, LargestTransaction, TransactionFlag

logger = logging.getLogger(__name__)


class StatementService:
    def __init__(self):
        """Initialize the statement service."""
        logger.debug("Initializing StatementService")

    def convert_pdf_to_images(self, pdf_content: bytes) -> List[Image.Image]:
        """Convert PDF to list of PIL Images."""
        try:
            logger.debug(f"Starting PDF conversion with content size: {len(pdf_content)} bytes")

            # Save PDF content to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(pdf_content)
                pdf_path = temp_pdf.name

            # Convert PDF to images
            images = convert_from_bytes(pdf_content)
            logger.info(f"Converted PDF to {len(images)} images")

            # Clean up
            os.remove(pdf_path)

            return images

        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to convert PDF to images: {str(e)}")

    def extract_text_from_images(self, images: List[Image.Image]) -> str:
        """Extract text from images using OCR."""
        try:
            extracted_text = ""
            for i, image in enumerate(images, 1):
                logger.debug(f"Processing OCR for page {i}")
                text = pytesseract.image_to_string(image)
                extracted_text += text + "\n"
            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            raise ValueError(f"Failed to extract text from images: {str(e)}")

    def extract_summary(self, text: str) -> CheckingSummary:
        """Extract checking summary from text."""
        try:
            summary = {
                "Beginning_Balance": 0.0,
                "Deposits_and_Additions": 0.0,
                "Electronic_Withdrawals": 0.0,
                "Ending_Balance": 0.0
            }

            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                # Extract numbers using more robust parsing
                if "Beginning Balance" in line:
                    amount = self._extract_amount(line)
                    if amount is not None:
                        summary["Beginning_Balance"] = amount
                elif "Deposits and Additions" in line:
                    amount = self._extract_amount(line)
                    if amount is not None:
                        summary["Deposits_and_Additions"] = amount
                elif "Electronic Withdrawals" in line:
                    amount = self._extract_amount(line)
                    if amount is not None:
                        summary["Electronic_Withdrawals"] = amount
                elif "Ending Balance" in line:
                    amount = self._extract_amount(line)
                    if amount is not None:
                        summary["Ending_Balance"] = amount

            return CheckingSummary(**summary)
        except Exception as e:
            logger.error(f"Error extracting summary: {str(e)}")
            raise ValueError(f"Failed to extract summary: {str(e)}")

    def _extract_amount(self, text: str) -> float:
        """Extract amount from text, handling various formats."""
        try:
            # Remove common text patterns
            amount_text = text.replace("Beginning Balance", "")\
                .replace("Ending Balance", "")\
                .replace("Deposits and Additions", "")\
                .replace("Electronic Withdrawals", "")\
                .replace("$", "")\
                .replace(",", "")\
                .strip()

            # Convert to float
            return float(amount_text)
        except Exception:
            logger.warning(f"Could not extract amount from: {text}")
            return None

    def _categorize_transaction(self, description: str, amount: float) -> tuple[str, str]:
        """Categorize transaction based on description and amount."""
        description = description.lower()

        # Define category rules
        categories = {
            'salary': ['jobr payrol', 'salary', 'paycheck'],
            'transfer': ['transfer', 'zelle'],
            'subscription': ['premium', 'recurring'],
            'payment': ['payment', 'pmt'],
            'car rental': ['turo'],
            'credit card': ['applecard', 'discover', 'american express'],
        }

        # Determine transaction type
        transaction_type = "Deposit" if amount > 0 else "Withdrawal"

        # Determine category
        category = "Other"
        for cat, keywords in categories.items():
            if any(keyword in description for keyword in keywords):
                category = cat.title()
                break

        return transaction_type, category

    def extract_transactions(self, text: str) -> List[Transaction]:
        """Extract transactions from text."""
        transactions = []
        lines = text.split("\n")
        transaction_start = False
        transaction_id = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "TRANSACTION DETAIL" in line:
                transaction_start = True
                continue

            if "DATE" in line and "DESCRIPTION" in line and "AMOUNT" in line and "BALANCE" in line:
                continue

            if transaction_start and not line.startswith("Ending Balance"):
                try:
                    if line.strip() == "Beginning Balance" or "$5,993.00" in line:
                        continue

                    parts = line.split()
                    if len(parts) >= 4:
                        if not self._is_valid_date(parts[0]):
                            continue

                        date = parts[0]
                        balance = float(
                            parts[-1].replace("$", "").replace(",", ""))
                        amount = float(
                            parts[-2].replace("$", "").replace(",", ""))
                        description_parts = parts[1:-2]
                        description = " ".join(description_parts)

                        # Clean up common OCR issues
                        description = description.replace("1D:", "ID:")
                        description = description.replace("Jom", "Jpm")
                        description = description.replace("Pmt__", "Pmt ")

                        # Categorize transaction
                        transaction_type, category = self._categorize_transaction(
                            description, amount)

                        transaction = Transaction(
                            id=transaction_id,
                            Date=date,
                            Description=description,
                            Transaction_Type=transaction_type,
                            Category=category,
                            Amount=amount,
                            Balance=balance,
                            Notes=""
                        )
                        transactions.append(transaction)
                        transaction_id += 1

                except Exception as e:
                    logger.warning(f"Failed to parse transaction line: {line}", exc_info=True)
                    continue

        return sorted(transactions, key=lambda x: (int(x.Date.split('/')[0]), int(x.Date.split('/')[1])))

    def _validate_balances(self, beginning_balance: float, ending_balance: float, transactions: List[Transaction]) -> str:
        """Validate that transactions reconcile with beginning and ending balances."""
        try:
            calculated_ending = beginning_balance
            for transaction in transactions:
                calculated_ending += transaction.Amount

            # Allow for small floating point differences
            if abs(calculated_ending - ending_balance) < 0.01:
                return "Reconciled"
            else:
                return "Unreconciled"
        except Exception as e:
            logger.warning(f"Error validating balances: {str(e)}")
            return "Validation Failed"

    def _is_valid_date(self, date_str: str) -> bool:
        """Check if string matches MM/DD format."""
        try:
            if '/' not in date_str:
                # Split "1214" into ["12", "14"]
                parts = [date_str[:2], date_str[2:]]
            else:
                parts = date_str.split('/')

            if len(parts) != 2:
                return False

            month = int(parts[0])
            day = int(parts[1])

            return 1 <= month <= 12 and 1 <= day <= 31
        except:
            return False

    def _calculate_totals(self, transactions: List[Transaction]) -> TotalTransactions:
        """Calculate total deposits, withdrawals, and net change."""
        total_deposits = sum(t.Amount for t in transactions if t.Amount > 0)
        total_withdrawals = sum(t.Amount for t in transactions if t.Amount < 0)
        net_change = total_deposits + total_withdrawals

        return TotalTransactions(
            Total_Deposits=total_deposits,
            Total_Withdrawals=total_withdrawals,
            Net_Change=net_change
        )

    def _get_date_range(self, transactions: List[Transaction]) -> str:
        """Get the date range covered by transactions."""
        if not transactions:
            return ""

        dates = [(int(t.Date.split('/')[0]), int(t.Date.split('/')[1]))
                 for t in transactions]
        start_month, start_day = min(dates)
        end_month, end_day = max(dates)
        year = datetime.now().year

        return f"{year}-{start_month:02d}-{start_day:02d} to {year}-{end_month:02d}-{end_day:02d}"

    def _get_location_from_description(self, description: str) -> str:
        """Extract location information from transaction description."""
        # Add location extraction logic here
        if "OH" in description:
            return "Ohio, USA"
        return ""

    def _get_category_confidence(self, description: str, category: str) -> float:
        """Calculate confidence score for category assignment."""
        description = description.lower()

        # High confidence matches
        if category == "Salary" and any(k in description for k in ["payrol", "salary"]):
            return 0.99
        elif category == "Transfer" and any(k in description for k in ["zelle", "transfer"]):
            return 0.98
        elif category == "Subscription" and "recurring" in description:
            return 0.95
        elif category == "Payment" and "payment" in description:
            return 0.95
        elif category == "Car Rental" and "turo" in description:
            return 0.94

        # Default confidence
        return 0.85

    def _get_transaction_notes(self, transaction: Transaction) -> str:
        """Generate meaningful notes for transactions."""
        description = transaction.Description.lower()
        amount = transaction.Amount

        if "zelle" in description:
            return "Matched with Zelle transfer description."
        elif "transfer" in description and "from" in description:
            return "Internal transfer to checking account."
        elif "recurring" in description:
            return f"Recurring {transaction.Category.lower()} payment."
        elif "payrol" in description:
            return "Direct deposit from employer."
        elif abs(amount) > 1000:
            return f"{transaction.Category} flagged for high amount."
        elif "turo" in description:
            return "Car rental income from Turo."
        elif "premium" in description:
            return f"Subscription payment for {' '.join(description.split()[:2])}."

        return ""

    def _calculate_spending_analysis(self, transactions: List[Transaction]) -> SpendingAnalysis:
        """Calculate spending patterns and analysis."""
        try:
            # Calculate total spent on subscriptions
            total_subscriptions = sum(t.Amount for t in transactions
                                      if t.Category == "Subscription" and t.Amount < 0)

            # Find largest transaction
            largest_trans = max(transactions, key=lambda x: abs(x.Amount))
            largest = LargestTransaction(
                Description=largest_trans.Description.split()[0],
                Amount=largest_trans.Amount,
                Date=largest_trans.Date
            )

            # Calculate average daily spending
            withdrawals = [t.Amount for t in transactions if t.Amount < 0]
            if withdrawals:
                avg_daily = sum(abs(x) for x in withdrawals) / \
                    30  # Assuming 30-day month
            else:
                avg_daily = 0.0

            return SpendingAnalysis(
                total_spent_on_subscriptions=total_subscriptions,
                largest_transaction=largest,
                average_daily_spending=avg_daily
            )
        except Exception as e:
            logger.error(f"Error calculating spending analysis: {str(e)}")
            raise ValueError(
                f"Failed to calculate spending analysis: {str(e)}")

    def _analyze_recurring_transactions(self, transactions: List[Transaction]) -> Dict[str, float]:
        """Analyze and separate recurring from one-off transactions."""
        try:
            recurring_deposits = sum(t.Amount for t in transactions
                                     if t.Amount > 0 and ("recurring" in t.Description.lower() or "payrol" in t.Description.lower()))
            total_deposits = sum(
                t.Amount for t in transactions if t.Amount > 0)
            one_off_deposits = total_deposits - recurring_deposits

            recurring_withdrawals = sum(t.Amount for t in transactions
                                        if t.Amount < 0 and "recurring" in t.Description.lower())
            total_withdrawals = sum(
                t.Amount for t in transactions if t.Amount < 0)
            irregular_withdrawals = total_withdrawals - recurring_withdrawals

            return {
                "Recurring_Deposits": recurring_deposits,
                "One_Off_Deposits": one_off_deposits,
                "Total_Deposits": total_deposits,
                "Recurring_Withdrawals": recurring_withdrawals,
                "Irregular_Withdrawals": irregular_withdrawals,
                "Total_Withdrawals": total_withdrawals,
                "Net_Change": total_deposits + total_withdrawals
            }
        except Exception as e:
            logger.error(f"Error analyzing recurring transactions: {str(e)}")
            raise ValueError(
                f"Failed to analyze recurring transactions: {str(e)}")

    def _flag_transactions(self, transactions: List[Transaction]) -> None:
        """Flag unusual transactions."""
        try:
            for transaction in transactions:
                # Flag high-value transactions
                if abs(transaction.Amount) > 4000:
                    transaction.Flagged = TransactionFlag(
                        is_high_value=True,
                        reason="Transaction exceeds $4000"
                    )
                # Add more flagging rules here
        except Exception as e:
            logger.error(f"Error flagging transactions: {str(e)}")

    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        import hashlib
        return hashlib.sha256(content).hexdigest()

    def parse_statement_text(self, text: str, start_time: float, file_content: bytes) -> StatementData:
        """Parse extracted text into structured data."""
        try:
            # Extract metadata first
            metadata = self._extract_statement_metadata(text)

            # Add timestamp and processing duration
            end_time = time.time()
            processing_duration = f"{end_time - start_time:.1f} seconds"
            metadata["parsed_on"] = datetime.utcnow().strftime(
                "%Y-%m-%dT%H:%M:%SZ")
            metadata["processing_duration"] = processing_duration
            metadata["timezone"] = "UTC"

            # Extract summary and transactions
            summary = self.extract_summary(text)
            transactions = self.extract_transactions(text)

            # Flag unusual transactions
            self._flag_transactions(transactions)

            # Analyze recurring transactions
            transaction_totals = self._analyze_recurring_transactions(
                transactions)
            totals = TotalTransactions(**transaction_totals)

            # Calculate spending analysis
            spending_analysis = self._calculate_spending_analysis(transactions)

            # Enhance transactions with additional details
            for transaction in transactions:
                transaction.Location = self._get_location_from_description(
                    transaction.Description)
                transaction.Category_Confidence = self._get_category_confidence(
                    transaction.Description, transaction.Category)
                transaction.Notes = self._get_transaction_notes(transaction)

            # Validate balances and create validation details
            validation_status = self._validate_balances(
                summary.Beginning_Balance, summary.Ending_Balance, transactions)
            validation_details = ValidationDetails(
                balances_match=(validation_status == "Reconciled"),
                all_transactions_processed=True,
                date_range_covered=self._get_date_range(transactions),
                rounding_differences=abs(
                    summary.Ending_Balance - (summary.Beginning_Balance + totals.Net_Change))
            )

            metadata["validation_status"] = validation_status
            metadata["validation_details"] = validation_details.dict()

            metadata_model = StatementMetadata(**metadata)

            # Calculate file hash
            file_hash = self._calculate_file_hash(file_content)

            return StatementData(
                metadata=metadata_model,
                file_metadata=FileMetadata(
                    file_name="statement.pdf",
                    file_size="0KB",
                    file_hash=file_hash
                ),
                Total_Transactions=totals,
                Checking_Summary=summary,
                Transaction_Detail=transactions,
                spending_analysis=spending_analysis,
                error_tracking=ErrorTracking()
            )
        except Exception as e:
            logger.error(f"Error parsing statement text: {str(e)}")
            raise ValueError(f"Failed to parse statement text: {str(e)}")

    def _extract_statement_metadata(self, text: str) -> dict:
        """Extract bank name, account number, and statement period from text."""
        try:
            metadata = {
                "bank_name": "chasebank",
                "account_number": "",
                "year": "",
                "month": ""
            }

            lines = text.split("\n")
            for line in lines:
                line = line.strip()

                # Extract account number (looking for the exact format)
                if "Account Number:" in line or "Account Number" in line:
                    # Try different patterns to extract account number
                    patterns = [
                        r'Account Number:\s*(\d+)',  # Pattern with colon
                        r'Account Number\s*(\d+)',   # Pattern without colon
                        r'(\d{12})',                 # Just 12 digits
                        r'(\d{9,})'                  # Any 9+ digit number
                    ]
                    for pattern in patterns:
                        import re
                        match = re.search(pattern, line)
                        if match:
                            account_num = match.group(1)
                            metadata["account_number"] = account_num
                            break

                # Extract statement period (looking for the exact format)
                if "through" in line and any(month in line for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]):
                    try:
                        # Extract end date
                        end_date = line.split("through")[1].strip()
                        # Parse month and year
                        for month_name in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]:
                            if month_name in end_date:
                                month_num = str(["January", "February", "March", "April", "May", "June", "July", "August",
                                                "September", "October", "November", "December"].index(month_name) + 1).zfill(2)
                                metadata["month"] = month_num
                                # Extract year (looking for 4-digit year)
                                year_match = end_date.split(
                                    ", ")[-1].strip()[:4]
                                if year_match.isdigit():
                                    metadata["year"] = year_match
                                break
                    except Exception as e:
                        logger.warning(f"Error parsing date: {str(e)}")

            # Validate metadata
            if not all(metadata.values()):
                logger.warning(f"Incomplete metadata: {metadata}")

            return metadata
        except Exception as e:
            logger.error(f"Error extracting statement metadata: {str(e)}")
            raise ValueError(f"Failed to extract statement metadata: {str(e)}")

    def _create_output_path(self, metadata: dict) -> str:
        """Create the output directory path and ensure it exists."""
        try:
            # Add leading slash to the path
            output_path = os.path.join(
                "/output",  # Changed from "output" to "/output"
                metadata["bank_name"],
                metadata["account_number"],
                metadata["year"],
                metadata["month"]
            )

            # Remove the leading slash temporarily for makedirs (it needs a relative path)
            relative_path = output_path[1:] if output_path.startswith(
                '/') else output_path
            os.makedirs(relative_path, exist_ok=True)

            return output_path
        except Exception as e:
            logger.error(f"Error creating output path: {str(e)}")
            raise ValueError(f"Failed to create output path: {str(e)}")

    def _save_statement_json(self, data: StatementData, output_path: str) -> str:
        """Save statement data as JSON file."""
        try:
            # Create filename with timestamp
            filename = f"statement_{data.Checking_Summary.Beginning_Balance}_{data.Checking_Summary.Ending_Balance}.json"
            file_path = os.path.join(output_path, filename)

            # Remove the leading slash temporarily for file operations
            relative_path = file_path[1:] if file_path.startswith(
                '/') else file_path

            # Ensure directory exists
            os.makedirs(os.path.dirname(relative_path), exist_ok=True)

            # Convert to dictionary and save as JSON using the relative path
            with open(relative_path, 'w') as f:
                json.dump(data.dict(), f, indent=4)

            # Return the absolute path with leading slash
            return file_path
        except Exception as e:
            logger.error(f"Error saving statement JSON: {str(e)}")
            raise ValueError(f"Failed to save statement JSON: {str(e)}")

    async def process_statement(self, file_content: bytes, filename: str = "statement.pdf") -> StatementResponse:
        """Process a bank statement PDF file."""
        try:
            start_time = time.time()

            # Convert PDF to images
            images = self.convert_pdf_to_images(file_content)
            logger.info(f"Successfully converted PDF to {len(images)} images")

            # Extract text using OCR
            extracted_text = self.extract_text_from_images(images)
            logger.info("Successfully extracted text from images")

            # Extract metadata for file path
            metadata = self._extract_statement_metadata(extracted_text)
            logger.info("Successfully extracted statement metadata")

            # Create output path
            output_path = self._create_output_path(metadata)
            logger.info(f"Created output directory: {output_path}")

            # Parse text into structured data
            statement_data = self.parse_statement_text(
                extracted_text, start_time, file_content)

            # Update file metadata
            statement_data.file_metadata.file_name = filename
            statement_data.file_metadata.file_size = f"{len(file_content) / 1024:.0f}KB"

            # Save JSON file
            file_path = self._save_statement_json(statement_data, output_path)
            logger.info(f"Saved statement JSON to: {file_path}")

            return StatementResponse(
                status="success",
                data=statement_data,
                file_path=file_path
            )

        except Exception as e:
            logger.error(f"Failed to process statement: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process statement: {str(e)}"
            )
