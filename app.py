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
from auth import check_authentication, show_logout_option
from database import log_ui_interaction, update_ui_interaction

# Configure page
st.set_page_config(
    page_title="Student Document Analyzer",
    page_icon="📚",
    layout="wide"
)

def configure_gemini():
    """Configure Gemini API"""
    api_key = "API_KEY"
    genai.configure(api_key=api_key)
    return True
def get_supported_languages():
    """Get list of supported languages"""
    return {
        "English": "en",
        "Telugu": "te", 
        "Kannada": "kn",
        "Hindi": "hi"
    }

def translate_text(text, target_language):
    """Translate text to target language using Gemini"""
    if target_language == "en":
        return text  
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        language_names = {
            "te": "Telugu",
            "kn": "Kannada", 
            "hi": "Hindi"
        }
        
        prompt = f"""
        Translate the following text to {language_names[target_language]}. 
        Maintain the markdown formatting, structure, and any special characters.
        Keep technical terms in their original form if they don't have direct translations.
        
        Text to translate:
        {text}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Translation error: {str(e)}")
        return text  # Return original text if translation fails

def display_translated_content(content):
    """Display content with translation if needed"""
    if st.session_state.language_code != "en":
        with st.spinner(f"🔄 Translating to {st.session_state.selected_language}..."):
            translated_content = translate_text(content, st.session_state.language_code)
            return translated_content
    return content

def get_ui_translations():
    """Get UI text translations"""
    return {
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

def get_text(key):
    """Get translated text for UI elements"""
    translations = get_ui_translations()
    return translations[st.session_state.language_code].get(key, translations["en"][key])

def extract_text_from_pdf(uploaded_file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def extract_text_from_ppt(uploaded_file):
    """Extract text from PowerPoint file"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name
        
        # Read the presentation
        prs = Presentation(tmp_file_path)
        text = ""
        
        for slide_num, slide in enumerate(prs.slides, 1):
            text += f"Slide {slide_num}:\n"
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
            text += "\n"
        
        # Clean up temporary file
        os.unlink(tmp_file_path)
        return text
    except Exception as e:
        st.error(f"Error reading PowerPoint: {str(e)}")
        return None

def analyze_with_gemini(text, file_type):
    """Analyze text using Gemini API with student-focused approach - Three difficulty levels"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        You are a caring, experienced professor who excels at making complex topics accessible to students at different learning levels. Your goal is to transform this {file_type} content into a comprehensive learning experience with THREE different difficulty levels.

        Create your response in this EXACT format:

        ## 📚 **Introduction**
        
        **🎯 What This Document Is About:**
        [Write a brief, engaging overview that works for all levels. Use simple language and relatable analogies.]

        **🌍 Real-World Relevance:**
        [Share exciting real-world examples that connect to students' daily experiences.]

        **🔑 Learning Path Overview:**
        [Explain that content is organized by difficulty levels to help students progress at their own pace.]

        ---

        ## 📖 **EASY LEVEL** ⭐⭐ (2.5/5 stars)
        *Perfect for beginners and those new to this topic*

        ### 📚 **Basic Understanding** 
        **🔤 Simple Concepts:**
        [Start from absolute basics. Use everyday analogies like "Think of it like ordering food on an app..." Define technical terms in the simplest possible way. Use short sentences and familiar examples.]

        **📖 Fundamental Ideas:**
        [Explain the core concepts as if talking to a middle school student. Use lots of analogies from daily life. Break everything into small, digestible pieces.]

        ### 🎨 **Visual Learning** 
        **📊 Simple Diagrams:**
        [Describe basic visual representations that are easy to understand. Focus on simple flowcharts and basic connections between concepts.]

        **🔄 Step-by-Step Process:**
        [Break down processes into 3-4 simple steps maximum. Use clear, sequential language like "First... Then... Finally..."]

        ### 💡 **Easy Examples** 
        **🌍 Everyday Examples:**
        [Use examples from social media, food delivery, shopping, or other familiar activities. Keep explanations short and sweet.]

        **🎯 Basic Applications:**
        [Show how this knowledge applies to simple, everyday situations that students can easily relate to.]

        ---

        ## 📖 **MEDIUM LEVEL** ⭐⭐⭐⭐ (3.5/5 stars)
        *For students with some background knowledge*

        ### 📚 **Detailed Explanation** 
        **🔤 Core Concepts & Definitions:**
        [Build on the basics with more technical detail. Introduce proper terminology while still using analogies. Connect concepts to show relationships.]

        **📖 Key Principles:**
        [Explain the "why" behind concepts. Use more sophisticated examples and show cause-and-effect relationships. Include some technical details.]

        ### 🎨 **Comprehensive Visuals** 
        **📊 Detailed Diagrams:**
        [Describe more complex visual representations. Include flowcharts with multiple branches, detailed process diagrams, and conceptual frameworks.]

        **🔄 Complete Process Flow:**
        [Walk through processes with 5-7 steps, showing interconnections. Explain decision points and alternative paths.]

        ### 💡 **Practical Examples** 
        **🌍 Real-World Applications:**
        [Use examples from various industries and professional contexts. Show how concepts apply in different scenarios.]

        **🔧 Problem-Solving Approach:**
        [Present structured problem-solving methods. Show multiple ways to approach challenges.]

        **❓ Common Questions:**
        [Address typical student concerns and misconceptions at this level.]

        ---

        ## 📖 **HARD LEVEL** ⭐⭐⭐⭐⭐ (4+ /5 stars)
        *For advanced students and those seeking mastery*

        ### 📚 **Advanced Analysis** 
        **🔤 Complex Concepts:**
        [Dive deep into sophisticated aspects. Use technical terminology appropriately. Discuss theoretical foundations and advanced principles.]

        **📖 Advanced Principles:**
        [Explore complex relationships, edge cases, and advanced applications. Discuss current research and emerging trends.]

        ### 🎨 **Sophisticated Modeling** 
        **📊 Complex Visualizations:**
        [Describe advanced diagrams, multi-dimensional models, and sophisticated frameworks. Include system-level thinking and integration concepts.]

        **🔄 Comprehensive Workflows:**
        [Present complete, real-world workflows with multiple decision points, feedback loops, and optimization considerations.]

        ### 💡 **Expert-Level Applications** 
        **🌍 Industry Case Studies:**
        [Provide detailed case studies from cutting-edge applications. Discuss challenges faced by professionals in the field.]

        **🔧 Advanced Problem-Solving:**
        [Present complex scenarios requiring synthesis of multiple concepts. Show how experts approach sophisticated challenges.]

        **❓ Research and Innovation:**
        [Discuss current research directions, unresolved questions, and opportunities for innovation.]

        **🎯 Professional Development:**
        [Connect to advanced career paths, specializations, and leadership roles in the field.]

        ---

        ## 🎓 **Learning Progression Guide**
        **📈 How to Use These Levels:**
        - Start with EASY if you're new to this topic
        - Move to MEDIUM when basic concepts feel comfortable
        - Tackle HARD level when you want professional-level understanding
        - Feel free to jump between levels for different concepts

        **💡 Study Tips for Each Level:**
        - EASY: Focus on understanding, use lots of examples
        - MEDIUM: Practice applications, connect concepts
        - HARD: Synthesize knowledge, think critically

        IMPORTANT: Write in an encouraging, professorial tone. Make each level feel achievable while building toward mastery. Use appropriate complexity for each level while maintaining engaging, clear explanations.

        Content to analyze:
        {text}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error with Gemini API: {str(e)}")
        return None
    
def generate_video_script(document_text):
    """Generate engaging video script based on document content"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        You are an experienced, charismatic faculty member who creates engaging educational videos. Your videos are known for being informative, entertaining, and easy to follow. Students love your teaching style because you make complex topics accessible and exciting.

        Create a comprehensive video script based on the document content. The script should be designed for a 10-15 minute educational video.

        SCRIPT FORMAT:

        # 🎬 **VIDEO SCRIPT: [TOPIC TITLE]**

        ## 📋 **Pre-Production Notes:**
        **Estimated Duration:** 12-15 minutes
        **Target Audience:** Students learning this topic
        **Tone:** Engaging, professorial, enthusiastic
        **Visual Aids Needed:** [List key diagrams, animations, or props mentioned in script]

        ---

        ## 🎭 **SCRIPT CONTENT:**

        ### **[INTRO - Hook & Welcome]** (0:00 - 1:30)
        **[On Screen: Engaging title animation]**

        **INSTRUCTOR:** [Write an enthusiastic opening that hooks the viewer. Start with a relatable scenario, intriguing question, or surprising fact. Introduce yourself as the subject expert and preview what they'll learn.]

        **[Visual Cue: Show preview clips or key points]**

        ---

        ### **[MAIN CONTENT - Part 1: Foundation]** (1:30 - 5:00)
        **[On Screen: Key concept diagrams]**

        **INSTRUCTOR:** [Explain core concepts using the "story-telling" approach. Use analogies, real-world examples, and build from simple to complex. Include natural pauses for emphasis and student processing time.]

        **[Visual Cue: Describe specific animations, diagrams, or demonstrations needed]**

        ---

        ### **[MAIN CONTENT - Part 2: Deep Dive]** (5:00 - 9:00)
        **[On Screen: Detailed examples and applications]**

        **INSTRUCTOR:** [Dive deeper into the topic with practical examples. Use phrases like "Now, let's see how this works in practice..." Show step-by-step processes and explain the reasoning behind each step.]

        **[Visual Cue: Describe hands-on demonstrations or case studies]**

        ---

        ### **[MAIN CONTENT - Part 3: Applications]** (9:00 - 12:00)
        **[On Screen: Real-world connections]**

        **INSTRUCTOR:** [Connect the topic to real-world applications and future career relevance. Use exciting examples from industry, current events, or emerging technologies.]

        **[Visual Cue: Show real-world examples, industry footage, or testimonials]**

        ---

        ### **[RECAP & CONCLUSION]** (12:00 - 14:00)
        **[On Screen: Summary points animation]**

        **INSTRUCTOR:** [Summarize key takeaways in an memorable way. Use the "Rule of 3" - highlight the 3 most important points. End with an inspiring message about the topic's importance.]

        **[Visual Cue: Clean, animated summary graphics]**

        ---

        ### **[CALL TO ACTION & NEXT STEPS]** (14:00 - 15:00)
        **[On Screen: Subscribe/Like animations]**

        **INSTRUCTOR:** [Encourage engagement, suggest next learning steps, and create excitement for continued learning. Include a warm, encouraging sign-off.]

        ---

        ## 🎯 **Production Notes:**
        - **Key Phrases to Emphasize:** [List 3-5 key terms that should be highlighted visually]
        - **Suggested B-Roll:** [Describe supporting footage or imagery needed]
        - **Interactive Elements:** [Suggest polls, quizzes, or engagement prompts]
        - **Accessibility Notes:** [Mention any visual descriptions needed for hearing-impaired viewers]


        IMPORTANT: Write the script in a conversational, engaging tone. Include natural speech patterns, enthusiasm markers, and clear transitions. The instructor should sound like the most inspiring teacher the student has ever had.

        Document Content to Base Script On:
        {document_text}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating video script: {str(e)}")
        return None

def generate_conclusion(document_text):
    """Generate comprehensive conclusion with domain-specific use cases"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        You are a seasoned professor wrapping up an important lesson. Create a comprehensive conclusion that reinforces understanding and shows real-world relevance.

        Create your response in this EXACT format:

        # 🎯 **CONCLUSION & REAL-WORLD APPLICATIONS**

        ## 📚 **Key Takeaways Recap**
        **🔑 The Big Picture:**
        [Summarize the main concepts in 2-3 clear, memorable statements. Use the "elevator pitch" approach - if you had 30 seconds to explain this topic to someone, what would you say?]

        **💡 Core Principles to Remember:**
        [List 3-4 fundamental principles that students should never forget. Frame these as "golden rules" or "key insights" that will serve them throughout their career.]

        ---

        ## 🌍 **Domain-Specific Use Cases**

        ### **🏢 In Industry & Business:**
        [Provide 2-3 specific examples of how this knowledge is applied in business settings. Use real company names or scenarios when possible. Explain the business impact and why this knowledge creates value.]

        ### **🔬 In Research & Development:**
        [Show how this topic contributes to advancing knowledge in the field. Mention current research trends, breakthrough discoveries, or emerging technologies that build on these concepts.]

        ### **💼 In Your Future Career:**
        [Paint a picture of specific job roles where this knowledge is crucial. Describe typical tasks, projects, or challenges where students will apply what they've learned. Make it aspirational and exciting.]

        ### **🌟 In Emerging Technologies:**
        [Connect the topic to cutting-edge developments like AI, IoT, blockchain, sustainability, or other relevant modern trends. Show how foundational knowledge enables innovation.]

        ---

        ## 🚀 **Next Steps for Mastery**

        **📖 Immediate Actions:**
        [Suggest 2-3 concrete steps students can take right now to deepen their understanding - practice problems, additional readings, projects, or experiments.]

        **🎯 Long-term Development:**
        [Recommend pathways for continued learning - advanced courses, certifications, projects, or areas of specialization that build on this foundation.]

        **🤝 Professional Development:**
        [Suggest ways to build professional competency - internships, networking opportunities, professional organizations, or skill-building activities.]

        ---

        ## 💭 **Final Reflection**
        **🌟 Why This Matters:**
        [End with an inspiring paragraph about the broader significance of this knowledge. Connect it to solving real-world problems, advancing human knowledge, or making a positive impact. Make students feel excited about what they've learned and eager to apply it.]

        **🎓 Your Learning Journey:**
        [Acknowledge the effort students have put in and encourage them to see this as one important step in their ongoing education. Build confidence and momentum for continued learning.]

        IMPORTANT: Write in an encouraging, professorial tone that builds confidence and excitement. Make students feel proud of what they've accomplished and eager to apply their new knowledge.

        Document Content:
        {document_text}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating conclusion: {str(e)}")
        return None

def generate_personalized_pdf_content(document_text, quiz_performance=None):
    """Generate content for personalized course PDF"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        performance_context = ""
        if quiz_performance:
            performance_context = f"Student's quiz performance: {quiz_performance}. Tailor the content difficulty and focus areas based on this performance."
        
        prompt = f"""
        You are creating a comprehensive, personalized study guide PDF. This should be a complete learning resource that students can use for in-depth study and reference.

        {performance_context}

        Create content in this EXACT format for PDF generation:

        # PERSONALIZED COURSE GUIDE

        ## COURSE OVERVIEW
        [Provide a comprehensive overview of the topic, its importance, and learning objectives. Write 2-3 substantial paragraphs.]

        ## THEORETICAL FOUNDATIONS

        ### Core Concepts
        [Explain fundamental concepts with detailed explanations. Use clear definitions, examples, and build complexity gradually. Include mathematical formulas or technical details where relevant.]

        ### Key Principles and Laws
        [Detail the governing principles, theories, or laws. Explain the reasoning behind each principle and how they interconnect.]

        ### Historical Context
        [Provide background on how these concepts developed, key contributors, and evolutionary milestones.]

        ## DETAILED EXPLANATIONS

        ### Step-by-Step Processes
        [Break down complex processes into clear, numbered steps. Explain the reasoning behind each step.]

        ### Mathematical/Technical Details
        [If applicable, include formulas, equations, calculations, or technical specifications with explanations.]

        ### Common Misconceptions
        [Address frequent misunderstandings and explain the correct concepts clearly.]

        ## PRACTICAL APPLICATIONS

        ### Industry Examples
        [Provide detailed real-world examples from various industries showing how these concepts are applied.]

        ### Case Studies
        [Include 2-3 detailed case studies that demonstrate practical application of the concepts.]

        ### Current Trends and Future Directions
        [Discuss how this field is evolving and emerging applications.]

        ## PRACTICE SECTION

        ### Worked Examples
        [Provide 3-4 detailed worked examples with complete solutions and explanations.]

        ### Practice Problems
        [Create 5-6 practice problems of varying difficulty with brief solution hints.]

        ### Self-Assessment Questions
        [Develop 8-10 questions that help students test their understanding.]

        ## ADDITIONAL RESOURCES

        ### Recommended Readings
        [Suggest books, papers, or articles for deeper study.]

        ### Online Resources
        [Recommend websites, videos, or online courses for supplementary learning.]

        ### Professional Development
        [Suggest certifications, conferences, or professional organizations relevant to this topic.]

        ## STUDY STRATEGIES

        ### Effective Study Methods
        [Provide specific study techniques tailored to this subject matter.]

        ### Common Pitfalls to Avoid
        [Warn about typical mistakes students make when learning this topic.]

        ### Tips for Practical Application
        [Offer advice on how to apply this knowledge in real-world situations.]

        IMPORTANT: Write comprehensive, detailed content suitable for an in-depth study guide. Use formal academic language while remaining accessible. Include specific examples, detailed explanations, and practical insights throughout.

        Document Content:
        {document_text}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating PDF content: {str(e)}")
        return None

def create_pdf_from_content(content, filename="personalized_course_guide.pdf"):
    """Create a PDF from the generated content"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()

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
                # Main title
                story.append(Paragraph(line[2:], title_style))
            elif line.startswith('## '):
                # Section heading
                story.append(Paragraph(line[3:], heading_style))
            elif line.startswith('### '):
                # Subsection heading
                story.append(Paragraph(line[4:], subheading_style))
            else:
                # Body text
                if line:
                    story.append(Paragraph(line, body_style))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    except Exception as e:
        st.error(f"Error creating PDF: {str(e)}")
        return None
def clean_json_string(raw_text):
    cleaned = raw_text.strip()
    cleaned = re.sub(r"```json|```", "", cleaned)  
    cleaned = cleaned.replace("“", '"').replace("”", '"')  
    cleaned = cleaned.replace("‘", "'").replace("’", "'")
    return cleaned

def generate_assessment(document_text):
    """Generate two MCQ questions based on the document content"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        You are creating an assessment for students based on the document content. Generate exactly 2 multiple choice questions that test understanding of the key concepts.

        REQUIREMENTS:
        1. Questions should test comprehension, not just memorization
        2. Each question must have exactly 4 options (A, B, C, D)
        3. Only one correct answer per question
        4. Questions should be challenging but fair
        5. Cover different aspects of the document

        Format your response as a JSON object with this EXACT structure:
        {{
            "question1": {{
                "question": "Question text here?",
                "options": {{
                    "A": "Option A text",
                    "B": "Option B text", 
                    "C": "Option C text",
                    "D": "Option D text"
                }},
                "correct_answer": "A",
                "explanation": "Detailed explanation of why this answer is correct and why others are wrong"
            }},
            "question2": {{
                "question": "Question text here?",
                "options": {{
                    "A": "Option A text",
                    "B": "Option B text",
                    "C": "Option C text", 
                    "D": "Option D text"
                }},
                "correct_answer": "B",
                "explanation": "Detailed explanation of why this answer is correct and why others are wrong"
            }}
        }}

        Document Content:
        {document_text}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating assessment: {str(e)}")
        return None

def answer_doubt(question, document_text):
    """Answer student's doubt based on the document content"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        You are a patient, caring professor helping a student understand their document. The student has asked a question about the content they're studying.

        IMPORTANT INSTRUCTIONS:
        1. First, check if the student's question is related to the document content provided below.
        2. If the question is NOT related to the document, respond EXACTLY with: "Your question is not related to the document. Please ask questions about the content you uploaded."
        3. If the question IS related to the document, provide a clear, easy-to-understand answer that:
           - Uses simple language and analogies
           - Gives concrete examples
           - Explains step-by-step if needed
           - Connects back to the document content
           - Is encouraging and supportive

        Document Content:
        {document_text}

        Student's Question: {question}

        Remember: Be like the most patient teacher who makes everything crystal clear for students.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error with Gemini API: {str(e)}")
        return None

def main():
    # Check authentication first
    check_authentication()
    
    st.title("📚 Student Document Analyzer with AI")
    st.markdown(f"Welcome back, **{st.session_state.user_email}**! Upload academic documents to get started.")
    configure_gemini()
    st.title("📚 Student Document Analyzer with AI")
    st.markdown("Upload academic documents")
    # Configure Gemini API
    configure_gemini()

    if 'user_email' not in st.session_state:
        st.session_state.user_email = ""
    
    # Initialize session state
    if 'analysis_completed' not in st.session_state:
        st.session_state.analysis_completed = False
    if 'document_text' not in st.session_state:
        st.session_state.document_text = ""
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = ""
    if 'assessment_questions' not in st.session_state:
        st.session_state.assessment_questions = None
    if 'show_doubt_session' not in st.session_state:
        st.session_state.show_doubt_session = False
    if 'show_assessment' not in st.session_state:
        st.session_state.show_assessment = False
    if 'show_video_script' not in st.session_state:
        st.session_state.show_video_script = False
    if 'show_conclusion' not in st.session_state:
        st.session_state.show_conclusion = False
    if 'show_personalized_pdf' not in st.session_state:
        st.session_state.show_personalized_pdf = False
    if 'video_script' not in st.session_state:
        st.session_state.video_script = ""
    if 'conclusion_content' not in st.session_state:
        st.session_state.conclusion_content = ""
    if 'quiz_performance' not in st.session_state:
        st.session_state.quiz_performance = None
    if 'selected_language' not in st.session_state:
        st.session_state.selected_language = "English"
    if 'language_code' not in st.session_state:
        st.session_state.language_code = "en"
    
    # Set default values for student preferences
    student_domain = "General Academic"
    knowledge_level = "Medium"
    
    # SIDEBAR NAVIGATION - Move navigation buttons to sidebar
    st.sidebar.image("https://img.icons8.com/dusk/64/000000/student-center.png", width=64)
    # Language Selection Section
    st.sidebar.markdown("## 🌐 Language / భాష / ಭಾಷೆ / भाषा")
    languages = get_supported_languages()
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
    
    # Navigation buttons in sidebar
    if st.session_state.analysis_completed:
        st.sidebar.markdown("### 🎯 Actions Available:")
        
        # Analysis View Button
        if st.sidebar.button(get_text("view_analysis"), use_container_width=True,
                            type="primary" if not any([st.session_state.show_doubt_session, 
                                                     st.session_state.show_assessment,
                                                     st.session_state.show_video_script,
                                                     st.session_state.show_conclusion,
                                                     st.session_state.show_personalized_pdf]) else "secondary"):
            st.session_state.show_doubt_session = False
            st.session_state.show_assessment = False
            st.session_state.show_video_script = False
            st.session_state.show_conclusion = False
            st.session_state.show_personalized_pdf = False
            st.rerun()
        
        # Doubt Session Button
        if st.sidebar.button(get_text("doubt_session"), use_container_width=True, 
                            type="primary" if st.session_state.show_doubt_session else "secondary"):
            st.session_state.show_doubt_session = True
            st.session_state.show_assessment = False
            st.session_state.show_video_script = False
            st.session_state.show_conclusion = False
            st.session_state.show_personalized_pdf = False
            st.rerun()
        
        # Assessment Button
        if st.sidebar.button(get_text("assessment"), use_container_width=True, 
                            type="primary" if st.session_state.show_assessment else "secondary"):
            st.session_state.show_assessment = True
            st.session_state.show_doubt_session = False
            st.session_state.show_video_script = False
            st.session_state.show_conclusion = False
            st.session_state.show_personalized_pdf = False
            st.rerun()
        
        # Video Script Button
        if st.sidebar.button(get_text("video_script"), use_container_width=True, 
                            type="primary" if st.session_state.show_video_script else "secondary"):
            st.session_state.show_video_script = True
            st.session_state.show_doubt_session = False
            st.session_state.show_assessment = False
            st.session_state.show_conclusion = False
            st.session_state.show_personalized_pdf = False
            st.rerun()
        
        # Conclusion Button
        if st.sidebar.button(get_text("conclusion"), use_container_width=True, 
                            type="primary" if st.session_state.show_conclusion else "secondary"):
            st.session_state.show_conclusion = True
            st.session_state.show_doubt_session = False
            st.session_state.show_assessment = False
            st.session_state.show_video_script = False
            st.session_state.show_personalized_pdf = False
            st.rerun()
        
        # Personalized PDF Button
        if st.sidebar.button(get_text("personalized_pdf"), use_container_width=True, 
                            type="primary" if st.session_state.show_personalized_pdf else "secondary"):
            st.session_state.show_personalized_pdf = True
            st.session_state.show_doubt_session = False
            st.session_state.show_assessment = False
            st.session_state.show_video_script = False
            st.session_state.show_conclusion = False
            st.rerun()
        
        st.sidebar.markdown("---")
        
        # New Analysis Button
        if st.sidebar.button(get_text("new_analysis"), help="Clear current analysis to analyze a new document", use_container_width=True):
            # Reset all session state
            for key in ['analysis_completed', 'document_text', 'analysis_result', 'assessment_questions',
                       'show_doubt_session', 'show_assessment', 'show_video_script', 'show_conclusion',
                       'show_personalized_pdf', 'video_script', 'conclusion_content', 'quiz_performance']:
                if key in st.session_state:
                    if key.startswith('show_') or key == 'analysis_completed':
                        st.session_state[key] = False
                    else:
                        st.session_state[key] = "" if key != 'assessment_questions' and key != 'quiz_performance' else None
            st.rerun()
    
    # File upload section (only show if no analysis is completed or if we're in the main view)
    if not st.session_state.analysis_completed or not any([st.session_state.show_doubt_session, 
                                                          st.session_state.show_assessment,
                                                          st.session_state.show_video_script,
                                                          st.session_state.show_conclusion,
                                                          st.session_state.show_personalized_pdf]):
        st.header(get_text("upload_header"))
        uploaded_file = st.file_uploader(
            "Choose a PDF or PowerPoint file",
            type=['pdf', 'pptx', 'ppt'],
            help="Upload academic papers, lecture slides, or study materials"
        )
        
        if uploaded_file is not None:
            # Display file details
            file_details = {
                "Filename": uploaded_file.name,
                "File size": f"{uploaded_file.size:,} bytes",
                "File type": uploaded_file.type
            }
            
            st.subheader("📋 Document Information")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**📄 Name:** {file_details['Filename']}")
            with col2:
                st.write(f"**📏 Size:** {file_details['File size']}")
            with col3:
                st.write(f"**🔧 Type:** {'PDF' if 'pdf' in uploaded_file.type else 'PowerPoint'}")
            
            # Process button
            if st.button(get_text("analysis_button"), type="primary"):
                with st.spinner("🔄 Processing document and generating comprehensive analysis..."):
                    # Extract text based on file type
                    if uploaded_file.type == "application/pdf":
                        text = extract_text_from_pdf(uploaded_file)
                        file_type = "PDF"
                    else:
                        text = extract_text_from_ppt(uploaded_file)
                        file_type = "PowerPoint"
                    
                    if text:
                        st.session_state.document_text = text
                        
                        # Generate analysis
                        analysis = analyze_with_gemini(text, file_type)
                        if analysis:
                            st.session_state.analysis_result = analysis
                            st.session_state.analysis_completed = True
                            
                            # Log the interaction to database
                            log_ui_interaction(
                                user_email=st.session_state.user_email,
                                document_name=uploaded_file.name,
                                file_type=file_type,
                                file_size=uploaded_file.size,
                                language_used=st.session_state.selected_language
                            )
                            
                            st.success("✅ Analysis completed successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to generate analysis. Please try again.")
                    else:
                        st.error("❌ Failed to extract text from the document. Please check the file format.")
    
    # MAIN CONTENT AREA - Show different views based on navigation
    if st.session_state.analysis_completed:
        # DOUBT SESSION VIEW
        if st.session_state.show_doubt_session:
            st.header("🤔 Ask Your Doubts")
            st.markdown("Feel free to ask any questions about the document content. I'm here to help clarify your doubts!")
            
            # Doubt input
            student_question = st.text_area(
                "💭 What would you like to understand better?",
                placeholder="Type your question about the document content here...",
                height=100
            )
            
            if st.button("Get Answer", type="primary"):
                if student_question.strip():
                    with st.spinner("🤔 Thinking about your question..."):
                        answer = answer_doubt(student_question, st.session_state.document_text)
                        if answer:
                            update_ui_interaction(st.session_state.user_email, doubt_sessions=1)
                            st.markdown("### 📚 Professor's Response:")
                            translated_answer = display_translated_content(answer)
                            st.markdown(translated_answer)
                        else:
                            st.error("❌ Sorry, I couldn't process your question. Please try again.")
                else:
                    st.warning("⚠️ Please enter a question first.")
        
        # ASSESSMENT VIEW
        elif st.session_state.show_assessment:
            st.header("📝 Knowledge Assessment")
            
            # Generate questions if not already generated
            if st.session_state.assessment_questions is None:
                with st.spinner("🔄 Generating personalized questions..."):
                    questions_json = generate_assessment(st.session_state.document_text)
                    if questions_json:
                        try:
                            cleaned_json = clean_json_string(questions_json)
                            st.session_state.assessment_questions = json.loads(cleaned_json)
                        except json.JSONDecodeError:
                            st.error("❌ Error generating questions. Please try again.")
                            st.session_state.assessment_questions = None
            
            # Display questions if available
            if st.session_state.assessment_questions:
                st.markdown("**Instructions:** Choose the best answer for each question.")
                
                # Create form for questions
                with st.form("assessment_form"):
                    answers = {}
                    
                    # Question 1
                    st.markdown("### Question 1")
                    st.markdown(st.session_state.assessment_questions["question1"]["question"])
                    answers["q1"] = st.radio(
                        "Select your answer:",
                        list(st.session_state.assessment_questions["question1"]["options"].keys()),
                        format_func=lambda x: f"{x}. {st.session_state.assessment_questions['question1']['options'][x]}",
                        key="q1"
                    )
                    
                    st.markdown("---")
                    
                    # Question 2
                    st.markdown("### Question 2")
                    st.markdown(st.session_state.assessment_questions["question2"]["question"])
                    answers["q2"] = st.radio(
                        "Select your answer:",
                        list(st.session_state.assessment_questions["question2"]["options"].keys()),
                        format_func=lambda x: f"{x}. {st.session_state.assessment_questions['question2']['options'][x]}",
                        key="q2"
                    )
                    
                    # Submit button
                    submitted = st.form_submit_button("📊 Submit Assessment", type="primary")
                    
                    if submitted:
                        # Calculate score
                        correct_answers = {
                            "q1": st.session_state.assessment_questions["question1"]["correct_answer"],
                            "q2": st.session_state.assessment_questions["question2"]["correct_answer"]
                        }
                        
                        score = 0
                        total = 2
                        
                        st.markdown("## 📊 Assessment Results")
                        
                        # Question 1 feedback
                        st.markdown("### Question 1 Feedback")
                        if answers["q1"] == correct_answers["q1"]:
                            st.success("✅ Correct!")
                            score += 1
                        else:
                            st.error(f"❌ Incorrect. The correct answer is {correct_answers['q1']}")
                        st.markdown(f"**Explanation:** {st.session_state.assessment_questions['question1']['explanation']}")
                        
                        st.markdown("---")
                        
                        # Question 2 feedback
                        st.markdown("### Question 2 Feedback")
                        if answers["q2"] == correct_answers["q2"]:
                            st.success("✅ Correct!")
                            score += 1
                        else:
                            st.error(f"❌ Incorrect. The correct answer is {correct_answers['q2']}")
                        st.markdown(f"**Explanation:** {st.session_state.assessment_questions['question2']['explanation']}")
                        
                        # Overall score
                        percentage = (score / total) * 100
                        st.markdown("---")
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
                        update_ui_interaction(
                            st.session_state.user_email, 
                            assessments_taken=1,
                            quiz_score=f"{score}/{total} ({percentage:.0f}%)"
                        )
                                
        # VIDEO SCRIPT VIEW
        elif st.session_state.show_video_script:
            st.header("🎬 Educational Video Script")
            
            # Generate video script if not already generated
            if not st.session_state.video_script:
                with st.spinner("🎥 Creating engaging video script..."):
                    script = generate_video_script(st.session_state.document_text)
                    if script:
                        st.session_state.video_script = script
                        update_ui_interaction(st.session_state.user_email, video_scripts_generated=1)
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
        
        # CONCLUSION VIEW
        elif st.session_state.show_conclusion:
            st.header("🎯 Conclusion & Applications")
            
            # Generate conclusion if not already generated
            if not st.session_state.conclusion_content:
                with st.spinner("🔄 Generating comprehensive conclusion..."):
                    conclusion = generate_conclusion(st.session_state.document_text)
                    if conclusion:
                        st.session_state.conclusion_content = conclusion
                    else:
                        st.error("❌ Failed to generate conclusion. Please try again.")
            
            # Display conclusion
            if st.session_state.conclusion_content:
                translated_conclusion = display_translated_content(st.session_state.conclusion_content)
                st.markdown(translated_conclusion)
        
        # PERSONALIZED PDF VIEW
        elif st.session_state.show_personalized_pdf:
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
                    # Generate PDF content
                    pdf_content = generate_personalized_pdf_content(
                        st.session_state.document_text, 
                        st.session_state.quiz_performance
                    )
                    
                    if pdf_content:
                        # Create PDF
                        pdf_bytes = create_pdf_from_content(pdf_content)
                        
                        if pdf_bytes:
                            st.success("✅ Your personalized PDF has been generated!")
                            update_ui_interaction(st.session_state.user_email, pdfs_generated=1)
                            
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
        
        # DEFAULT VIEW - ANALYSIS RESULTS
        else:
            st.header("📚 Document Analysis Results")
            translated_analysis = display_translated_content(st.session_state.analysis_result)
            st.markdown(translated_analysis)
                        
            # Action buttons at bottom of analysis
            st.markdown("---")
            st.markdown("### 🚀 Next Steps")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Ask Questions", help="Get clarification on any doubts"):
                    st.session_state.show_doubt_session = True
                    st.rerun()
            
            with col2:
                if st.button("Take Assessment", help="Test your understanding"):
                    st.session_state.show_assessment = True
                    st.rerun()
            
            with col3:
                if st.button("View Video Script", help="See educational video script"):
                    st.session_state.show_video_script = True
                    st.rerun()

if __name__ == "__main__":
    main()
