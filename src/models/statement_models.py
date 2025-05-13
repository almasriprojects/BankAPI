from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class ValidationDetails(BaseModel):
    balances_match: bool
    all_transactions_processed: bool
    date_range_covered: str
    missing_transactions: List[str] = []
    rounding_differences: float = 0.0


class SessionMetadata(BaseModel):
    user_id: str = "user_12345"
    session_id: str = "session_67890"


class ErrorTracking(BaseModel):
    unprocessed_sections: List[str] = []
    parsing_errors: List[str] = []


class TransactionFlag(BaseModel):
    is_high_value: bool = False
    reason: str = ""


class Transaction(BaseModel):
    id: int
    Date: str
    Description: str
    Transaction_Type: str
    Category: str
    Amount: float
    Balance: float
    Category_Confidence: float = 0.0
    Location: str = ""
    Notes: str = ""
    Flagged: TransactionFlag = TransactionFlag()


class LargestTransaction(BaseModel):
    Description: str
    Amount: float
    Date: str


class SpendingAnalysis(BaseModel):
    total_spent_on_subscriptions: float
    largest_transaction: LargestTransaction
    average_daily_spending: float


class CheckingSummary(BaseModel):
    Beginning_Balance: float
    Deposits_and_Additions: float
    Electronic_Withdrawals: float
    Ending_Balance: float


class TotalTransactions(BaseModel):
    Total_Deposits: float
    Recurring_Deposits: float
    One_Off_Deposits: float
    Total_Withdrawals: float
    Recurring_Withdrawals: float
    Irregular_Withdrawals: float
    Net_Change: float


class FileMetadata(BaseModel):
    file_name: str
    file_size: str
    file_hash: str = ""


class StatementMetadata(BaseModel):
    bank_name: str
    account_number: str
    account_holder: str = "Anan Almasri"
    year: str
    month: str
    currency: str = "USD"
    parsed_by: str = "BankStatementParser v1.0"
    parsed_on: str
    processing_duration: str
    timezone: str = "UTC"
    validation_status: str
    validation_details: ValidationDetails
    session_metadata: SessionMetadata = SessionMetadata()


class StatementData(BaseModel):
    metadata: StatementMetadata
    file_metadata: FileMetadata
    Total_Transactions: TotalTransactions
    Checking_Summary: CheckingSummary
    Transaction_Detail: List[Transaction]
    spending_analysis: SpendingAnalysis
    error_tracking: ErrorTracking


class StatementResponse(BaseModel):
    status: str
    data: StatementData
    file_path: Optional[str] = None
