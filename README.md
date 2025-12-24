# AI Global Math Bot & Message Classifier

This project is a Django REST Framework application that provides a suite of AI-powered tools for mathematical tasks. It can solve math problems from images or text, verify solutions, classify messages, and generate new math questions. It leverages the power of Google's Gemini model for its AI capabilities.

## ✨ Features

-   **Solve Math Problems**: Submit a math problem as an image, a URL to an image, or plain text and get a step-by-step solution.
-   **Check Solutions**: Provide a problem and a solution, and the AI will verify if the solution is correct.
-   **Classify Messages**: Determine the category or intent of a given text message.
-   **Generate Questions**: Create new math questions tailored to a specific grade level and subject.
-   **Simple Web Interface**: A basic HTML frontend to interact with the API.
-   **RESTful API**: A well-defined API for programmatic access.

## 🛠️ Technology Stack

-   **Backend**: Python, Django, Django REST Framework
-   **AI**: Google Gemini API
-   **Database**: SQLite (default for development)
-   **Frontend**: HTML, CSS, JavaScript (for the demo page)

## 🚀 Quickstart

Follow these steps to get the project running on your local machine.

### 1. Prerequisites

-   Python 3.8+
-   `pip` and `virtualenv`

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd AI_Global_Math_Judebeale_Project
```

### 3. Set Up a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

```bash
# For Windows
python -m venv venv
.\venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

-   Copy the example environment file `.env.example` to a new file named `.env`.
-   Open `.env` and add your Google Gemini API key.

```ini
# .env
GEMINI_API_KEY="your_gemini_api_key_here"
```

### 6. Run Database Migrations

Apply the initial database schema.

```bash
python manage.py migrate
```

### 7. Run the Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

### 8. Open the Application

Navigate to **http://localhost:8000/** in your web browser to see the application's frontend.

## 🔌 API Endpoints

All endpoints are relative to the base URL (e.g., `http://localhost:8000`).

---

### `GET /`

-   **Description**: Serves the static `index.html` file, which provides a simple UI for interacting with the API.

---

### `POST /solve/image-with-prompt`

-   **Description**: Solves a math problem from an uploaded image file and/or a text prompt.
-   **Content-Type**: `multipart/form-data`
-   **Parameters**:
    -   `file` (file, optional): An image file containing the math problem.
    -   `prompt` (string, optional): A text-based math problem or additional context.
-   **Example `curl`**:
    ```bash
    curl -X POST -F "file=@/path/to/your/image.png" -F "prompt=Solve for x" http://localhost:8000/solve/image-with-prompt
    ```

---

### `POST /solve/url`

-   **Description**: Solves a math problem from an image URL.
-   **Content-Type**: `application/json`
-   **Parameters**:
    -   `url` (string, required): The public URL of an image containing the math problem.
-   **Example `curl`**:
    ```bash
    curl -X POST -H "Content-Type: application/json" -d '{"url": "http://example.com/problem.jpg"}' http://localhost:8000/solve/url
    ```

---

### `POST /check-solution`

-   **Description**: Verifies if a given solution is correct for a given problem.
-   **Content-Type**: `multipart/form-data`
-   **Parameters**:
    -   `problem_text` / `problem_file` (string/file, required): The problem statement.
    -   `solution_text` / `solution_file` (string/file, required): The proposed solution.
-   **Example `curl`**:
    ```bash
    curl -X POST -F "problem_text=What is 2+2?" -F "solution_text=It is 4." http://localhost:8000/check-solution
    ```

---

### `POST /classify`

-   **Description**: Classifies a given text message.
-   **Content-Type**: `application/json`
-   **Parameters**:
    -   `message` (string, required): The text message to classify.
-   **Example `curl`**:
    ```bash
    curl -X POST -H "Content-Type: application/json" -d '{"message": "Can you help me with my algebra homework?"}' http://localhost:8000/classify
    ```

---

### `POST /generate-question`

-   **Description**: Generates one or more math questions.
-   **Content-Type**: `application/json`
-   **Parameters**:
    -   `grade` (string, required): The grade level (e.g., "8th Grade").
    -   `subject` (string, required): The subject (e.g., "Algebra").
    -   `count` (integer, optional, default: 1): The number of questions to generate.
-   **Example `curl`**:
    ```bash
    curl -X POST -H "Content-Type: application/json" -d '{"grade": "10th Grade", "subject": "Geometry", "count": 3}' http://localhost:8000/generate-question
    ```

## ⚙️ Configuration

-   **CORS**: In development mode (`DEBUG=True`), Cross-Origin Resource Sharing (CORS) is enabled for all origins for easier testing. For production, you should restrict this to your frontend's domain.
-   **Static Files**: Static files are served automatically from the `/static/` directory when `DEBUG=True`.