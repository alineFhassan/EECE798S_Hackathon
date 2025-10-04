from flask import Flask, request, jsonify
import PyPDF2
import io
import openai
import json
from openai import OpenAI
import requests 
app = Flask(__name__)
import os
from graph_extraction_chain import extract_graph_from_text
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file."""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def format_cv_with_gpt4(cv_text):
    """Send CV text to GPT-4 for formatting."""
    prompt = f"""Extract the following details from this CV (if available) and return in a structured JSON format:
    - Education (degree, school, GPA)
    - Skills  (for the skills please list them only without putting them as sub types or putting true beside the skill if it presents. Please just listing)
    - Experience (Role, Company, Years of experience (count of years taking into consideration that we are now in 2025), key responsibilities)
    - Projects (only list them)
    - Certifications (only list the name and the issuer if available)
    
    CV Content:
    {cv_text}
    
    Return only valid JSON without any additional text or explanation.
    The JSON structure should be like this and in the below same order please:
    {{
        "candidate name": [
            {{
                ""
            }}
        ]
        "education": [
            {{
                "degree": "",
                "school": "",
                "gpa": "",
            }}
        ],
        "skills": {{

        }},
        "experience": [
            {{
                "role": "",
                "company": "",
                "years": "",
                "responsibilities": []
            }}
        ],
        "projects":  [
            {{

            }}
       ] ,
        "certifications": [
            {{
            }}
        ]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts information from CVs and returns structured JSON data."},
            {"role": "user", "content": prompt}
        ],
    )
 
    # Extract the JSON content from the response
    json_str = response.choices[0].message.content
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        json_str = json_str[json_str.find('{'):json_str.rfind('}')+1]
        return json.loads(json_str)

@app.route('/extract-cv', methods=['POST'])
def extract_cv():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    pdf_file = request.files['file']
    if pdf_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        # Extract text from PDF
        cv_text = extract_text_from_pdf(pdf_file)
        
        # Format with GPT-4
        formatted_cv = format_cv_with_gpt4(cv_text)
        graph = extract_graph_from_text(formatted_cv, kind="cv")
        return jsonify({
            "status": "success",
            "cv_data": formatted_cv,    
            "cv_graph": graph
        })
    
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=True)