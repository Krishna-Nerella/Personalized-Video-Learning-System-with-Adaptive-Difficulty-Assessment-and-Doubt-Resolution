import streamlit as st
from database import validate_email, create_user, authenticate_user

def show_login_page():
    """Display login page"""
    st.title("🔐 Student Document Analyzer - Login")
    st.markdown("---")
    
    # Create tabs for Login and Signup
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
    
    with tab1:
        st.header("Welcome Back!")
        st.markdown("Please enter your credentials to continue")
        
        with st.form("login_form"):
            email = st.text_input("📧 Email Address", placeholder="Enter your email")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                login_button = st.form_submit_button("🚀 Login", type="primary", use_container_width=True)
            
            if login_button:
                if not email or not password:
                    st.error("❌ Please fill in all fields")
                elif not validate_email(email):
                    st.error("❌ Please enter a valid email address")
                else:
                    with st.spinner("🔄 Authenticating..."):
                        success, message = authenticate_user(email, password)
                        if success:
                            st.success(f"✅ {message}")
                            st.session_state.logged_in = True
                            st.session_state.user_email = email
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
    
    with tab2:
        st.header("Create New Account")
        st.markdown("Join us to start analyzing your documents with AI")
        
        with st.form("signup_form"):
            new_email = st.text_input("📧 Email Address", placeholder="Enter your email")
            new_password = st.text_input("🔒 Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
            
            # Password requirements
            st.markdown("""
            **Password Requirements:**
            - At least 6 characters long
            - Must contain letters and numbers
            """)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                signup_button = st.form_submit_button("✨ Create Account", type="primary", use_container_width=True)
            
            if signup_button:
                # Validation
                if not new_email or not new_password or not confirm_password:
                    st.error("❌ Please fill in all fields")
                elif not validate_email(new_email):
                    st.error("❌ Please enter a valid email address")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters long")
                elif new_password != confirm_password:
                    st.error("❌ Passwords do not match")
                elif not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password):
                    st.error("❌ Password must contain both letters and numbers")
                else:
                    with st.spinner("🔄 Creating account..."):
                        success, message = create_user(new_email, new_password)
                        if success:
                            st.success(f"✅ {message}")
                            st.info("🎉 You can now login with your new account!")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}")

def show_logout_option():
    """Show logout option in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **Logged in as:** {st.session_state.user_email}")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def check_authentication():
    """Check if user is authenticated"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        show_login_page()
        st.stop()
    else:
        show_logout_option()