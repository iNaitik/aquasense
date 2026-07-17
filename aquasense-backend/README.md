# AQUA-SENSE Backend

FastAPI backend for the AQUA-SENSE citizen water-complaint system.

## Quick Start

### 1. Create a Python virtual environment

```bash
cd aquasense-backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the PostgreSQL database

Make sure PostgreSQL is running, then:

```sql
CREATE DATABASE aquasense;
```

Or from the command line:

```bash
createdb aquasense
```

### 4. Configure environment variables

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
```

Edit `.env` and set your actual PostgreSQL credentials:

```dotenv
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/aquasense
FRONTEND_ORIGIN=http://localhost:5173
```

### 5. Run Alembic migrations

Generate the initial migration (first time only):

```bash
alembic revision --autogenerate -m "create complaints table"
```

Apply migrations:

```bash
alembic upgrade head
```

### 6. Start the FastAPI server

```bash
uvicorn app.main:app --reload --port 8000
```

### 7. Access Swagger docs

Open your browser and visit:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health check**: [http://localhost:8000/health](http://localhost:8000/health)

## API Endpoints

| Method | Path                              | Description             |
| ------ | --------------------------------- | ----------------------- |
| GET    | `/health`                         | Health check            |
| POST   | `/api/v1/complaints`              | Submit a new complaint  |
| GET    | `/api/v1/complaints/{reference_id}` | Track complaint status |

## Project Structure

```
aquasense-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, routers
│   ├── database.py           # SQLAlchemy engine & session
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py         # Pydantic-settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── complaint.py      # ORM model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── complaint.py      # Pydantic request/response schemas
│   ├── routes/
│   │   ├── __init__.py
│   │   └── complaints.py     # API endpoints
│   └── services/
│       ├── __init__.py
│       └── complaint_service.py  # Business logic
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
