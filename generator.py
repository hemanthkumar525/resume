import streamlit as st
import google.generativeai as genai
from datetime import datetime
import re
import json
import base64
from io import BytesIO
import streamlit.components.v1 as components
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas

def render_latex_js(latex_code):
    """Render LaTeX using LaTeX.js in browser via Streamlit component"""
    safe_latex = latex_code.replace("\\", "\\\\").replace("`", "\\`").replace("'", "\\'")
    html_content = f"""
        <div id="latex-output">
            <script src="https://cdn.jsdelivr.net/npm/latex.js@0.12.4/dist/latex.min.js"></script>
            <script>
                const generator = new latexjs.HtmlGenerator({{ hyphenate: false }});
                const doc = latexjs.parse(`{safe_latex}`, {{ generator }});
                document.getElementById('latex-output').appendChild(doc.dom);
            </script>
            <style>
                #latex-output {{ font-size: 12px; padding: 20px; background: #f9f9f9; border-radius: 8px; }}
            </style>
            🔄 Rendering LaTeX document...
        </div>
    """
    components.html(html_content, height=700, scrolling=True)

def create_pdf_with_reportlab(user_data):
    """Create PDF using ReportLab (fallback option)"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=6,
        spaceBefore=12,
        textColor=colors.darkblue
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY
    )
    story = []
    name = user_data.get('name', 'Your Name')
    story.append(Paragraph(name, title_style))
    contact_info = []
    if user_data.get('email'):
        contact_info.append(user_data['email'])
    if user_data.get('phone'):
        contact_info.append(user_data['phone'])
    if user_data.get('location'):
        contact_info.append(user_data['location'])
    if contact_info:
        story.append(Paragraph(' • '.join(contact_info), normal_style))
    story.append(Spacer(1, 12))
    if user_data.get('summary'):
        story.append(Paragraph("PROFESSIONAL SUMMARY", heading_style))
        story.append(Paragraph(user_data['summary'], normal_style))
        story.append(Spacer(1, 12))
    if user_data.get('education'):
        story.append(Paragraph("EDUCATION", heading_style))
        for edu in user_data['education']:
            if edu.get('degree') and edu.get('institution'):
                edu_text = f"{edu['degree']}\n{edu['institution']}"
                if edu.get('year'):
                    edu_text += f" ({edu['year']})"
                if edu.get('cgpa'):
                    edu_text += f"\nCGPA: {edu['cgpa']}"
                story.append(Paragraph(edu_text, normal_style))
                story.append(Spacer(1, 6))
    if user_data.get('experience'):
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", heading_style))
        for exp in user_data['experience']:
            if exp.get('title') and exp.get('company'):
                exp_header = f"{exp['title']} - {exp['company']}"
                if exp.get('duration'):
                    exp_header += f" ({exp['duration']})"
                story.append(Paragraph(exp_header, normal_style))
                if exp.get('points'):
                    for point in exp['points']:
                        if point.strip():
                            story.append(Paragraph(f"• {point.strip()}", normal_style))
                story.append(Spacer(1, 8))
    if user_data.get('projects'):
        story.append(Paragraph("PROJECTS", heading_style))
        for proj in user_data['projects']:
            if proj.get('name'):
                proj_header = f"{proj['name']}"
                if proj.get('tech'):
                    proj_header += f" - {proj['tech']}"
                story.append(Paragraph(proj_header, normal_style))
                if isinstance(proj.get('description'), list):
                    for desc in proj['description']:
                        if desc.strip():
                            story.append(Paragraph(f"• {desc.strip()}", normal_style))
                elif proj.get('description'):
                    story.append(Paragraph(f"• {proj['description']}", normal_style))
                story.append(Spacer(1, 8))
    if user_data.get('skills'):
        story.append(Paragraph("TECHNICAL SKILLS", heading_style))
        for category, skills in user_data['skills'].items():
            if skills:
                story.append(Paragraph(f"{category}: {skills}", normal_style))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def configure_gemini(api_key):
    """Configure Gemini AI with the provided API key"""
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Error configuring Gemini AI: {str(e)}")
        return False

def generate_with_gemini(prompt, api_key):
    """Generate content using Gemini AI"""
    try:
        if not configure_gemini(api_key):
            return None
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating content with Gemini: {str(e)}")
        return None

def generate_professional_summary(name, field, experience_level, key_skills, api_key):
    """Generate professional summary using Gemini AI"""
    prompt = f"""
    Create a professional, ATS-friendly resume summary for {name}, a {experience_level} professional in {field}.
    Key skills: {key_skills}
    Requirements:
    - 2-3 sentences maximum
    - Include relevant keywords for ATS optimization
    - Highlight key achievements and value proposition
    - Professional tone
    - No personal pronouns
    Return only the summary text, no additional formatting.
    """
    return generate_with_gemini(prompt, api_key)

def enhance_job_description(title, company, basic_description, api_key):
    """Enhance job description using Gemini AI"""
    prompt = f"""
    Enhance this job description for a resume:
    Position: {title} at {company}
    Basic description: {basic_description}
    Requirements:
    - Create 3-4 bullet points
    - Start each with strong action verbs
    - Include quantifiable achievements where possible
    - Use ATS-friendly keywords
    - Professional tone
    - Focus on impact and results
    Return only the bullet points, one per line, without bullet symbols.
    """
    return generate_with_gemini(prompt, api_key)

def enhance_project_description(project_name, technologies, basic_description, api_key):
    """Enhance project description using Gemini AI"""
    prompt = f"""
    Enhance this project description for a resume:
    Project: {project_name}
    Technologies: {technologies}
    Basic description: {basic_description}
    Requirements:
    - Create 2-3 bullet points
    - Highlight technical skills and achievements
    - Include impact or results where possible
    - Use technical keywords appropriately
    - Professional and concise
    Return only the bullet points, one per line, without bullet symbols.
    """
    return generate_with_gemini(prompt, api_key)

def optimize_resume(user_data, api_key):
    """Optimize the resume content using Gemini AI to make it more professional, visually appealing, and ATS-friendly"""
    optimized_data = user_data.copy()

    # Step 1: Optimize Professional Summary
    if user_data.get('name') and user_data.get('field') and user_data.get('experience_level') and user_data.get('key_skills'):
        optimized_summary = generate_professional_summary(
            user_data['name'],
            user_data['field'],
            user_data['experience_level'],
            user_data['key_skills'],
            api_key
        )
        if optimized_summary:
            optimized_data['summary'] = optimized_summary
        else:
            optimized_data['summary'] = user_data.get('summary', '')

    # Step 2: Optimize Job Descriptions
    if user_data.get('experience'):
        optimized_experience = []
        for exp in user_data['experience']:
            if exp.get('title') and exp.get('company') and exp.get('basic_description'):
                enhanced_points = enhance_job_description(
                    exp['title'],
                    exp['company'],
                    exp['basic_description'],
                    api_key
                )
                if enhanced_points:
                    exp_copy = exp.copy()
                    exp_copy['points'] = [point for point in enhanced_points.split('\n') if point.strip()]
                    optimized_experience.append(exp_copy)
                else:
                    optimized_experience.append(exp)
            else:
                optimized_experience.append(exp)
        optimized_data['experience'] = optimized_experience

    # Step 3: Optimize Skills for ATS
    if user_data.get('skills'):
        optimized_skills = {}
        for category, skills in user_data['skills'].items():
            if skills:
                prompt = f"""
                Optimize the following skills list for ATS compatibility and clarity:
                Category: {category}
                Skills: {skills}
                Requirements:
                - Ensure keywords are ATS-friendly and relevant.
                - Remove duplicates and overly generic terms.
                - Return the optimized skills as a comma-separated string (e.g., "Skill1, Skill2, Skill3").
                - Do not include additional text or formatting.
                """
                optimized_skill_list = generate_with_gemini(prompt, api_key)
                if optimized_skill_list:
                    optimized_skills[category] = optimized_skill_list
                else:
                    optimized_skills[category] = skills
        optimized_data['skills'] = optimized_skills

    # Step 4: Ensure LaTeX Visual Optimization
    # The LaTeX structure in create_latex_resume is already ATS-friendly (no tables, no images, clear sections).
    # We will add additional user_data fields for visual enhancements that maintain ATS compatibility.
    optimized_data['software_skills'] = user_data.get('software_skills', {
        'Microsoft Project': {'rating': 5, 'label': 'Excellent'},
        'Windows Server': {'rating': 4, 'label': 'Very Good'},
        'Linux/Unix': {'rating': 4, 'label': 'Very Good'},
        'Microsoft Excel': {'rating': 3, 'label': 'Good'}
    })
    optimized_data['languages'] = user_data.get('languages', {
        'French': {'rating': 3, 'label': 'Intermediate'}
    })
    optimized_data['certifications'] = user_data.get('certifications', [
        {'name': 'PMP', 'issuer': 'Project Management Institute', 'date': '2010-05'},
        {'name': 'CAPM', 'issuer': 'Project Management Institute', 'date': '2007-11'},
        {'name': 'PRINCE2 Foundation', 'issuer': '', 'date': '2003-04'}
    ])
    optimized_data['interests'] = user_data.get('interests', [
        'Avid cross country skier and cyclist.',
        'Member of the Parent Teacher Association.',
        'Father of two passionate boys.',
        'Interested in personal development.'
    ])

    return optimized_data

def escape_latex(text):
    """Escape special LaTeX characters"""
    if not text:
        return ""
    latex_special_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '^': r'\^{}',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\~{}',
        '\\': r'\textbackslash{}'
    }
    for char, escaped in latex_special_chars.items():
        text = text.replace(char, escaped)
    return text

def create_latex_resume(user_data):
    """Create LaTeX resume code with enhanced visual appeal and ATS optimization"""
    name = user_data.get('name', 'John Smith')
    email = user_data.get('email', 'john.smith@email.com')
    phone = user_data.get('phone', '774-987-4032')
    linkedin = user_data.get('linkedin', 'linkedin.com/in/johnsmith')
    github = user_data.get('github', '')
    location = user_data.get('location', 'Portland, ME 04109')
    job_title = user_data.get('job_title', 'IT Project Manager')

    def safe_line(text):
        return escape_latex(text.strip()) if text else ''

    latex_content = r"""\documentclass[10pt, a4paper]{article}

% Setting up the page layout and basic packages
\usepackage[left=0.75in, right=0.75in, top=0.5in, bottom=0.5in]{geometry}
\usepackage{lmodern}
\usepackage[T1]{fontenc}
\usepackage{xcolor}
\usepackage{titlesec}
\usepackage{hyperref}
\usepackage{enumitem}
\usepackage{paracol}
\usepackage{pgffor}

% Defining colors for styling
\definecolor{primaryblue}{RGB}{42, 94, 133}
\definecolor{lightgray}{RGB}{220, 220, 220}

% Setting up hyperlinks
\hypersetup{
    colorlinks=true,
    urlcolor=primaryblue,
    linkcolor=primaryblue,
}

% Removing page numbers
\pagestyle{empty}

% Custom command for skill ratings with filled and empty bullets
\newcommand{\skillrating}[2]{%
    \textcolor{primaryblue}{\foreach \x in {1,...,#1}{\textbullet}\foreach \x in {1,...,#2}{\circ}}%
}

% Formatting section titles
\titleformat{\section}
  {\color{primaryblue}\normalsize\bfseries\MakeUppercase}
  {}{0em}
  {}
  [\vspace{-0.5ex}\textcolor{lightgray}{\titlerule[0.5pt]}]
\titlespacing*{\section}{0pt}{2.5ex}{0.5ex}

% Adjusting itemize spacing for tight lists
\setlist[itemize]{noitemsep, topsep=2pt, leftmargin=1.2em}

\begin{document}

% Header: Name, Job Title, and Summary
\begin{center}
    {\Huge\bfseries """ + safe_line(name) + r"""}
    \vspace{1mm}
    \\
    {\large\color{primaryblue}""" + safe_line(job_title) + r"""}
    \vspace{3mm}
    \\
    \small
    """ + safe_line(user_data.get('summary', 'IT professional with over 10 years of experience specializing in IT department management for international logistics companies. Greatest strength is business awareness, which enables permanent infrastructure and applications. Seeking to leverage IT management abilities in SanCorp.')) + r"""
    \vspace{5mm}
\end{center}

% Two-column layout
\setcolumnwidth{0.35\textwidth, 0.62\textwidth}
\begin{paracol}{2}

% Left Column: Personal Info, Skills, Software, Languages
\section*{Personal Info}
\small
""" + safe_line(location) + r""" \\
Phone: """ + safe_line(phone) + r""" \\
Email: """ + safe_line(email) + r""" \\""" + (r"""
LinkedIn: \href{""" + safe_line(linkedin) + r"""}{""" + safe_line(linkedin) + r"""} \\""" if linkedin else '') + (r"""
GitHub: \href{""" + safe_line(github) + r"""}{""" + safe_line(github) + r"""} \\""" if github else '') + r"""
\vspace{5mm}

\section*{Skills}
\small
"""
    # Skills section
    if user_data.get("skills"):
        for skill_category, skills_list in user_data["skills"].items():
            if skills_list and str(skills_list).strip():
                skills = [s.strip() for s in skills_list.split(",")]
                for skill in skills:
                    if skill:
                        latex_content += f"{safe_line(skill)} \\\\\n"
                latex_content += r"\vspace{2mm}" + "\n"

    latex_content += r"""
\vspace{5mm}

\section*{Software}
\small
\begin{itemize}
"""
    # Software section (dynamic if data is provided, otherwise default)
    software_skills = user_data.get('software_skills', {
        'Microsoft Project': {'rating': 5, 'label': 'Excellent'},
        'Windows Server': {'rating': 4, 'label': 'Very Good'},
        'Linux/Unix': {'rating': 4, 'label': 'Very Good'},
        'Microsoft Excel': {'rating': 3, 'label': 'Good'}
    })
    for software, info in software_skills.items():
        empty_bullets = 5 - info['rating']
        latex_content += f"    \\item {safe_line(software)} \\hfill \\skillrating{{{info['rating']}}}{{{empty_bullets}}} \\\\ \\small {info['label']}\n"
    latex_content += r"""\end{itemize}
\vspace{5mm}

\section*{Languages}
\small
\begin{itemize}
"""
    # Languages section (dynamic if data is provided, otherwise default)
    languages = user_data.get('languages', {
        'French': {'rating': 3, 'label': 'Intermediate'}
    })
    for lang, info in languages.items():
        empty_bullets = 5 - info['rating']
        latex_content += f"    \\item {safe_line(lang)} \\hfill \\skillrating{{{info['rating']}}}{{{empty_bullets}}} \\\\ \\small {info['label']}\n"
    latex_content += r"""\end{itemize}

\switchcolumn

% Right Column: Experience, Education, Certifications, Interests
\section*{Experience}
\small
"""
    # Experience section
    if user_data.get("experience"):
        for exp in user_data["experience"]:
            if exp.get("title") and exp.get("company"):
                latex_content += f"\\textbf{{{safe_line(exp['title'])}}} \\hfill {safe_line(exp.get('duration', ''))} \\\\\n"
                latex_content += f"\\textit{{{safe_line(exp['company'])}}}\n"
                if exp.get("location"):
                    latex_content += f" \\hfill {safe_line(exp['location'])}"
                latex_content += r"\\" + "\n"
                if exp.get("points") and any(point.strip() for point in exp["points"]):
                    latex_content += r"\begin{itemize}\n"
                    for point in exp.get("points", []):
                        if point.strip():
                            latex_content += f"    \\item {escape_latex(point.strip())}\n"
                    latex_content += r"\end{itemize}\n"
                latex_content += r"\vspace{3mm}" + "\n"

    latex_content += r"""
\section*{Education}
\small
"""
    # Education section
    if user_data.get("education"):
        for edu in user_data["education"]:
            if edu.get("degree") and edu.get("institution"):
                latex_content += f"\\textbf{{{safe_line(edu['degree'])}}} \\hfill {safe_line(edu.get('year', ''))} \\\\\n"
                latex_content += f"{safe_line(edu['institution'])} \\\\\n"
                if edu.get('cgpa'):
                    latex_content += r"\begin{itemize}\n"
                    latex_content += f"    \\item CGPA: {safe_line(edu['cgpa'])}\n"
                    latex_content += r"\end{itemize}\n"
                latex_content += r"\vspace{5mm}" + "\n"

    latex_content += r"""
\section*{Certifications}
\small
\begin{itemize}
"""
    # Certifications section (dynamic if data is provided, otherwise default)
    certifications = user_data.get('certifications', [
        {'name': 'PMP', 'issuer': 'Project Management Institute', 'date': '2010-05'},
        {'name': 'CAPM', 'issuer': 'Project Management Institute', 'date': '2007-11'},
        {'name': 'PRINCE2 Foundation', 'issuer': '', 'date': '2003-04'}
    ])
    for cert in certifications:
        issuer = f" -- {safe_line(cert['issuer'])}" if cert.get('issuer') else ''
        latex_content += f"    \\item {safe_line(cert['name'])}{issuer} \\hfill {safe_line(cert['date'])}\n"
    latex_content += r"""\end{itemize}
\vspace{5mm}

\section*{Interests}
\small
\begin{itemize}
"""
    # Interests section (dynamic if data is provided, otherwise default)
    interests = user_data.get('interests', [
        'Avid cross country skier and cyclist.',
        'Member of the Parent Teacher Association.',
        'Father of two passionate boys.',
        'Interested in personal development.'
    ])
    for interest in interests:
        latex_content += f"    \\item {safe_line(interest)}\n"
    latex_content += r"""\end{itemize}

\end{paracol}

\end{document}
"""
    return latex_content

def main():
    st.set_page_config(page_title="AI-Powered Resume Generator", page_icon="📄", layout="wide")
    st.title("🤖 AI-Powered Resume Generator")
    st.markdown("Generate professional, ATS-optimized resumes with AI-enhanced content")
    st.info("☁️ **Cloud-Ready**: This version works on Streamlit Cloud without system LaTeX installation!")
    st.sidebar.header("🔑 AI Configuration")
    api_key = st.sidebar.text_input("Enter your Gemini API Key", type="password", 
                                   help="Get your free API key from Google AI Studio")
    if not api_key:
        st.warning("⚠️ Please enter your Gemini API key in the sidebar to use AI features")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.header("📋 Basic Information")
        name = st.text_input("Full Name*", placeholder="John Doe")
        email = st.text_input("Email Address*", placeholder="john.doe@email.com")
        phone = st.text_input("Phone Number*", placeholder="+1 (555) 123-4567")
        location = st.text_input("Location", placeholder="City, State")
        linkedin = st.text_input("LinkedIn Profile", placeholder="linkedin.com/in/johndoe")
        github = st.text_input("GitHub Profile", placeholder="github.com/johndoe")
        job_title = st.text_input("Job Title", placeholder="IT Project Manager")
        st.subheader("🎯 Professional Summary")
        if api_key:
            col_a, col_b = st.columns([2, 1])
            with col_a:
                field = st.text_input("Your Field/Industry", placeholder="Software Engineering")
                experience_level = st.selectbox("Experience Level", 
                                              ["Entry-level", "Mid-level", "Senior-level", "Executive"])
                key_skills = st.text_input("Key Skills (comma-separated)", 
                                         placeholder="Python, React, AWS, Machine Learning")
            with col_b:
                if st.button("🚀 Generate Summary with AI"):
                    if all([name, field, key_skills]):
                        with st.spinner("Generating professional summary..."):
                            ai_summary = generate_professional_summary(name, field, experience_level, key_skills, api_key)
                            if ai_summary:
                                st.session_state['generated_summary'] = ai_summary
                    else:
                        st.warning("Please fill in name, field, and key skills first")
        summary = st.text_area("Professional Summary*", 
                              value=st.session_state.get('generated_summary', ''),
                              height=100,
                              placeholder="Brief professional summary highlighting your key strengths and achievements")
    with col2:
        st.header("🎓 Education")
        education = []
        num_edu = st.number_input("Number of education entries", 1, 5, 1)
        for i in range(num_edu):
            with st.expander(f"Education {i+1}"):
                degree = st.text_input(f"Degree*", key=f"deg_{i}", 
                                     placeholder="Bachelor of Science in Computer Science")
                institution = st.text_input(f"Institution*", key=f"inst_{i}", 
                                          placeholder="University of Technology")
                year = st.text_input(f"Year*", key=f"year_{i}", placeholder="2020-2024")
                cgpa = st.text_input(f"CGPA/GPA", key=f"cgpa_{i}", placeholder="3.8/4.0")
                education.append({"degree": degree, "institution": institution, "year": year, "cgpa": cgpa})
        st.header("💼 Skills")
        skills = {}
        skill_categories = st.text_input("Skill Categories (comma-separated)", 
                                       value="Programming Languages, Frameworks & Libraries, Tools & Technologies, Soft Skills")
        for cat in skill_categories.split(','):
            cat = cat.strip()
            if cat:
                val = st.text_input(f"{cat}", key=f"skill_{cat}",
                                  placeholder="List relevant skills for this category")
                if val.strip():
                    skills[cat] = val.strip()
    st.header("💼 Work Experience")
    work_experience = []
    num_jobs = st.number_input("Number of work experiences", 0, 10, 0)
    for i in range(num_jobs):
        with st.expander(f"Work Experience {i+1}"):
            col_x, col_y = st.columns([2, 1])
            with col_x:
                title = st.text_input(f"Job Title", key=f"title_{i}", placeholder="Software Engineer")
                company = st.text_input(f"Company", key=f"comp_{i}", placeholder="Tech Corp Inc.")
                duration = st.text_input(f"Duration", key=f"dur_{i}", placeholder="Jan 2022 - Present")
                job_location = st.text_input(f"Location", key=f"jloc_{i}", placeholder="San Francisco, CA")
                basic_desc = st.text_area(f"Brief description of role", key=f"basic_desc_{i}",
                                        placeholder="Describe your main responsibilities and technologies used")
            with col_y:
                if api_key and st.button(f"🤖 Enhance with AI", key=f"enhance_{i}"):
                    if all([title, company, basic_desc]):
                        with st.spinner("Enhancing job description..."):
                            enhanced = enhance_job_description(title, company, basic_desc, api_key)
                            if enhanced:
                                st.session_state[f'enhanced_job_{i}'] = enhanced.split('\n')
                    else:
                        st.warning("Please fill in job title, company, and basic description first")
            points_text = st.text_area(f"Responsibilities & Achievements (one per line)", 
                                     key=f"pts_{i}",
                                     value='\n'.join(st.session_state.get(f'enhanced_job_{i}', [])),
                                     height=120,
                                     placeholder="• Developed scalable web applications\n• Improved system performance by 40%")
            work_experience.append({
                "title": title,
                "company": company,
                "duration": duration,
                "location": job_location,
                "basic_description": basic_desc,
                "points": [p.strip() for p in points_text.split("\n") if p.strip()]
            })
    st.header("🚀 Projects")
    projects = []
    num_proj = st.number_input("Number of projects", 0, 10, 0)
    for i in range(num_proj):
        with st.expander(f"Project {i+1}"):
            col_p, col_q = st.columns([2, 1])
            with col_p:
                proj_name = st.text_input(f"Project Name", key=f"pname_{i}", 
                                        placeholder="E-commerce Web Application")
                tech = st.text_input(f"Technologies Used", key=f"tech_{i}", 
                                   placeholder="React, Node.js, MongoDB, AWS")
                basic_proj_desc = st.text_area(f"Brief project description", key=f"basic_proj_{i}",
                                             placeholder="Describe what the project does and your role")
            with col_q:
                if api_key and st.button(f"🤖 Enhance Project", key=f"enhance_proj_{i}"):
                    if all([proj_name, tech, basic_proj_desc]):
                        with st.spinner("Enhancing project description..."):
                            enhanced = enhance_project_description(proj_name, tech, basic_proj_desc, api_key)
                            if enhanced:
                                st.session_state[f'enhanced_proj_{i}'] = enhanced.split('\n')
                    else:
                        st.warning("Please fill in project name, technologies, and basic description first")
            desc_text = st.text_area(f"Project Description (one point per line)", 
                                   key=f"pdesc_{i}",
                                   value='\n'.join(st.session_state.get(f'enhanced_proj_{i}', [])),
                                   height=100,
                                   placeholder="• Built responsive web application\n• Implemented secure user authentication")
            projects.append({
                "name": proj_name, 
                "tech": tech, 
                "description": [d.strip() for d in desc_text.split("\n") if d.strip()]
            })
    st.markdown("---")
    col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
    with col_gen2:
        if 'latex_code' not in st.session_state:
            st.session_state['latex_code'] = None
        if 'pdf_bytes' not in st.session_state:
            st.session_state['pdf_bytes'] = None
        if 'optimized' not in st.session_state:
            st.session_state['optimized'] = False

        if st.button("🎯 Generate Professional Resume", type="primary", use_container_width=True):
            required_fields = [name, email, phone, summary]
            if not all(required_fields):
                st.error("❌ Please fill in all required fields (marked with *)")
            else:
                user_data = {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "location": location,
                    "linkedin": linkedin,
                    "github": github,
                    "job_title": job_title,
                    "summary": summary,
                    "field": field,
                    "experience_level": experience_level,
                    "key_skills": key_skills,
                    "education": education,
                    "skills": skills,
                    "experience": work_experience,
                    "projects": projects
                }
                with st.spinner("Generating your professional resume..."):
                    latex_code = create_latex_resume(user_data)
                    pdf_bytes = create_pdf_with_reportlab(user_data)
                st.session_state['latex_code'] = latex_code
                st.session_state['pdf_bytes'] = pdf_bytes
                st.session_state['user_data'] = user_data
                st.session_state['optimized'] = False
                st.success("✅ Resume generated successfully!")

        if st.session_state.get('latex_code') and api_key and st.button("✨ Optimize Resume with AI", use_container_width=True):
            with st.spinner("Optimizing your resume..."):
                optimized_data = optimize_resume(st.session_state['user_data'], api_key)
                latex_code = create_latex_resume(optimized_data)
                pdf_bytes = create_pdf_with_reportlab(optimized_data)
            st.session_state['latex_code'] = latex_code
            st.session_state['pdf_bytes'] = pdf_bytes
            st.session_state['user_data'] = optimized_data
            st.session_state['optimized'] = True
            st.success("✅ Resume optimized successfully!")

        if st.session_state.get('latex_code'):
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                if st.session_state['pdf_bytes']:
                    b64_pdf = base64.b64encode(st.session_state['pdf_bytes']).decode()
                    href_pdf = f'<a href="data:application/pdf;base64,{b64_pdf}" download="resume.pdf">📄 Download PDF Resume</a>'
                    st.markdown(href_pdf, unsafe_allow_html=True)
            with col_dl2:
                b64_tex = base64.b64encode(st.session_state['latex_code'].encode()).decode()
                href_tex = f'<a href="data:text/plain;base64,{b64_tex}" download="resume.tex">📝 Download LaTeX Code</a>'
                st.markdown(href_tex, unsafe_allow_html=True)
            st.subheader("🧪 Live Resume Preview (LaTeX.js)")
            st.info("💡 This preview is rendered using LaTeX.js in your browser - no server-side LaTeX required!")
            render_latex_js(st.session_state['latex_code'])
            with st.expander("📄 LaTeX Source Code"):
                st.code(st.session_state['latex_code'], language="latex")
                st.info("💡 You can copy this LaTeX code and compile it locally with any LaTeX distribution (TeX Live, MiKTeX, etc.) for perfect formatting")
    st.markdown("---")
    st.markdown("""
        Made with ❤️ using Streamlit and Google Gemini AI
        ✨ Cloud-Ready: No system LaTeX installation required!
        Get your free Gemini API key from Google AI Studio
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()