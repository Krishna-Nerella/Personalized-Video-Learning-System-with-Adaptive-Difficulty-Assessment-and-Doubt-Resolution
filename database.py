import psycopg2
import re
from datetime import datetime
import streamlit as st

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'AI',
    'user': 'postgres',
    'password': 'PASSWORD',
    'port': '5432'
}

def get_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def create_user(email, password):
    """Create new user account"""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT email FROM login WHERE email = %s", (email,))
        if cursor.fetchone():
            return False, "Email already registered"
        
        # Store password directly 
        cursor.execute(
            "INSERT INTO login (email, password) VALUES (%s, %s)",
            (email, password)
        )
        
        conn.commit()
        return True, "Account created successfully"
        
    except Exception as e:
        conn.rollback()
        return False, f"Error creating account: {str(e)}"
    finally:
        conn.close()

def authenticate_user(email, password):
    """Authenticate user login"""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # Get user data
        cursor.execute(
            "SELECT email, password, no_of_time_logged_in FROM login WHERE email = %s",
            (email,)
        )
        user_data = cursor.fetchone()
        
        if not user_data:
            return False, "Email not found"
        
        stored_email, stored_password, login_count = user_data
        
        # Compare passwords directly
        if password == stored_password:
            # Update login count and timestamp
            cursor.execute(
                """UPDATE login 
                   SET no_of_time_logged_in = %s, 
                       latest_login_time_stamp = %s 
                   WHERE email = %s""",
                (login_count + 1, datetime.now(), email)
            )
            conn.commit()
            return True, "Login successful"
        else:
            return False, "Invalid password"
            
    except Exception as e:
        return False, f"Login error: {str(e)}"
    finally:
        conn.close()

def log_ui_interaction(user_email, document_name=None, file_type=None, file_size=None, 
                      language_used="English", doubt_sessions=0, assessments_taken=0, 
                      quiz_score=None, video_scripts_generated=0, pdfs_generated=0):
    """Log user interaction with the UI"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO ui_interactions 
               (user_email, document_name, file_type, file_size, language_used, 
                doubt_sessions, assessments_taken, quiz_score, video_scripts_generated, pdfs_generated)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_email, document_name, file_type, file_size, language_used,
             doubt_sessions, assessments_taken, quiz_score, video_scripts_generated, pdfs_generated)
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error logging interaction: {str(e)}")
        return False
    finally:
        conn.close()

def update_ui_interaction(user_email, **updates):
    """Update UI interaction record for current session"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Get the latest interaction record for this user
        cursor.execute(
            "SELECT s_no FROM ui_interactions WHERE user_email = %s ORDER BY analysis_timestamp DESC LIMIT 1",
            (user_email,)
        )
        result = cursor.fetchone()
        
        if result:
            s_no = result[0]
            # Build update query dynamically
            update_fields = []
            values = []
            
            for field, value in updates.items():
                if field in ['doubt_sessions', 'assessments_taken', 'quiz_score', 
                           'video_scripts_generated', 'pdfs_generated']:
                    update_fields.append(f"{field} = %s")
                    values.append(value)
            
            if update_fields:
                values.append(s_no)
                query = f"UPDATE ui_interactions SET {', '.join(update_fields)} WHERE s_no = %s"
                cursor.execute(query, values)
                conn.commit()
                return True
        
        return False
    except Exception as e:
        st.error(f"Error updating interaction: {str(e)}")
        return False
    finally:
        conn.close()
