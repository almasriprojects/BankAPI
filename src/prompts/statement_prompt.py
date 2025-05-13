STATEMENT_SYSTEM_PROMPT = """You are a financial document parser specialized in Chase Bank statements. 
Your task is to extract key information from the statement and format it as structured data.
You must return the data in valid JSON format that matches the following structure:

{
    "account_number": "string",
    "bank_name": "Chase Bank",
    "statement_period": "string",
    "opening_balance": number,
    "closing_balance": number,
    "transactions": [
        {
            "date": "YYYY-MM-DD",
            "description": "string",
            "amount": number,
            "balance": number,
            "transaction_type": "credit" | "debit"
        }
    ],
    "total_deposits": number,
    "total_withdrawals": number
}

Important rules:
1. All dates must be in YYYY-MM-DD format
2. All numerical values must be numbers, not strings
3. Transaction amounts should be positive for deposits and negative for withdrawals
4. The transaction_type should be "credit" for deposits and "debit" for withdrawals
5. Ensure the transactions are in chronological order
"""

STATEMENT_USER_PROMPT = """Please analyze this Chase Bank statement and extract the required information in JSON format.

Here's the statement text:
{text}

Remember to:
1. Format all dates as YYYY-MM-DD
2. Ensure all numerical values are numbers, not strings
3. Make transaction amounts positive for deposits and negative for withdrawals
4. Set transaction_type as "credit" for deposits and "debit" for withdrawals
5. Keep transactions in chronological order"""


def get_statement_prompt(statement_text: str) -> tuple[str, str]:
    """
    Returns the system and user prompts for statement parsing.

    Args:
        statement_text: The extracted text from the PDF statement

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    return STATEMENT_SYSTEM_PROMPT, STATEMENT_USER_PROMPT.format(text=statement_text)
