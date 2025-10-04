from flask import Flask, request, jsonify
import os
import json
import requests
import numpy as np
from datetime import datetime

import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

import mysql.connector  # instead of psycopg2
import os

DB_HOST = os.getenv('DB_HOST', 'db')  # 'db' matches the service name in docker-compose.yml
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'Hackathon')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')

def get_db_connection():
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn


@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        date_of_birth = data.get('date')  # Frontend sends 'date' but schema expects 'date_of_birth'
        password = data.get('password')
        user_type = data.get('user_type', 'applicant')  # Default to 'applicant' if not provided

        # Validate required fields
        if not all([first_name, last_name, email, phone_number, date_of_birth, password]):
            return jsonify({"status": "error", "message": "All fields are required."}), 400

        # Hash the password (use a secure hashing method)
        # For example, using bcrypt:
        # hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email already registered."}), 409

        # Insert the new user
        cursor.execute("""
            INSERT INTO users (first_name, last_name, email, password, date_of_birth, phone_number, user_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (first_name, last_name, email, password, date_of_birth, phone_number, user_type))  # Use hashed_password here

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "User registered successfully."}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# login route
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')  # In production, compare hashed passwords
        register_option = data.get('register_option')  # This is the user_type from the frontend

        if not email or not password or not register_option:
            return jsonify({"status": "error", "message": "All fields are required."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check different tables based on register_option
        if register_option == 'company':
            # Check in departments table
            cursor.execute("""
                SELECT id, email, name FROM departments 
                WHERE email = %s AND password = %s;
            """, (email, password))
            
            user = cursor.fetchone()
            
            if user:
                cursor.close()
                conn.close()
                return jsonify({
                    "status": "success",
                    "user_id": user[0],
                    "register_option": "company"
                }), 200
        else:
            # Check in users table
            cursor.execute("""
                SELECT id, email, user_type FROM users 
                WHERE email = %s AND password = %s;
            """, (email, password))
            
            user = cursor.fetchone()
            
            if user:
                cursor.close()
                conn.close()
                return jsonify({
                    "status": "success",
                    "user_id": user[0],
                    "register_option": user[2]  # Return user_type as register_option
                }), 200

        # If we get here, no user was found
        cursor.close()
        conn.close()
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    


@app.route('/check_db', methods=['GET'])
def check_db():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "success", "message": "Database connection successful!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, full_name, username, email, user_type FROM users;")
        users = cursor.fetchall()

        # Format the result as a list of dictionaries
        users_list = []
        for user in users:
            users_list.append({
                "id": user[0],
                "full_name": user[1],
                "username": user[2],
                "email": user[3],
                "user_type": user[4]
            })

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "users": users_list}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
 
    

@app.route('/add_applicant', methods=['POST'])
def add_application():
    try:
        data = request.json
        cv_data = data.get('cv_data', {})
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"status": "error", "message": "User ID is required."}), 400

        # Extract fields from cv_data
        education = json.dumps(cv_data.get('education', []))
        skills = json.dumps(cv_data.get('skills', []))
        experience = json.dumps(cv_data.get('experience', []))
        projects = json.dumps(cv_data.get('projects', []))
        certifications = json.dumps(cv_data.get('certifications', []))
        experience_years = sum(
            float(exp['years']) 
            for exp in cv_data.get('experience', []) 
            if isinstance(exp.get('years'), (int, float)) or (isinstance(exp.get('years'), str) and exp['years'].replace('.', '', 1).isdigit())
        )
        print("years", experience_years)

        cv_graph = data.get('graph', {})
        # Database insertion
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user already has a CV
        cursor.execute("SELECT id FROM applicant_cv WHERE user_id = %s", (user_id,))
        existing_cv = cursor.fetchone()

        if existing_cv:
            # Update existing CV
            cursor.execute("""
                UPDATE applicant_cv 
                SET education = %s, skills = %s, experience = %s, 
                    experience_years = %s, projects = %s, certifications = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s, cv_graph = %s;
            """, (
                education, skills, experience, experience_years, 
                projects, certifications, user_id, cv_graph
            ))
            message = "CV updated successfully."
        else:
            # Insert new CV
            cursor.execute("""
                INSERT INTO applicant_cv (
                    user_id, education, skills, experience, 
                    experience_years, projects, certifications
                ) VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                user_id, education, skills, experience, 
                experience_years, projects, certifications
            ))
            message = "CV added successfully."

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": message}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_applicant/<int:user_id>', methods=['GET'])
def get_applicant_cv(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get CV data for the specific user
        cursor.execute("""
            SELECT id, education, skills, experience, 
                   experience_years, projects, certifications,
                   created_at, updated_at
            FROM applicant_cv
            WHERE user_id = %s;
        """, (user_id,))
        
        cv = cursor.fetchone()
        
        if not cv:
            return jsonify({"status": "error", "message": "CV not found"}), 404
            
        # Format the result as a dictionary that matches the frontend's expected format
        cv_data = {
            "education": json.loads(cv[1]) if cv[1] else [],
            "skills": json.loads(cv[2]) if cv[2] else [],
            "experience": json.loads(cv[3]) if cv[3] else [],
            "experience_years":cv[4],
            "projects": json.loads(cv[5]) if cv[5] else [],
            "certifications": json.loads(cv[6]) if cv[6] else []
        }

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "cv_data": cv_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user data
        cursor.execute("""
            SELECT id, first_name, last_name, email, 
                   phone_number, date_of_birth
            FROM users
            WHERE id = %s;
        """, (user_id,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
            
        # Format the result as a dictionary
        user_data = {
            "id": user[0],
            "first_name": user[1],
            "last_name": user[2],
            "email": user[3],
            "phone_number": user[4],
            "date_of_birth": user[5].isoformat() if user[5] else None
        }

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "user": user_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_offered_job', methods=['GET'])
def get_offered_jobs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT j.id, j.title, j.job_level, j.years_experience, 
                   j.requirements, j.responsibilities, j.required_certifications,
                   j.status, j.date_offered, j.created_at, j.department_id,
                   d.name as department_name
            FROM jobs j
            JOIN departments d ON j.department_id = d.id
            ORDER BY j.created_at DESC;
        """)
        
        jobs = []
        for job in cursor.fetchall():
            jobs.append({
                "id": job[0],  # Changed to uppercase to match frontend
                "job_title": job[1],
                "job_level": job[2],
                "years_experience": job[3],
                "requirements": json.loads(job[4]) if job[4] else [],
                "responsibilities": json.loads(job[5]) if job[5] else [],
                "required_certifications": json.loads(job[6]) if job[6] else [],
                "status": job[7],
                "date_offered": job[8].isoformat() if job[8] else None,
                "created_at": job[9].isoformat() if job[9] else None,
                "dept_id": job[10],
                "department_name": job[11],
                "job_graph": job[12]  # Already included from the join
            })

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "jobs": jobs}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/add_offer_job', methods=['POST'])
def add_offer_job():
    try:
        data = request.json
        
        # Validation
        if 'department_id' not in data or 'job_description' not in data:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        job_desc = data['job_description']

        required_fields = ['job_title', 'job_level', 'years_experience']
        if not all(field in job_desc for field in required_fields):
            missing = [f for f in required_fields if f not in job_desc]
            return jsonify({"status": "error", "message": f"Missing fields in job_description: {missing}"}), 400

        # Prepare data for insertion
        insert_data = {
            'department_id': data['department_id'],
            'title': job_desc['job_title'],
            'job_level': job_desc['job_level'],
            'years_experience': job_desc['years_experience'],
            'requirements': json.dumps(job_desc.get('requirements', [])),
            'responsibilities': json.dumps(job_desc.get('responsibilities', [])),
            'required_certifications': json.dumps(job_desc.get('required_certifications', [])),
            'status': job_desc.get('status', 'open'),
            'date_offered': datetime.now()
        }
        
        logging.debug(f"💾 Prepared insert data: {insert_data}")
        job_graph = data.get('graph', {})
        conn = get_db_connection()
        cursor = conn.cursor()

        # Modified INSERT query for MySQL
        cursor.execute("""
            INSERT INTO jobs (
                department_id, title, job_level, years_experience,
                requirements, responsibilities, required_certifications,
                status, date_offered, job_graph
            ) VALUES (%(department_id)s, %(title)s, %(job_level)s, %(years_experience)s,
                      %(requirements)s, %(responsibilities)s, %(required_certifications)s,
                      %(status)s, %(date_offered)s, %(job_graph)s)
        """, insert_data)

        # Get the last inserted ID for MySQL
        job_id = cursor.lastrowid
        conn.commit()

        return jsonify({
            "status": "success",
            "job_id": job_id,
            "message": "Job posted successfully"
        }), 201

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e),
            "type": type(e).__name__
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@app.route('/get_applicants/<int:job_id>', methods=['GET'])
def get_applicants(job_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # First check if the job exists
        cursor.execute("""
            SELECT id, department_id, title, job_level, years_experience
            FROM jobs
            WHERE id = %s
        """, (job_id,))
        
        job = cursor.fetchone()
        if not job:
            return jsonify({"status": "error", "message": "Job not found"}), 404

        # Get all applicants who applied for this job
        cursor.execute("""
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                u.email,
                u.phone_number,
                ac.experience_years,
                ac.skills,
                ac.experience,
                ac.education,
                aj.scores,
                aj.status
            FROM applied_jobs aj
            JOIN users u ON aj.applicant_id = u.id
            LEFT JOIN applicant_cv ac ON u.id = ac.user_id
            WHERE aj.job_id = %s
            ORDER BY ac.experience_years DESC
        """, (job_id,))
        
        applicants = []
        for row in cursor.fetchall():
            # Parse JSON fields
            skills = json.loads(row[6]) if row[6] else []
            experience = json.loads(row[7]) if row[7] else []
            education = json.loads(row[8]) if row[8] else {}
            scores = json.loads(row[9]) if row[9] else {}
            status= row[10]
            applicant = {
                "id": row[0],
                "name": f"{row[1]} {row[2]}",
                "email": row[3],
                "phone_number": row[4],
                "exp_years": row[5] or 0,
                "skills": skills,
                "experience": experience,
                "education": education,
                "match_score": scores,
                "status": status
            }
            applicants.append(applicant)

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success", 
            "job_id": job_id,
            "applications": applicants
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/get_applicants', methods=['GET'])
def get_all_applicants():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                u.email,
                u.phone_number,
                ac.experience_years,
                ac.skills,
                ac.experience,
                ac.education,
                aj.scores,
                aj.status,
                aj.job_id
            FROM applied_jobs aj
            JOIN users u ON aj.applicant_id = u.id
            LEFT JOIN applicant_cv ac ON u.id = ac.user_id
            ORDER BY aj.job_id, ac.experience_years DESC
        """)

        applicants = []
        for row in cursor.fetchall():
            skills = json.loads(row[6]) if row[6] else []
            experience = json.loads(row[7]) if row[7] else []
            education = json.loads(row[8]) if row[8] else {}
            scores = json.loads(row[9]) if row[9] else {}
            status = row[10]
            job_id = row[11]
            applicant_graph = row[12]
            applicants.append({
                "id": row[0],
                "name": f"{row[1]} {row[2]}",
                "email": row[3],
                "phone_number": row[4],
                "exp_years": row[5] or 0,
                "skills": skills,
                "experience": experience,
                "education": education,
                "match_score": scores,
                "status": status,
                "job_id": job_id,
                "cv_graph": applicant_graph
            })

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "applications": applicants
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@app.route('/get_applied_job/<int:job_id>', methods=['GET'])
def get_applied_job(job_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # First check if the job exists
        cursor.execute("""
            SELECT id FROM jobs
            WHERE id = %s
        """, (job_id,))
        
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Job not found"}), 404

        # Get all applications for this job
        cursor.execute("""
            SELECT 
                aj.id,
                aj.applicant_id,
                aj.status,
                aj.scores,
                aj.thresholds,
                aj.meets_threshold,
                aj.passed_criteria,
                aj.qualified_cv,
                aj.reason,
                aj.created_at
            FROM applied_jobs aj
            WHERE aj.job_id = %s
            ORDER BY aj.created_at DESC
        """, (job_id,))
        
        applications = []
        for row in cursor.fetchall():
            # Parse JSON fields
            scores = json.loads(row[3]) if row[3] else {}
            thresholds = json.loads(row[4]) if row[4] else {}
            meets_threshold = json.loads(row[5]) if row[5] else {}
            
            application = {
                "id": row[0],
                "applicant_id": row[1],
                "status": row[2],
                "scores": scores,
                "thresholds": thresholds,
                "meets_threshold": meets_threshold,
                "passed_criteria": row[6],
                "qualified_cv": row[7],
                "reason": row[8],
                "created_at": row[9].isoformat() if row[9] else None
            }
            applications.append(application)

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success", 
            "job_id": job_id,
            "applications": applications
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/update_interview/<int:meeting_id>', methods=['PUT'])
def update_interview(meeting_id):
    try:
        data = request.json
        required_fields = ['meeting_title', 'meeting_date', 'start_time', 'end_time']
        
        # Validate required fields
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if interview exists
        cursor.execute("""
            SELECT id FROM interviews 
            WHERE id = %s
        """, (meeting_id,))
        
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Interview not found"}), 404

        # Update the interview
        cursor.execute("""
            UPDATE interviews 
            SET meeting_title = %s, date = %s, start_time = %s, end_time = %s
            WHERE id = %s
        """, (
            data['meeting_title'],
            data['meeting_date'],
            data['start_time'],
            data['end_time'],
            meeting_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Interview updated successfully"
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/update_technical_interview/<int:meeting_id>', methods=['PUT'])
def update_technical_interview(meeting_id):
    try:
        data = request.json
        required_fields = ['meeting_title', 'meeting_date', 'start_time', 'end_time']
        
        # Validate required fields
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if technical interview exists
        cursor.execute("""
            SELECT id FROM technical_interviews 
            WHERE id = %s
        """, (meeting_id,))
        
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Technical interview not found"}), 404

        # Update the technical interview
        cursor.execute("""
            UPDATE technical_interviews 
            SET meeting_title = %s, interview_date = %s, start_time = %s, end_time = %s
            WHERE id = %s
        """, (
            data['meeting_title'],
            data['meeting_date'],
            data['start_time'],
            data['end_time'],
            meeting_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Technical interview updated successfully"
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/add_technical_interview', methods=['POST'])
def add_technical_interview():
    try:
        data = request.json
        required_fields = ['interview']
        
        # Validate required fields
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
            
        interview_data = data['interview']
        
        # Validate interview data
        interview_required_fields = ['applicant_id', 'job_id', 'meeting_title', 'meeting_date', 'start_time', 'end_time']
        if not all(field in interview_data for field in interview_required_fields):
            return jsonify({"status": "error", "message": "Missing required interview fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if applicant exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (interview_data['applicant_id'],))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Applicant not found"}), 404

        # Check if job exists and is open
        cursor.execute("SELECT status FROM jobs WHERE id = %s", (interview_data['job_id'],))
        job = cursor.fetchone()
        if not job:
            return jsonify({"status": "error", "message": "Job not found"}), 404
            
        if job[0].lower() != 'open':
            return jsonify({"status": "error", "message": "This job is no longer available"}), 400

        # Check if interview already scheduled for this time slot
        cursor.execute("""
            SELECT id FROM technical_interviews 
            WHERE applicant_id = %s AND job_id = %s AND interview_date = %s AND start_time = %s;
        """, (
            interview_data['applicant_id'], 
            interview_data['job_id'], 
            interview_data['meeting_date'], 
            interview_data['start_time']
        ))
        
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "A technical interview is already scheduled for this time slot"}), 400

        # Insert the technical interview
        cursor.execute("""
            INSERT INTO technical_interviews (
                applicant_id, job_id, meeting_title, interview_date, 
                start_time, end_time
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            interview_data['applicant_id'],
            interview_data['job_id'],
            interview_data['meeting_title'],
            interview_data['meeting_date'],
            interview_data['start_time'],
            interview_data['end_time']
        ))

        interview_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Technical interview scheduled successfully",
            "interview_id": interview_id
        }), 201

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
import traceback
from datetime import timedelta
def safe_serialize_time(val):
    if isinstance(val, timedelta):
        return str(val)
    elif hasattr(val, 'isoformat'):
        return val.isoformat()
    return val

@app.route('/add_interview_answers', methods=['POST'])
def add_interview_answers():
    try:
        data = request.json
        required_fields = ['interview_id', 'answers']
        
        # Validate required fields
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the interview exists
        cursor.execute("SELECT id FROM interviews WHERE id = %s", (data['interview_id'],))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Interview not found"}), 404

        # Insert the answers
        cursor.execute("""
            INSERT INTO interview_answers (interview_id, answers)
            VALUES (%s, %s)
        """, (data['interview_id'], json.dumps(data['answers'])))

        answer_id = cursor.lastrowid
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Answers submitted successfully",
            "answer_id": answer_id
        }), 201

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/get_interview_answers/<int:interview_id>', methods=['GET'])
def get_interview_answers(interview_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the answers for the interview
        cursor.execute("""
            SELECT id, answers, created_at
            FROM interview_answers
            WHERE interview_id = %s
        """, (interview_id,))
        
        answers = cursor.fetchone()
        if not answers:
            return jsonify({"status": "error", "message": "Answers not found"}), 404

        answer_data = {
            "id": answers[0],
            "answers": json.loads(answers[1]),
            "created_at": answers[2].isoformat() if answers[2] else None
        }

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "answers": answer_data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
@app.route('/add_answer_evaluation', methods=['POST'])
def add_answer_evaluation():
    try:
        data = request.json
        app.logger.debug(f"Received data: {data}")

        required_fields = ['answer_id', 'avg_score_requirements', 'avg_score_responsibilities', 'full_evaluation', 'qualified_interview']
        
        # Validate required fields
        if not all(field in data for field in required_fields):
            app.logger.error("Missing required fields in the request")
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the answer exists
        app.logger.debug(f"Checking if Answer ID {data['answer_id']} exists in interview_answers")
        cursor.execute("SELECT id FROM interview_answers WHERE id = %s", (data['answer_id'],))
        if not cursor.fetchone():
            app.logger.error(f"Answer ID {data['answer_id']} not found in the database")
            return jsonify({"status": "error", "message": "Answer not found"}), 404

        # Extract only the required fields from full_evaluation
        full_evaluation = data['full_evaluation']
        reduced_evaluation = {
            "average_score_all_answers_requirements": full_evaluation["overall_scores"]["requirements"]["average_score_all_answers"],
            "average_score_all_answers_responsibilities": full_evaluation["overall_scores"]["responsibilities"]["average_score_all_answers"]
        }

        # Insert the evaluation
        app.logger.debug(f"Inserting evaluation for Answer ID {data['answer_id']}")
        cursor.execute("""
            INSERT INTO answer_evaluations (
                answer_id, avg_score_requirements, avg_score_responsibilities, 
                full_evaluation, qualified_interview
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            data['answer_id'],
            data['avg_score_requirements'],
            data['avg_score_responsibilities'],
            json.dumps(reduced_evaluation),  # Save only the reduced evaluation
            data['qualified_interview']
        ))

        evaluation_id = cursor.lastrowid
        conn.commit()

        app.logger.debug(f"Evaluation added successfully with ID: {evaluation_id}")
        return jsonify({
            "status": "success",
            "message": "Evaluation submitted successfully",
            "evaluation_id": evaluation_id
        }), 201

    except Exception as e:
        app.logger.error(f"Error in add_answer_evaluation: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/get_answer_evaluation/<int:answer_id>', methods=['GET'])
def get_answer_evaluation(answer_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the evaluation for the answer
        cursor.execute("""
            SELECT id, avg_score_requirements, avg_score_responsibilities, 
                   full_evaluation, qualified_interview, created_at
            FROM answer_evaluations
            WHERE answer_id = %s
        """, (answer_id,))
        
        evaluation = cursor.fetchone()
        if not evaluation:
            return jsonify({"status": "error", "message": "Evaluation not found"}), 404

        evaluation_data = {
            "id": evaluation[0],
            "avg_score_requirements": evaluation[1],
            "avg_score_responsibilities": evaluation[2],
            "full_evaluation": evaluation[3],
            "qualified_interview": evaluation[4],
            "created_at": evaluation[5].isoformat() if evaluation[5] else None
        }

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "evaluation": evaluation_data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

from datetime import timedelta

@app.route('/get_interview_answers', methods=['GET'])
def get_interview_answer():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch all interview answers
        cursor.execute("""
            SELECT 
                ia.id AS answer_id,
                ia.interview_id,
                ia.answers,
                ia.created_at,
                i.applicant_id,
                i.job_id,
                i.meeting_title,
                i.date AS interview_date,
                i.start_time,
                i.end_time
            FROM interview_answers ia
            JOIN interviews i ON ia.interview_id = i.id
        """)
        answers = cursor.fetchall()

        # Format the response
        formatted_answers = []
        for answer in answers:
            # Convert start_time and end_time to total seconds if they are timedelta objects
            if isinstance(answer["start_time"], timedelta):
                start_time = answer["start_time"].total_seconds()
            else:
                start_time = answer["start_time"]

            if isinstance(answer["end_time"], timedelta):
                end_time = answer["end_time"].total_seconds()
            else:
                end_time = answer["end_time"]

            formatted_answers.append({
                "answer_id": answer["answer_id"],
                "interview_id": answer["interview_id"],
                "answers": json.loads(answer["answers"]) if answer["answers"] else [],
                "created_at": answer["created_at"].isoformat() if answer["created_at"] else None,
                "applicant_id": answer["applicant_id"],
                "job_id": answer["job_id"],
                "meeting_title": answer["meeting_title"],
                "interview_date": answer["interview_date"].isoformat() if answer["interview_date"] else None,
                "start_time": start_time,
                "end_time": end_time
            })

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "answers": formatted_answers}), 200

    except Exception as e:
        app.logger.error(f"Error fetching interview answers: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@app.route('/get_interview', methods=['GET'])
def get_all_interviews():  # Renamed function to avoid conflict
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get all interviews
        cursor.execute("""
            SELECT 
                id,
                applicant_id,
                job_id,
                meeting_title,
                date,
                start_time,
                end_time,
                created_at,
                questions       
            FROM interviews
            ORDER BY date, start_time
        """)
        
        interviews = []
        for row in cursor.fetchall():
            interview = {
                "id": row[0],
                "applicant_id": row[1],
                "job_id": row[2],
                "meeting_title": row[3],
                "meeting_date": row[4].isoformat() if hasattr(row[4], 'isoformat') else row[4],
                "start_time": safe_serialize_time(row[5]),
                "end_time": safe_serialize_time(row[6]),
                "created_at": safe_serialize_time(row[7]),
                "questions": json.loads(row[8]) if row[8] else [],
            }
            interviews.append(interview)

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success", 
            "interviews": interviews
        }), 200

    except Exception as e:
        traceback.print_exc() 
        return jsonify({"status": "error", "message": str(e)}), 500
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@app.route('/get_interview/<int:question_id>', methods=['GET'])
def get_interview_by_id(question_id):  # Renamed function to avoid conflict
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the interview details based on the question_id
        cursor.execute("""
            SELECT 
                i.id AS interview_id,
                i.applicant_id,
                i.job_id,
                i.meeting_title,
                i.date AS interview_date,
                i.start_time,
                i.end_time,
                i.questions
            FROM interviews i
            WHERE i.id = %s
        """, (question_id,))
        
        interview = cursor.fetchone()

        if not interview:
            return jsonify({"status": "error", "message": "Interview not found"}), 404

        # Format the response
        interview_data = {
            "interview_id": interview["interview_id"],
            "applicant_id": interview["applicant_id"],
            "job_id": interview["job_id"],
            "meeting_title": interview["meeting_title"],
            "interview_date": interview["interview_date"].isoformat() if interview["interview_date"] else None,
            "start_time": safe_serialize_time(interview["start_time"]),
            "end_time": safe_serialize_time(interview["end_time"]),
            "questions": json.loads(interview["questions"]) if interview["questions"] else []
        }

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "interview": interview_data}), 200

    except Exception as e:
        app.logger.error(f"Error fetching interview: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()



@app.route('/get_interviews/<int:applicant_id>/<int:job_id>', methods=['GET'])
def get_interviews(applicant_id, job_id):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Query to get interviews for specific applicant and job
        query = """
        SELECT id, applicant_id, job_id, meeting_title, date, 
               start_time, end_time, questions, created_at
        FROM interviews
        WHERE applicant_id = %s AND job_id = %s
        """
        cursor.execute(query, (applicant_id, job_id))
        interviews = cursor.fetchall()

        cursor.close()
        db.close()

        # Convert datetime/date objects to strings
        interviews = [{
            **interview,
            'date': str(interview['date']),
            'start_time': str(interview['start_time']),
            'end_time': str(interview['end_time']),
            'created_at': str(interview['created_at'])
        } for interview in interviews]

        return jsonify({
            "status": "success",
            "message": "Interviews retrieved successfully",
            "interviews": interviews
        }), 200

    except mysql.connector.Error as err:
        return jsonify({
            "status": "error",
            "message": f"Database error: {err}"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500
