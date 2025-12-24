# Math Bot & Message Classifier — Django REST

This is a Django REST Framework port of your FastAPI app. All routes and features are preserved.

## Quickstart

1. **Create a virtualenv** (recommended) and activate it.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment**:
   - Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
4. **Run the server**:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
5. **Open**: http://localhost:8000/

## Endpoints

- `GET /` — serves `static/index.html`
- `POST /solve/text` — `problem` (form field)
- `POST /solve/image` — `file` (image upload)
- `POST /solve/image-with-prompt` — optional `file` and/or `prompt`
- `POST /solve/url` — `url` to an image
- `POST /check-solution` — `problem_text`/`problem_file` and `solution_text`/`solution_file`
- `POST /classify` — `message`
- `POST /generate-question` — `grade`, `subject`, optional `count`

## Notes

- CORS is allowed for all origins (development).
- Static files are served from `/static/` during development (DEBUG=True).
