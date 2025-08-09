import streamlit as st
import google.generativeai as genai
import PyPDF2
from pptx import Presentation
import io
import base64
from PIL import Image
import tempfile
import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import markdown
import re
from functools import lru_cache
from contextlib import contextmanager
import logging
from typing import Dict, Optional, Tuple, Any

# Import custom modules
from auth import check_authentication, show_logout_option
from database import log_ui_interaction, update_ui_interaction
from prompts import (
    DOCUMENT_ANALYSIS_PROMPT,
    VIDEO_SCRIPT_PROMPT,
    CONCLUSION_PROMPT,
    ASSESSMENT_PROMPT,
    DOUBT_RESOLUTION_PROMPT,
    PDF_CONTENT_PROMPT,
    TRANSLATION_PROMPT
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SUPPORTED_FILE_TYPES = ['pdf', 'pptx', 'ppt']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
GEMINI_MODEL = 'gemini-2.0-flash'

# Configure page
st.set_page_config(
    page_title="Student Document Analyzer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

class SessionManager:
    """Manages Streamlit session state efficiently"""
    
    DEFAULT_VALUES = {
        'analysis_completed': False,
        'document_text': "",
        'analysis_result': "",
        'assessment_questions': None,
        'show_doubt_session': False,
        'show_assessment': False,
        'show_video_script': False,
        'show_conclusion': False,
        'show_personalized_pdf': False,
        'video_script': "",
        'conclusion_content': "",
        'quiz_performance': None,
        'selected_language': "English",
        'language_code': "en",
        'user_email': ""
    }
    
    @staticmethod
    def initialize():
        """Initialize session state with default values"""
        for key, value in SessionManager.DEFAULT_VALUES.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def reset_analysis():
        """Reset analysis-related session state"""
        reset_keys = [
            'analysis_completed', 'document_text', 'analysis_result', 
            'assessment_questions', 'video_script', 'conclusion_content', 
            'quiz_performance'
        ]
        for key in reset_keys:
            if key in SessionManager.DEFAULT_VALUES:
                st.session_state[key] = SessionManager.DEFAULT_VALUES[key]
        
        # Reset all show flags
        show_keys = [k for k in SessionManager.DEFAULT_VALUES.keys() if k.startswith('show_')]
        for key in show_keys:
            st.session_state[key] = False
    
    @staticmethod
    def set_view(view_name: str):
        """Set active view and reset others"""
        show_keys = [k for k in SessionManager.DEFAULT_VALUES.keys() if k.startswith('show_')]
        for key in show_keys:
            st.session_state[key] = (key == f'show_{view_name}')

class GeminiManager:
    """Manages Gemini API interactions"""
    
    def __init__(self):
        self._model = None
        self.configure()
    
    def configure(self) -> bool:
        """Configure Gemini API"""
        try:
            api_key = "API_KEY"
            genai.configure(api_key=api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}")
            return False
    
    @property
    def model(self):
        """Get or create Gemini model instance"""
        if self._model is None:
            self._model = genai.GenerativeModel(GEMINI_MODEL)
        return self._model
    
    def generate_content(self, prompt: str) -> Optional[str]:
        """Generate content using Gemini API with error handling"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            st.error(f"Error with Gemini API: {str(e)}")
            return None

# Global Gemini manager instance
@st.cache_resource
def get_gemini_manager():
    """Get cached Gemini manager instance"""
    return GeminiManager()

class LanguageManager:
    """Manages language support and translations"""
    
    SUPPORTED_LANGUAGES = {
        "English": "en",
        "Telugu": "te", 
        "Kannada": "kn",
        "Hindi": "hi"
    }
    
    UI_TRANSLATIONS = {
        "en": {
            "upload_header": "📄 Upload Your Document",
            "analysis_button": "🔍 Generate Multi-Level Analysis",
            "doubt_session": "🤔 Doubt Session",
            "assessment": "📝 Assessment",
            "video_script": "🎬 Video Script",
            "conclusion": "🎯 Conclusion",
            "personalized_pdf": "📄 Personalized Course PDF",
            "view_analysis": "📖 View Multi-Level Analysis",
            "new_analysis": "🔄 New Analysis",
            "easy_level": "⭐⭐ Easy Level (2.5/5)",
            "medium_level": "⭐⭐⭐⭐ Medium Level (3.5/5)",
            "hard_level": "⭐⭐⭐⭐⭐ Hard Level (4+/5)"
        },
        "te": {
            "upload_header": "📄 మీ పత్రాన్ని అప్‌లోడ్ చేయండి",
            "analysis_button": "🔍 బహుళ-స్థాయి విశ్లేషణ రూపొందించండి",
            "doubt_session": "🤔 సందేహాల సెషన్",
            "assessment": "📝 మూల్యాంకనం",
            "video_script": "🎬 వీడియో స్క్రిప్ట్",
            "conclusion": "🎯 ముగింపు",
            "personalized_pdf": "📄 వ్యక్తిగతీకరించిన కోర్సు PDF",
            "view_analysis": "📖 బహుళ-స్థాయి విశ్లేషణ చూడండి",
            "new_analysis": "🔄 కొత్త విశ్లేషణ",
            "easy_level": "⭐⭐ సులభ స్థాయి (2.5/5)",
            "medium_level": "⭐⭐⭐⭐ మధ్యమ స్థాయి (3.5/5)",
            "hard_level": "⭐⭐⭐⭐⭐ కష్ట స్థాయి (4+/5)"
        },
        "hi": {
            "upload_header": "📄 अपना दस्तावेज़ अपलोड करें",
            "analysis_button": "🔍 बहु-स्तरीय विश्लेषण बनाएं",
            "doubt_session": "🤔 संदेह सत्र",
            "assessment": "📝 मूल्यांकन",
            "video_script": "🎬 वीडियो स्क्रिप्ट",
            "conclusion": "🎯 निष्कर्ष",
            "personalized_pdf": "📄 व्यक्तिगत कोर्स PDF",
            "view_analysis": "📖 बहु-स्तरीय विश्लेषण देखें",
            "new_analysis": "🔄 नया विश्लेषण",
            "easy_level": "⭐⭐ आसान स्तर (2.5/5)",
            "medium_level": "⭐⭐⭐⭐ मध्यम स्तर (3.5/5)",
            "hard_level": "⭐⭐⭐⭐⭐ कठिन स्तर (4+/5)"
        },
        "kn": {
            "upload_header": "📄 ನಿಮ್ಮ ದಾಖಲೆಯನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
            "analysis_button": "🔍 ಬಹು-ಹಂತದ ವಿಶ್ಲೇಷಣೆಯನ್ನು ರಚಿಸಿ",
            "doubt_session": "🤔 ಸಂದೇಹ ಸೆಷನ್",
            "assessment": "📝 ಮೌಲ್ಯಮಾಪನ",
            "video_script": "🎬 ವೀಡಿಯೋ ಸ್ಕ್ರಿಪ್ಟ್",
            "conclusion": "🎯 ಸಮಾಪನೆ",
            "personalized_pdf": "📄 ವೈಯಕ್ತಿಕಗೊಳಿಸಿದ ಕೋರ್ಸ್ PDF",
            "view_analysis": "📖 ಬಹು-ಹಂತದ ವಿಶ್ಲೇಷಣೆಯನ್ನು ವೀಕ್ಷಿಸಿ",
            "new_analysis": "🔄 ಹೊಸ ವಿಶ್ಲೇಷಣೆ",
            "easy_level": "⭐⭐ ಸುಲಭ ಹಂತ (2.5/5)",
            "medium_level": "⭐⭐⭐⭐ ಮಧ್ಯಮ ಹಂತ (3.5/5)",
            "hard_level": "⭐⭐⭐⭐⭐ ಕಠಿಣ ಹಂತ (4+/5)"
        }
    }
    
    @staticmethod
    def get_text(key: str) -> str:
        """Get translated text for UI elements"""
        language_code = st.session_state.get('language_code', 'en')
        translations = LanguageManager.UI_TRANSLATIONS
        return translations[language_code].get(key, translations["en"][key])
    
    @staticmethod
    def translate_content(text: str, target_language: str) -> str:
        """Translate text to target language using Gemini"""
        if target_language == "en" or not text.strip():
            return text
        
        try:
            gemini = get_gemini_manager()
            language_names = {"te": "Telugu", "kn": "Kannada", "hi": "Hindi"}
            
            prompt = TRANSLATION_PROMPT.format(
                target_language=language_names[target_language],
                text=text
            )
            
            return gemini.generate_content(prompt) or text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

class DocumentProcessor:
    """Handles document processing operations"""
    
    @staticmethod
    @contextmanager
    def temporary_file(uploaded_file, suffix='.pptx'):
        """Context manager for temporary file handling"""
        tmp_file = None
        try:
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_file.write(uploaded_file.read())
            tmp_file.close()
            yield tmp_file.name
        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)
    
    @staticmethod
    def extract_text_from_pdf(uploaded_file) -> Optional[str]:
        """Extract text from PDF file with error handling"""
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text_parts = []
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    continue
            
            return "\n".join(text_parts) if text_parts else None
            
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            st.error(f"Error reading PDF: {str(e)}")
            return None
    
    @staticmethod
    def extract_text_from_ppt(uploaded_file) -> Optional[str]:
        """Extract text from PowerPoint file with error handling"""
        try:
            with DocumentProcessor.temporary_file(uploaded_file, '.pptx') as tmp_path:
                prs = Presentation(tmp_path)
                text_parts = []
                
                for slide_num, slide in enumerate(prs.slides, 1):
                    slide_text = f"Slide {slide_num}:\n"
                    slide_content = []
                    
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            slide_content.append(shape.text.strip())
                    
                    if slide_content:
                        slide_text += "\n".join(slide_content) + "\n\n"
                        text_parts.append(slide_text)
                
                return "\n".join(text_parts) if text_parts else None
                
        except Exception as e:
            logger.error(f"PowerPoint processing error: {e}")
            st.error(f"Error reading PowerPoint: {str(e)}")
            return None
    
    @staticmethod
    def validate_file(uploaded_file) -> Tuple[bool, str]:
        """Validate uploaded file"""
        if uploaded_file.size > MAX_FILE_SIZE:
            return False, f"File size ({uploaded_file.size:,} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE:,} bytes)"
        
        file_type = uploaded_file.type.lower()
        if not any(ft in file_type for ft in ['pdf', 'powerpoint', 'presentation']):
            return False, "Unsupported file type. Please upload PDF or PowerPoint files only."
        
        return True, "Valid file"

class ContentGenerator:
    """Handles AI content generation"""
    
    def __init__(self):
        self.gemini = get_gemini_manager()
    
    def analyze_document(self, text: str, file_type: str) -> Optional[str]:
        """Analyze document with Gemini API"""
        prompt = DOCUMENT_ANALYSIS_PROMPT.format(file_type=file_type, text=text)
        return self.gemini.generate_content(prompt)
    
    def generate_video_script(self, document_text: str) -> Optional[str]:
        """Generate engaging video script"""
        prompt = VIDEO_SCRIPT_PROMPT.format(document_text=document_text)
        return self.gemini.generate_content(prompt)
    
    def generate_conclusion(self, document_text: str) -> Optional[str]:
        """Generate comprehensive conclusion"""
        prompt = CONCLUSION_PROMPT.format(document_text=document_text)
        return self.gemini.generate_content(prompt)
    
    def generate_assessment(self, document_text: str) -> Optional[str]:
        """Generate assessment questions"""
        prompt = ASSESSMENT_PROMPT.format(document_text=document_text)
        return self.gemini.generate_content(prompt)
    
    def answer_doubt(self, question: str, document_text: str) -> Optional[str]:
        """Answer student's doubt"""
        prompt = DOUBT_RESOLUTION_PROMPT.format(
            document_text=document_text,
            question=question
        )
        return self.gemini.generate_content(prompt)
    
    def generate_pdf_content(self, document_text: str, quiz_performance=None) -> Optional[str]:
        """Generate content for personalized course PDF"""
        performance_context = ""
        if quiz_performance:
            performance_context = f"Student's quiz performance: {quiz_performance}. Tailor the content difficulty and focus areas based on this performance."
        
        prompt = PDF_CONTENT_PROMPT.format(
            performance_context=performance_context,
            document_text=document_text
        )
        return self.gemini.generate_content(prompt)

class PDFGenerator:
    """Handles PDF generation operations"""
    
    @staticmethod
    def create_pdf_from_content(content: str, filename: str = "personalized_course_guide.pdf") -> Optional[bytes]:
        """Create a PDF from the generated content"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()

            # Define custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor='darkblue',
                alignment=TA_CENTER,
                spaceAfter=30
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor='darkblue',
                spaceBefore=20,
                spaceAfter=10
            )
            
            subheading_style = ParagraphStyle(
                'CustomSubheading',
                parent=styles['Heading3'],
                fontSize=14,
                textColor='darkgreen',
                spaceBefore=15,
                spaceAfter=8
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=11,
                alignment=TA_JUSTIFY,
                spaceAfter=10
            )
            
            # Parse content and create PDF elements
            story = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 6))
                    continue
                    
                if line.startswith('# '):
                    story.append(Paragraph(line[2:], title_style))
                elif line.startswith('## '):
                    story.append(Paragraph(line[3:], heading_style))
                elif line.startswith('### '):
                    story.append(Paragraph(line[4:], subheading_style))
                else:
                    if line:
                        story.append(Paragraph(line, body_style))
            
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
        
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            st.error(f"Error creating PDF: {str(e)}")
            return None

class UIComponents:
    """Handles UI component rendering"""
    
    @staticmethod
    def render_sidebar():
        """Render sidebar navigation"""
        st.sidebar.image("https://img.icons8.com/dusk/64/000000/student-center.png", width=64)
        
        # Language Selection
        st.sidebar.markdown("## 🌐 Language / భాష / ಭಾಷೆ / भाषा")
        languages = LanguageManager.SUPPORTED_LANGUAGES
        selected_language = st.sidebar.selectbox(
            "Choose Language:",
            list(languages.keys()),
            index=list(languages.keys()).index(st.session_state.selected_language)
        )

        # Update session state if language changed
        if selected_language != st.session_state.selected_language:
            st.session_state.selected_language = selected_language
            st.session_state.language_code = languages[selected_language]
            st.rerun()

        st.sidebar.markdown("---")
        st.sidebar.markdown("## 📋 Navigation")
        
        # Navigation buttons if analysis is completed
        if st.session_state.analysis_completed:
            UIComponents._render_navigation_buttons()
    
    @staticmethod
    def _render_navigation_buttons():
        """Render navigation buttons in sidebar"""
        st.sidebar.markdown("### 🎯 Actions Available:")
        
        # Current active view
        active_views = {
            'analysis': not any([
                st.session_state.show_doubt_session,
                st.session_state.show_assessment,
                st.session_state.show_video_script,
                st.session_state.show_conclusion,
                st.session_state.show_personalized_pdf
            ]),
            'doubt_session': st.session_state.show_doubt_session,
            'assessment': st.session_state.show_assessment,
            'video_script': st.session_state.show_video_script,
            'conclusion': st.session_state.show_conclusion,
            'personalized_pdf': st.session_state.show_personalized_pdf
        }
        
        # Navigation buttons
        buttons = [
            ("view_analysis", "analysis"),
            ("doubt_session", "doubt_session"),
            ("assessment", "assessment"),
            ("video_script", "video_script"),
            ("conclusion", "conclusion"),
            ("personalized_pdf", "personalized_pdf")
        ]
        
        for text_key, view_key in buttons:
            button_type = "primary" if active_views[view_key] else "secondary"
            if st.sidebar.button(LanguageManager.get_text(text_key), 
                               use_container_width=True, type=button_type):
                if view_key == "analysis":
                    SessionManager.set_view("")  # Reset all views
                else:
                    SessionManager.set_view(view_key)
                st.rerun()
        
        st.sidebar.markdown("---")
        
        # New Analysis Button
        if st.sidebar.button(LanguageManager.get_text("new_analysis"), 
                           help="Clear current analysis to analyze a new document", 
                           use_container_width=True):
            SessionManager.reset_analysis()
            st.rerun()
    
    @staticmethod
    def render_file_upload():
        """Render file upload section"""
        st.header(LanguageManager.get_text("upload_header"))
        uploaded_file = st.file_uploader(
            "Choose a PDF or PowerPoint file",
            type=SUPPORTED_FILE_TYPES,
            help="Upload academic papers, lecture slides, or study materials"
        )
        
        if uploaded_file is not None:
            # Validate file
            is_valid, message = DocumentProcessor.validate_file(uploaded_file)
            if not is_valid:
                st.error(f"❌ {message}")
                return None
            
            # Display file details
            UIComponents._display_file_info(uploaded_file)
            
            # Process button
            if st.button(LanguageManager.get_text("analysis_button"), type="primary"):
                return UIComponents._process_document(uploaded_file)
        
        return None
    
    @staticmethod
    def _display_file_info(uploaded_file):
        """Display file information"""
        st.subheader("📋 Document Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**📄 Name:** {uploaded_file.name}")
        with col2:
            st.write(f"**📏 Size:** {uploaded_file.size:,} bytes")
        with col3:
            file_type = 'PDF' if 'pdf' in uploaded_file.type else 'PowerPoint'
            st.write(f"**🔧 Type:** {file_type}")
    
    @staticmethod
    def _process_document(uploaded_file):
        """Process uploaded document"""
        with st.spinner("🔄 Processing document and generating comprehensive analysis..."):
            # Extract text based on file type
            if uploaded_file.type == "application/pdf":
                text = DocumentProcessor.extract_text_from_pdf(uploaded_file)
                file_type = "PDF"
            else:
                text = DocumentProcessor.extract_text_from_ppt(uploaded_file)
                file_type = "PowerPoint"
            
            if text:
                st.session_state.document_text = text
                
                # Generate analysis
                content_gen = ContentGenerator()
                analysis = content_gen.analyze_document(text, file_type)
                
                if analysis:
                    st.session_state.analysis_result = analysis
                    st.session_state.analysis_completed = True
                    
                    # Log the interaction to database
                    try:
                        log_ui_interaction(
                            user_email=st.session_state.user_email,
                            document_name=uploaded_file.name,
                            file_type=file_type,
                            file_size=uploaded_file.size,
                            language_used=st.session_state.selected_language
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log interaction: {e}")
                    
                    st.success("✅ Analysis completed successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to generate analysis. Please try again.")
            else:
                st.error("❌ Failed to extract text from the document. Please check the file format.")
        
        return True

# Utility functions
def clean_json_string(raw_text: str) -> str:
    """Clean JSON string for parsing"""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"```json|```", "", cleaned)
    cleaned = cleaned.replace(""", '"').replace(""", '"')
    cleaned = cleaned.replace("'", "'").replace("'", "'")
    return cleaned

def display_translated_content(content: str) -> str:
    """Display content with translation if needed"""
    if st.session_state.language_code != "en":
        with st.spinner(f"🔄 Translating to {st.session_state.selected_language}..."):
            return LanguageManager.translate_content(content, st.session_state.language_code)
    return content

# View rendering functions
def render_doubt_session():
    """Render doubt session view"""
    st.header("🤔 Ask Your Doubts")
    st.markdown("Feel free to ask any questions about the document content. I'm here to help clarify your doubts!")
    
    student_question = st.text_area(
        "💭 What would you like to understand better?",
        placeholder="Type your question about the document content here...",
        height=100
    )
    
    if st.button("Get Answer", type="primary"):
        if student_question.strip():
            with st.spinner("🤔 Thinking about your question..."):
                content_gen = ContentGenerator()
                answer = content_gen.answer_doubt(student_question, st.session_state.document_text)
                
                if answer:
                    try:
                        update_ui_interaction(st.session_state.user_email, doubt_sessions=1)
                    except Exception as e:
                        logger.warning(f"Failed to update interaction: {e}")
                    
                    st.markdown("### 📚 Professor's Response:")
                    translated_answer = display_translated_content(answer)
                    st.markdown(translated_answer)
                else:
                    st.error("❌ Sorry, I couldn't process your question. Please try again.")
        else:
            st.warning("⚠️ Please enter a question first.")

def render_assessment():
    """Render assessment view"""
    st.header("📝 Knowledge Assessment")
    
    # Generate questions if not already generated
    if st.session_state.assessment_questions is None:
        with st.spinner("🔄 Generating personalized questions..."):
            content_gen = ContentGenerator()
            questions_json = content_gen.generate_assessment(st.session_state.document_text)
            
            if questions_json:
                try:
                    cleaned_json = clean_json_string(questions_json)
                    st.session_state.assessment_questions = json.loads(cleaned_json)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {e}")
                    st.error("❌ Error generating questions. Please try again.")
                    st.session_state.assessment_questions = None
    
    # Display questions if available
    if st.session_state.assessment_questions:
        st.markdown("**Instructions:** Choose the best answer for each question.")
        
        # Create form for questions
        with st.form("assessment_form"):
            answers = {}
            
            # Render questions dynamically
            for q_num in ["question1", "question2"]:
                if q_num in st.session_state.assessment_questions:
                    question_data = st.session_state.assessment_questions[q_num]
                    
                    st.markdown(f"### Question {q_num[-1]}")
                    st.markdown(question_data["question"])
                    
                    key = f"q{q_num[-1]}"
                    answers[key] = st.radio(
                        "Select your answer:",
                        list(question_data["options"].keys()),
                        format_func=lambda x, qd=question_data: f"{x}. {qd['options'][x]}",
                        key=key
                    )
                    
                    if q_num != "question2":  # Don't add separator after last question
                        st.markdown("---")
            
            # Submit button
            submitted = st.form_submit_button("📊 Submit Assessment", type="primary")
            
            if submitted:
                _process_assessment_results(answers)

def _process_assessment_results(answers: Dict[str, str]):
    """Process and display assessment results"""
    # Calculate score
    correct_answers = {
        "q1": st.session_state.assessment_questions["question1"]["correct_answer"],
        "q2": st.session_state.assessment_questions["question2"]["correct_answer"]
    }
    
    score = 0
    total = 2
    
    st.markdown("## 📊 Assessment Results")
    
    # Process each question
    for i, (q_key, correct_answer) in enumerate(correct_answers.items(), 1):
        st.markdown(f"### Question {i} Feedback")
        if answers[q_key] == correct_answer:
            st.success("✅ Correct!")
            score += 1
        else:
            st.error(f"❌ Incorrect. The correct answer is {correct_answer}")
        
        question_key = f"question{i}"
        explanation = st.session_state.assessment_questions[question_key]["explanation"]
        st.markdown(f"**Explanation:** {explanation}")
        
        if i < len(correct_answers):
            st.markdown("---")
    
    # Overall score
    percentage = (score / total) * 100
    st.markdown("### 🎯 Overall Performance")
    
    if percentage >= 50:
        st.success(f"🎉 Great job! You scored {score}/{total} ({percentage:.0f}%)")
        performance_level = "Good"
    else:
        st.warning(f"📚 You scored {score}/{total} ({percentage:.0f}%). Keep studying!")
        performance_level = "Needs Improvement"
    
    # Store quiz performance for PDF generation
    st.session_state.quiz_performance = {
        "score": score,
        "total": total,
        "percentage": percentage,
        "level": performance_level
    }
    
    try:
        update_ui_interaction(
            st.session_state.user_email, 
            assessments_taken=1,
            quiz_score=f"{score}/{total} ({percentage:.0f}%)"
        )
    except Exception as e:
        logger.warning(f"Failed to update interaction: {e}")

def render_video_script():
    """Render video script view"""
    st.header("🎬 Educational Video Script")
    
    # Generate video script if not already generated
    if not st.session_state.video_script:
        with st.spinner("🎥 Creating engaging video script..."):
            content_gen = ContentGenerator()
            script = content_gen.generate_video_script(st.session_state.document_text)
            
            if script:
                st.session_state.video_script = script
                try:
                    update_ui_interaction(st.session_state.user_email, video_scripts_generated=1)
                except Exception as e:
                    logger.warning(f"Failed to update interaction: {e}")
            else:
                st.error("❌ Failed to generate video script. Please try again.")
    
    # Display video script
    if st.session_state.video_script:
        translated_script = display_translated_content(st.session_state.video_script)
        st.markdown(translated_script)
        
        # Download button for script
        st.download_button(
            label="📥 Download Video Script",
            data=st.session_state.video_script,
            file_name="educational_video_script.md",
            mime="text/markdown",
            help="Download the complete video script for production"
        )

def render_conclusion():
    """Render conclusion view"""
    st.header("🎯 Conclusion & Applications")
    
    # Generate conclusion if not already generated
    if not st.session_state.conclusion_content:
        with st.spinner("🔄 Generating comprehensive conclusion..."):
            content_gen = ContentGenerator()
            conclusion = content_gen.generate_conclusion(st.session_state.document_text)
            
            if conclusion:
                st.session_state.conclusion_content = conclusion
            else:
                st.error("❌ Failed to generate conclusion. Please try again.")
    
    # Display conclusion
    if st.session_state.conclusion_content:
        translated_conclusion = display_translated_content(st.session_state.conclusion_content)
        st.markdown(translated_conclusion)

def render_personalized_pdf():
    """Render personalized PDF view"""
    st.header("📄 Personalized Course PDF")
    st.markdown("Generate a comprehensive study guide tailored to your learning needs and quiz performance.")
    
    # Show quiz performance if available
    if st.session_state.quiz_performance:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Quiz Score", f"{st.session_state.quiz_performance['score']}/{st.session_state.quiz_performance['total']}")
        with col2:
            st.metric("Percentage", f"{st.session_state.quiz_performance['percentage']:.0f}%")
        with col3:
            st.metric("Performance Level", st.session_state.quiz_performance['level'])
        
        st.info("📊 Your PDF will be customized based on your quiz performance!")
    else:
        st.info("💡 Take the assessment first for a more personalized PDF experience!")
    
    # Generate PDF button
    if st.button("Generate Personalized PDF", type="primary"):
        with st.spinner("📚 Creating your personalized study guide..."):
            content_gen = ContentGenerator()
            pdf_content = content_gen.generate_pdf_content(
                st.session_state.document_text, 
                st.session_state.quiz_performance
            )
            
            if pdf_content:
                # Create PDF
                pdf_bytes = PDFGenerator.create_pdf_from_content(pdf_content)
                
                if pdf_bytes:
                    st.success("✅ Your personalized PDF has been generated!")
                    try:
                        update_ui_interaction(st.session_state.user_email, pdfs_generated=1)
                    except Exception as e:
                        logger.warning(f"Failed to update interaction: {e}")
                    
                    # Download button
                    st.download_button(
                        label="📥 Download Personalized Course Guide",
                        data=pdf_bytes,
                        file_name="personalized_course_guide.pdf",
                        mime="application/pdf",
                        help="Download your customized study guide PDF"
                    )
                    
                    # Preview content
                    with st.expander("👀 Preview PDF Content"):
                        st.markdown(pdf_content)
                else:
                    st.error("❌ Failed to create PDF. Please try again.")
            else:
                st.error("❌ Failed to generate PDF content. Please try again.")

def render_analysis_results():
    """Render analysis results view"""
    st.header("📚 Document Analysis Results")
    translated_analysis = display_translated_content(st.session_state.analysis_result)
    st.markdown(translated_analysis)
    
    # Action buttons at bottom of analysis
    st.markdown("---")
    st.markdown("### 🚀 Next Steps")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Ask Questions", help="Get clarification on any doubts"):
            SessionManager.set_view("doubt_session")
            st.rerun()
    
    with col2:
        if st.button("Take Assessment", help="Test your understanding"):
            SessionManager.set_view("assessment")
            st.rerun()
    
    with col3:
        if st.button("View Video Script", help="See educational video script"):
            SessionManager.set_view("video_script")
            st.rerun()

def render_main_content():
    """Render main content based on current view"""
    if not st.session_state.analysis_completed:
        # File upload section
        UIComponents.render_file_upload()
        return
    
    # Route to appropriate view
    view_map = {
        'show_doubt_session': render_doubt_session,
        'show_assessment': render_assessment,
        'show_video_script': render_video_script,
        'show_conclusion': render_conclusion,
        'show_personalized_pdf': render_personalized_pdf
    }
    
    # Check which view is active
    active_view = None
    for view_key, render_func in view_map.items():
        if st.session_state.get(view_key, False):
            active_view = render_func
            break
    
    # Render active view or default analysis results
    if active_view:
        active_view()
    else:
        render_analysis_results()

def main():
    """Main application function"""
    # Check authentication first
    check_authentication()
    
    # Initialize session state
    SessionManager.initialize()
    
    # Configure Gemini API
    gemini_manager = get_gemini_manager()
    if not gemini_manager.configure():
        st.error("❌ Failed to configure AI service. Please try again later.")
        return
    
    # App header
    st.title("📚 Student Document Analyzer with AI")
    if st.session_state.user_email:
        st.markdown(f"Welcome back, **{st.session_state.user_email}**! Upload academic documents to get started.")
    
    # Render sidebar
    UIComponents.render_sidebar()
    
    # Render main content
    render_main_content()
    
    # Show logout option
    try:
        show_logout_option()
    except Exception as e:
        logger.warning(f"Failed to show logout option: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error("❌ An unexpected error occurred. Please refresh the page and try again.")
        st.exception(e)
