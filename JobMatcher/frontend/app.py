from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import requests
import os
from datetime import datetime
from flask_mail import Mail, Message
import re
import logging
from prometheus_client import Counter, Histogram, generate_latest
import requests
import time
from nx_graph_store import build_nx_from_graph, merge_graphs, find_nodes, skill_overlap, simple_draw
from nx_graph_store import build_nx_from_graph, merge_graphs, save_gpickle
from graph_tools import set_KG
from agent_chat import chat
app = Flask(__name__)



# ========================
#   CONFIGURE FLASK-MAIL
# ========================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
# Replace with your Gmail credentials
app.config['MAIL_USERNAME'] = 'zynab.ahmad.saad@gmail.com' 
app.config['MAIL_DEFAULT_SENDER'] = 'zynab.ahmad.saad@gmail.com' 
app.config['MAIL_PASSWORD'] = 'teyv eues tgoq ipvt'  
mail = Mail(app)

# ===========================================
#   SECRET KEY FOR SESSION MANAGEMENT
# ===========================================
app.secret_key = 'dev-key-123-abc!@#'



BACKEND_API_URL = "http://backend:5000"
CV_EXTRACTION_URL = os.getenv('CV_EXTRACTION_URL')
JOB_DESCRIPTION_URL = os.getenv('JOB_DESCRIPTION_URL')


# ========================
#   LOGIN
# ========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password')
        register_option = request.form.get('user_type')
        
        # Validate inputs
        if not email or not password or not register_option:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('login'))
        
        if not validate_email_format(email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('login'))
    
        try:
            # Verifying Credentials 
            auth_response = requests.post(f"{BACKEND_API_URL}/login", json={
                    'email': email,
                    'password': password,
                    'register_option': register_option
                } ) 
            print(auth_response)
                
            if auth_response.status_code == 200:
                    data = auth_response.json()
                    session['user_id'] = data.get('user_id')
                    session['register_option'] = data.get('register_option')
                    session['email'] = email
                    
                     # Redirect based on user type (consider using a mapping)
                    if data.get('register_option') == 'company':
                        if session['user_id'] == 1:
                            return redirect(url_for('post_job'))
                        else:
                            return redirect(url_for('company_dashboard'))
                    
                    return redirect(url_for('upload_cv'))
            else:
                # Generic error message to prevent information disclosure
                flash('Login failed. Please check your credentials and try again', 'error')
                    
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Login connection error: {str(e)}")
            flash('Service temporarily unavailable. Please try again later', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('An unexpected error occurred during login', 'error')
        return redirect(url_for('login')) 
    return render_template('login.html')

# Function To Validate email
def validate_email_format(email):
    """Basic email format validation"""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None
@app.route('/match_search', methods=['GET', 'POST'])
def match_search():
    if request.method == 'POST':
        data = request.get_json() or {}
        text = data.get('text', '')
        
        result = {
            'original': text,
            'length': len(text),
            'words': len(text.split()),
            'uppercase': text.upper(),
            'lowercase': text.lower()
        }
        return render_template('match_search.html', result=result)
    
    # GET request just loads the page
    return render_template('match_search.html')
# ========================
#  SIGNUP
# ========================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # 1. Stronger Input Validation
        first_name = request.form.get('first_name','').strip()
        last_name = request.form.get('last_name','').strip()
        email = request.form.get('email','').strip()
        phone = request.form.get('phone_number','').strip()
        date_str = request.form.get('dob','').strip()
        password = request.form.get('password','').strip()
        confirm_password = request.form.get('confirm_password','').strip()
        
        # 2. Better Password Validation
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return redirect(url_for('signup'))
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))
        
        # 3. Email Validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email address', 'error')
            return redirect(url_for('signup'))
            
        
        # 5. Check for empty fields after cleaning
        if not all([first_name, last_name, email, phone, date_str, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('signup'))
        
        try:
            # Call database service to create user
            response = requests.post(f"{BACKEND_API_URL}/signup", json={
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'date':date_str,
                'phone_number': phone,
                'password': password
            }, )
            
            if response.status_code == 201:
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                try:
                    error_msg = response.json().get('message', 'Registration failed')
                    flash(error_msg, 'error')
                except ValueError:
                    flash('Registration failed - server error', 'error')
        except requests.exceptions.RequestException as e:
            flash('Service temporarily unavailable. Please try again later.', 'error')
            app.logger.error(f"Signup API error: {str(e)}")
        except Exception as e:
            flash('An unexpected error occurred', 'error')
            app.logger.exception("Unexpected signup error")
        
        return redirect(url_for('signup'))
    
    return render_template('signup.html')

# ========================
#   LOGOUT
# ========================
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    try:
        # Clear the session data
        session.clear()
        
        # Create a response with the index page
        response = make_response(redirect(url_for('index')))  # Redirect to index page
        
        # Add headers to prevent caching of the protected pages
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        
        # Add security headers to prevent going back
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ========================
#  MAIN APPLICATION ENTRY
# ========================
@app.route('/')
def index():
    return render_template('index.html')




# ===========================================
#       APPLICANR DASHBOARD CONFIGURATION
# ===========================================
# -------- CONFIGURATION FOR ALLOWED FILES --------
ALLOWED_EXTENSIONS = {'pdf'} # alowed extension
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB limit

# -------- FUNCTION FOR ALLOWED FILES --------
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ========================
#   UPLOAD CV
# ========================  
@app.route('/profile', methods=['GET', 'POST'])
def upload_cv():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('upload_cv'))
    

    # Handle POST requests (file upload) regardless of whether CV exists
    if request.method == 'POST':
        try:
            if 'pdfFile' not in request.files:
                flash('No file selected', 'error')
                return redirect(url_for('upload_cv'))  # Redirect back to upload page

            file = request.files['pdfFile'] 

            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(url_for('upload_cv'))
            
            if not (file and allowed_file(file.filename)):
                flash('Invalid file type. Only PDF/DOCX files are allowed', 'error')
                return redirect(url_for('upload_cv'))
            
            files = {'file': (file.filename, file.stream, file.mimetype)}
            logging.info(files)
            response = requests.post(f"{CV_EXTRACTION_URL}/extract-cv", files=files)
            logging.info(response)
            response.raise_for_status()

            # cv_data = response.json().get('cv_data', {})
                                  
            # if not cv_data.get('skills') or not cv_data.get('experience'):
            #     flash('CV processed but missing critical data (skills/experience)', 'warning')
            
            # save_response = requests.post(
            #     f"{BACKEND_API_URL}/add_applicant",
            #     json={'cv_data': cv_data, 'user_id': session['user_id']}
            # )
            
            # if save_response.status_code == 201:
            #     flash('CV uploaded and processed successfully!', 'success')
              
            #     return redirect(url_for('upload_cv'))
            
            # flash(save_response.json().get('message', 'Error saving CV data'), 'error')
        

        except requests.exceptions.RequestException as e:
            flash('CV processing service unavailable. Please try later.', 'error')
            app.logger.error(f"CV processing error: {str(e)}")
          
        except Exception as e:
            flash('An unexpected error occurred', 'error')
            app.logger.exception("CV upload error")
      

    # Always render the template with current has_cv status
    return render_template('upload_cv.html')




# ===========================================
#       DEPARTMENT DASHBOARD CONFIGURATION
# ===========================================

# ========================
#  DEPARTMENT DASHBOARD
# ========================
@app.route('/company_dashboard')
def company_dashboard():
    
    try:
        dept_id = session['user_id']
        job_offer_response = requests.get(f"{BACKEND_API_URL}/get_offered_job_by_dept/{dept_id}")
        
        if job_offer_response.status_code != 200:
            flash('Error fetching your company jobs', 'error')
            return render_template('company_dashboard.html', jobs=[], stats={})
        
        jobs = job_offer_response.json().get('jobs', [])
        
        # Transform job data to match template expectations
        processed_jobs = []
        for job in jobs:
            processed_job = {
                'id': job.get('id', 0),
                'job_title': job.get('title', ''),
                'job_level': job.get('job_level', ''),
                'years_experience': job.get('years_experience', ''),
                'date_offering': job.get('created_at', ''),
                'status': job.get('status', ''),
             
            }
            processed_jobs.append(processed_job)

        # Calculate Some Statistics To Display
        stats = {
            'total_jobs': len(processed_jobs),
            'open_jobs': sum(1 for job in processed_jobs if job.get('status', '').lower() == 'open'),
            'closed_jobs': sum(1 for job in processed_jobs if job.get('status', '').lower() == 'closed'),
            'total_applicants': sum(job.get('applicant_count', 0) for job in processed_jobs)
        }
        
        return render_template(
            'company_dashboard.html',
            jobs=processed_jobs,
            stats=stats
        )

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('company_dashboard.html', jobs=[], stats={})
      
# ========================
#   OFFER JOB
# ========================  
# need
@app.route('/post_job', methods=['POST','GET'])
def post_job():

    
    if request.method == 'POST':
        try:
            # Validate required fields first
            required_fields = ['jobTitle', 'jobLevel', 'yearsExperience','jobDescription']
            if not all(request.form.get(field) for field in required_fields):
                flash('Please fill all required fields', 'error')
                return redirect(url_for('post_job'))
                
            job_data = {
                'job_title': request.form.get('jobTitle'),   
                'department_id': session['user_id'],
                'job_level': request.form.get('jobLevel'),
                'years_experience': request.form.get('yearsExperience'),
                'additional_info': request.form.get('jobDescription'),     
              
            }
              
        except KeyError as e:
            flash(f'Missing key in session or form data: {str(e)}', 'error')
            return redirect(url_for('post_job'))
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'error')
            app.logger.error(f"Error creating job posting: {str(e)}")
            return redirect(url_for('post_job'))
        get_job_description_responce = requests.post(f"{JOB_DESCRIPTION_URL}/generate-job-description",
                                            json={
                                            'job_title' : job_data['job_title'],
                                            'job_level' : job_data['job_level'],
                                            'years_experience' : job_data['years_experience'],
                                            'additional_info' : job_data['additional_info']   
                                         })

       
        if get_job_description_responce.status_code != 200:
                    flash('Error saving job description', 'error')
                    return redirect(url_for('post_job'))
 
        job_description = get_job_description_responce.json().get('job_description', {})
        add_offer_job_response = requests.post(f"{BACKEND_API_URL}/add_offer_job", json={
                   "job_description" : job_description,
                   "department_id": job_data['department_id']
                })
        if add_offer_job_response.status_code != 201:
                    flash('Error In Saving job Offere', 'error')
                    return redirect(url_for('post_job'))
        
    return render_template('post_job.html')

# ===========================
#   FILTER JOBS BY DEPARTMENT
# ==========================  
@app.route('/job_applicants/<int:job_id>')
def job_applicants(job_id):
    try:
         # First get the job details
         job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{job_id}")
         if job_response.status_code != 200:
             flash('Job not found', 'error')
             return redirect(url_for('company_dashboard'))
            
         job = job_response.json().get('job')

         logging.basicConfig(level=logging.DEBUG)
         logger = logging.getLogger(__name__)
         # Verify this company owns the job
         if job['dept_id'] != session.get('user_id'):
             flash('You can only view applicants for your own jobs', 'error')
             return redirect(url_for('company_dashboard'))
        
         # Get all applications from the database
         applications_response = requests.get(f"{BACKEND_API_URL}/get_applicants/{job_id}")
         print(applications_response)
         if applications_response.status_code != 200:
             flash('Error fetching applications', 'error')
             return render_template('job_applicants.html', job=job, applicants=[])
            
         all_applications = applications_response.json().get('applications', [])
         logger.debug(f"app: {all_applications}")
         # For demo purposes, we'll just return all applications
         # In a real app, you'd want to filter applications that actually applied to this job
         # You would need an "applications" table that links users to jobs they applied for
        
         return render_template('job_applicants.html', 
                              job=job, 
                              applicants=all_applications)
    
    except Exception as e:
         flash(f'Error: {str(e)}', 'error')
         return redirect(url_for('company_dashboard'))

@app.template_filter('format_date')
def format_date_filter(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
        return date_obj.strftime('%b %d, %Y')
    except:
        return date_str





# ===========================
#   Visualise Graph
# ==========================  
@app.route('/visualise_graph')
def visualise_graph():


    ## get all cv and applicanr graphs
    cv_response = requests.get(f"{BACKEND_API_URL}/get_applicants")
    cv_graphs = cv_response.json().get('cv_graph', [])


    ## get all job and offered job graphs
    job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job")
    job_graphs = job_response.json().get('job_graph', [])
    


    # Build graphs
    G_cv, _ = build_nx_from_graph(cv_graphs)
    G_jd, _ = build_nx_from_graph(job_graphs)

    # Merge into a single knowledge graph
    KG = merge_graphs([G_cv, G_jd])

    save_gpickle(KG, r"C:\Users\aline\Desktop\hackathon")
    set_KG(KG)  # Update the global KG in graph_tools

    # Visualize (local debug)
    simple_draw(KG, node_limit=50)


# ===========================
#   Agent prompt
# ==========================  
@app.route('/Agent')
def agent_chat():
    """
    Receives a message from the chatbox and returns the agent's answer.
    """
    # read the prompt from the chatbox
    user_prompt = request.form.get("prompt")

    if not user_prompt:
        return jsonify({"error": "No prompt provided"}), 400

    print(f"User asked: {user_prompt}")
    try:
        answer = chat(user_prompt)
        return jsonify({"response": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)