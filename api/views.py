import io
import re
import json
import requests
from PIL import Image
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status
from .utils import process_math_problem, extract_text_from_genai_response, classification_model, text_model
import logging

# Root: serve static/index.html if present, otherwise simple redirect-style HTML
@api_view(['GET'])
def root(request):
    try:
        with open('static/index.html', 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html')
    except FileNotFoundError:
        html = """
        <html>
            <head>
                <title>Math Bot & Message Classifier</title>
                <meta http-equiv="refresh" content="0; URL='/static/index.html'" />
            </head>
            <body>
                <p>Redirecting to <a href="/static/index.html">the application</a>...</p>
            </body>
        </html>
        """
        return HttpResponse(html, content_type='text/html')




# Latest function for only image or only text or both based math problems it will be used in the project
@csrf_exempt
@api_view(['POST'])
@parser_classes([JSONParser])
def solve_image_with_prompt(request):
    """
    Status:
    - 0 → AI provided the solution
    - 1 → Not a math question
    - 2 → Unable to provide the solution
    """
    import re
    from .utils import process_math_problem, process_math_problem_from_url

    data = request.data
    image_url = data.get('url')
    user_prompt = data.get('prompt')

    if not image_url and not user_prompt:
        return JsonResponse({"detail": "Provide an image URL or a text prompt."}, status=400)

    # Describe problem
    if image_url and user_prompt:
        problem_description = f"The following math problem is shown in the image from this URL: {image_url}. The user also provided this clarifying text: {user_prompt}."
    elif image_url:
        problem_description = f"The math problem is contained in the image from this URL: {image_url}."
    else:
        problem_description = f"The math problem text is: {user_prompt}"

    # 1️⃣ Check if input looks like math (user input), using symbols and numbers
    math_symbols = r'\d|[\+\-\*/=]|[A-Za-z]|[\^\∫√πΣ∆]'
    if not re.search(math_symbols, problem_description):
        return JsonResponse({"status": 1})

    # Mathematical solution prompt
    final_prompt = f"""
Analyze the language of the user's query below. Your entire response, including explanations, steps, and the final answer, MUST be in that same language.

TASK:
Extract and solve the math problem from the user's input (which could be from an image URL or text).

RESPONSE FORMAT (use literal markers on their own lines):
START_WORK
1.  **Step-by-Step Explanation**: Present your solution in a clear, step-by-step format. Use a bulleted list or a table to explain the transformation at each stage.
2.  **Final Answer**: Clearly state the final answer.
END_WORK

GUIDELINES:
- Use Delimiters: Always wrap LaTeX in 2$inline$ delimiters for expressions within a sentence; use $$...$$ for display equations.
- Show Your Work: Don't just provide the answer. Use a step-by-step table or bulleted list to explain the transformation at each stage.
- Avoid "Over-Latexing": Only apply LaTeX to mathematical notation; keep normal text plain.
- If the input is not a math problem, your ONLY response should be: **NOT_A_MATH_PROBLEM**

--- USER INPUT ---
{problem_description}
--- END USER INPUT ---
"""

    try:
        # Get AI output
        solution = process_math_problem_from_url(image_url, final_prompt) if image_url else process_math_problem(final_prompt)
        text = (solution or "").strip().upper()

        # 2️⃣ Explicit AI response check for non-math
        if "NOT_A_MATH_PROBLEM" in text:
            return JsonResponse({"status": 1})

        # 3️⃣ If AI could not provide a usable response → status 2
        if not text:
            return JsonResponse({"status": 2, "message": "I am unable to provide the solution."})

        # 4️⃣ AI successfully provided a solution → prefer content between delimiters
        start_delimiter = "START_WORK"
        end_delimiter = "END_WORK"

        start_index = solution.find(start_delimiter)
        end_index = solution.find(end_delimiter)

        if start_index != -1 and end_index != -1 and end_index > start_index:
            content_start = start_index + len(start_delimiter)
            solution_content = solution[content_start:end_index].strip()
        else:
            solution_content = solution.strip()

        # Normalize numbering to start from 1 and drop stray END markers
        def _normalize_numbering(text: str) -> str:
            lines = text.splitlines()
            idxs, nums = [], []
            for i, ln in enumerate(lines):
                m = re.match(r"^\s*(\d+)\.\s", ln)
                if m:
                    idxs.append(i)
                    nums.append(int(m.group(1)))
            if idxs:
                offset = nums[0] - 1
                if offset > 0:
                    for i, idx in enumerate(idxs):
                        new_num = nums[i] - offset
                        lines[idx] = re.sub(r"^\s*\d+\.", f"{new_num}.", lines[idx], count=1)
            # Remove explicit END markers if leaked into content
            lines = [ln for ln in lines if not re.search(r"\bEND_WORK\b", ln)]
            # Remove lines that are just a number with no content
            lines = [ln for ln in lines if not re.match(r"^\s*\d+\.\s*$", ln)]
            return "\n".join(lines).strip()

        solution_content = _normalize_numbering(solution_content)

        # Final safety: if still empty, mark as unable
        if not solution_content:
            return JsonResponse({"status": 2, "message": "I am unable to provide the solution."})

        return JsonResponse({"status": 0, "solution": solution_content})

    except Exception:
        return JsonResponse({"status": 2, "message": "I am unable to provide the solution."})




# Latest function for checking the solution provided by the user in the project
@csrf_exempt
@api_view(['POST'])
@parser_classes([JSONParser, FormParser])
def check_solution(request):
    from .utils import process_math_problem_from_url, process_math_problem

    problem_text = request.data.get('problem_text')
    solution_text = request.data.get('solution_text')
    problem_url = request.data.get('problem_url')
    solution_url = request.data.get('solution_url')

    if (not problem_text or not str(problem_text).strip()) and not problem_url:
        return JsonResponse({"detail": "Provide the problem as text or an image URL."}, status=400)
    if (not solution_text or not str(solution_text).strip()) and not solution_url:
        return JsonResponse({"detail": "Provide the solution as text or an image URL."}, status=400)

    try:
        # -----------------------------
        # 1) Canonical correct solution
        # -----------------------------
        problem_prompt = "Solve the following math problem. Provide only the final answer in its simplest form.\nUse LaTeX formatting if appropriate. Do not include any explanations or steps.\n\n"
        if problem_text and str(problem_text).strip():
            problem_prompt += f"Problem (text): {str(problem_text).strip()}\n\n"
        problem_prompt += "Final answer only:"

        if problem_url:
            correct_solution = process_math_problem_from_url(problem_url, problem_prompt)
        else:
            correct_solution = process_math_problem(problem_prompt)
        correct_solution = (correct_solution or "").strip()

        # -----------------------------
        # 2) Compare user's solution
        # -----------------------------
        check_prompt_base = f"""
Extract the final answer from the provided solution (either text or image). Then compare it with the correct answer: {correct_solution}

Return ONLY a single word: CORRECT (if the answers match, considering equivalent formats like fractions vs decimals) or INCORRECT (if they don't match).
If you cannot determine, return INCORRECT.
Do not include any explanations.
"""
        if solution_text and str(solution_text).strip():
            check_prompt_base = f"Solution (text): {str(solution_text).strip()}\n\n" + check_prompt_base

        if solution_url:
            raw_result = process_math_problem_from_url(solution_url, check_prompt_base)
        else:
            raw_result = process_math_problem(check_prompt_base)
        raw_result = (raw_result or "").strip()

        m = re.search(r'\b(CORRECT|INCORRECT)\b', raw_result, re.IGNORECASE)
        if m:
            verdict = m.group(1).upper()
            comparison = 0 if verdict == "CORRECT" else 1
        else:
            comparison = 1

        # -----------------------------
        # 3) Extract final answer from user's solution
        # -----------------------------
        extract_prompt = """
Extract the final answer from the provided solution. Return only the answer (use LaTeX if appropriate).
If you cannot determine the final answer, return "UNCLEAR".
"""
        if solution_text and str(solution_text).strip():
            extract_prompt = f"Solution (text): {str(solution_text).strip()}\n\n" + extract_prompt

        if solution_url:
            extracted_raw = process_math_problem_from_url(solution_url, extract_prompt)
        else:
            extracted_raw = process_math_problem(extract_prompt)

        extracted_solution = (extracted_raw or "").strip()

        return JsonResponse({
            "status": comparison,
            "correct_solution": correct_solution,
            "extracted_solution": extracted_solution,
            "raw_result": raw_result,
            "inputs": {
                "problem_text_provided": bool(problem_text and str(problem_text).strip()),
                "problem_url_provided": bool(problem_url),
                "solution_text_provided": bool(solution_text and str(solution_text).strip()),
                "solution_url_provided": bool(solution_url),
            }
        })
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)



MAX_QUESTIONS = 20
# This function will generate math questions based on grade and subject provided by the user in the project.
@csrf_exempt
@api_view(['POST'])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def generate_math_question(request):
    grade = request.data.get('grade')
    subject = request.data.get('subject')
    count = request.data.get('count', 1)

    if not grade or not subject:
        return JsonResponse({"detail": "Fields 'grade' and 'subject' are required."}, status=400)

    try:
        if isinstance(count, str):
            try:
                count = int(count)
            except (ValueError, TypeError):
                count = 1
        elif not isinstance(count, int):
            count = 1
            
        if count < 1:
            count = 1
        if count > MAX_QUESTIONS:
            count = MAX_QUESTIONS

        questions = []
        try:
            json_prompt = f"""
You are a math teacher. Generate {count} unique math questions for a student in grade {grade}
on the topic of {subject}. Each question should be age-appropriate, clear, and solvable.

Return **only** valid JSON. The JSON must be an array of objects with exactly these keys:
[
  {{
    "question": "question text here",
    "answer": "answer text here"
  }},
  ...
]

Do NOT include any additional text outside the JSON array. Make sure there are exactly {count} objects.
"""
            response = text_model.generate_content(json_prompt)
            text = getattr(response, "text", "").strip() or str(response)

            m = re.search(r'(\[.*\])', text, re.DOTALL)
            if m:
                try:
                    arr = json.loads(m.group(1))
                    for item in arr:
                        q = item.get("question") if isinstance(item, dict) else None
                        a = item.get("answer") if isinstance(item, dict) else None
                        if q and a:
                            questions.append({"question": q.strip(), "answer": a.strip()})
                except Exception:
                    pass

            if len(questions) < count:
                qa_pairs = re.findall(
                    r"(?:Question\s*\d*[:：]\s*)(.*?)(?:\r?\n\s*Answer\s*\d*[:：]\s*)(.*?)(?=(?:\r?\n\s*Question\s*\d*[:：])|$)",
                    text,
                    re.DOTALL | re.IGNORECASE
                )
                for q, a in qa_pairs:
                    if len(questions) >= count:
                        break
                    questions.append({"question": q.strip(), "answer": a.strip()})

            attempt = 0
            while len(questions) < count and attempt < (count * 2):
                attempt += 1
                single_prompt = f"""
Generate 1 unique math question for grade {grade} on the topic {subject}.
Return as:
Question: ...
Answer: ...
Do not repeat previous questions.
"""
                resp = text_model.generate_content(single_prompt)
                text_single = getattr(resp, "text", "").strip() or str(resp)
                m2 = re.search(r"Question\s*\d*[:：]\s*(.*?)(?:\r?\n\s*Answer\s*\d*[:：]\s*(.*))?$",
                               text_single, re.DOTALL | re.IGNORECASE)
                if m2:
                    q = (m2.group(1) or "").strip()
                    a = (m2.group(2) or "").strip()
                    if q and a and not any(q == e["question"] for e in questions):
                        questions.append({"question": q, "answer": a})
                        continue
                lines = [ln.strip() for ln in text_single.splitlines() if ln.strip()]
                if len(lines) >= 2:
                    q = lines[0]
                    a = lines[1]
                    if not any(q == e["question"] for e in questions):
                        questions.append({"question": q, "answer": a})
        except Exception as e:
            logging.error(f"Error generating questions from AI model: {str(e)}")
            # Fallback when the AI model fails
            pass


        while len(questions) < count:
            questions.append({"question": "Unable to generate question — please retry.", "answer": ""})

        result = []
        for i in range(count):
            qitem = questions[i]
            result.append({
                "number": i + 1,
                "question": qitem["question"],
                "answer": qitem["answer"]
            })

        return JsonResponse({
            "grade": grade,
            "subject": subject,
            "count": count,
            "questions": result
        })
    except Exception as e:
        return JsonResponse({"detail": f"Error generating questions: {str(e)}"}, status=500)

# This function will classify the message provided by the user in the project.
@csrf_exempt
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def classify_message(request):
    message = request.data.get('message')
    if not message or not str(message).strip():
        return JsonResponse({"detail": "Field 'message' is required."}, status=400)

    classification_prompt = f"""
Analyze the following message and classify it. Return only a single digit (0 or 1) with no additional text.

Return 1 if the message contains any of the following:
- Bullying or harassment
- Slang or inappropriate language
- Dangerous links (malware, viruses, etc.)
- Phishing attempts
- Any other harmful content

Return 0 if the message is normal, safe conversation.

Message: {message}

Classification:
"""
    try:
        response = classification_model.generate_content(classification_prompt)
        raw = extract_text_from_genai_response(response).strip()

        m = re.search(r'(?<!\d)([01])(?!\d)', raw)
        if m:
            classification = int(m.group(1))
            return JsonResponse({"message": message, "classification": classification})

        raw_lower = raw.lower()
        if "one" in raw_lower and "zero" not in raw_lower:
            return JsonResponse({"message": message, "classification": 1})
        if "zero" in raw_lower and "one" not in raw_lower:
            return JsonResponse({"message": message, "classification": 0})

        return JsonResponse({"message": message, "classification": 0})
    except Exception as e:
        return JsonResponse({"detail": f"Error classifying message: {str(e)}"}, status=500)