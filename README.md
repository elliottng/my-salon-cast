# MySalonCast

A web application for converting PDF documents and web links into engaging, conversational audio podcasts.

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## Project Structure

- `app/` - Main application code
- `services/` - Business logic and external service integrations
- `utils/` - Helper functions and utilities
- `temp_files/` - Temporary storage for uploaded files and generated content
- `tests/` - Test files

## Environment Variables

Create a `.env` file with the following variables:
```
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-file.json
```

## Development

The project uses FastAPI for the backend API and follows RESTful conventions.

## API Documentation

API documentation is automatically generated and available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
