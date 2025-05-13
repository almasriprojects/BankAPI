# Chase Bank Statement Parser

A FastAPI service that processes Chase Bank statements (PDF) using OpenAI, converting them into structured JSON data.

## Features

- PDF statement upload endpoint
- OpenAI-powered document parsing
- Structured JSON output
- Organized file storage system

## Project Structure

```
chase_statement_parser/
├── src/
│   ├── main.py
│   ├── prompts/
│   ├── routes/
│   ├── services/
│   ├── utils/
│   └── models/
├── output/
│   └── [bankname]/[accountnumber]/[year]/[month]/
├── requirements.txt
├── Dockerfile
├── README.md
├── pyproject.toml
├── .dockerignore
└── .gitignore
```

## Setup

### Environment Variables

Create a `.env` file with:

```env
OPENAI_API_KEY=your_api_key_here
```

### Docker Deployment (Recommended)

1. Build the image:
   ```bash
   docker build -t chase-statement-parser .
   ```

2. Run the container:
   ```bash
   docker run -p 8086:8086 -e OPENAI_API_KEY=your_api_key_here chase-statement-parser
   ```

The API will be available at http://localhost:8086

### API Usage

### Upload Statement

```bash
curl -X POST "http://localhost:8086/upload-statement" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@statement.pdf"
```

The API will:
1. Process the PDF
2. Extract information using OpenAI
3. Return and save the structured JSON data

## Output

The processed statements are saved in the following structure:
```
output/
└── ChaseBank/
    └── [account_number]/
        └── [year]/
            └── [month]/
                └── statement.json
``` 