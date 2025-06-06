import streamlit as st
from PIL import Image
from streamlit_cropper import st_cropper
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
import json
import os
import pandas as pd
from datetime import date, datetime
import zipfile
from io import BytesIO
import shutil


# Constants
DATA_FILE = "student_data.json"
PHOTO_DIR = "photos"
PDF_DIR = "pdfs"
CARD_WIDTH, CARD_HEIGHT = 189, 321


# ------------------ CONFIG ------------------
st.set_page_config(page_title="Student ID Card Manager", page_icon="🎓", layout="wide")

# ------------------ USERS ------------------
USERS = {
    "aghs": "aghs@321",
    # "admin": "admin123",
    # "teacher": "teacher2024",
    # "staff": "staff@123"
}

# ------------------ SESSION INIT ------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'current_page' not in st.session_state:
    st.session_state.current_page = "add_student"
if 'selected_students' not in st.session_state:
    st.session_state.selected_students = []
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
if 'edit_student_id' not in st.session_state:
    st.session_state.edit_student_id = None

# ------------------ PERSIST LOGIN FROM URL ------------------
params = st.query_params
if params.get("logged_in", "false") == "true":
    st.session_state.authenticated = True

# ------------------ AUTH FUNCTIONS ------------------
def authenticate_user(username, password):
    return USERS.get(username) == password

def logout():
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.query_params.clear()
    st.rerun()

def login_form():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 2rem; background-color: #f0f2f6; border-radius: 10px; margin: 2rem 0;'>
            <h2>🎓 AL GHAZALI HIGH SCHOOL</h2>
            <p>Welcome to Student ID Manager</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")

            colA, colB, colC = st.columns([1, 1, 1])
            with colB:
                login_button = st.form_submit_button("🚀 Login", use_container_width=True)

            if login_button:
                if authenticate_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.query_params["logged_in"] = "true"
                    st.success(f"Welcome, {username}! 🎉")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password!")

        with st.expander("🔍 Demo Credentials"):
            st.markdown("""
            **Example Login Credentials:**
            - Username: `aghs` | Password: `aghs@321`
            - Username: `admin` | Password: `admin123`
            - Username: `teacher` | Password: `teacher2024`
            """)

# ------------------ AUTH CHECK ------------------
if not st.session_state.authenticated:
    login_form()
    st.stop()


# ------------------ LOGGED IN AREA ------------------
st.title("🎓 Enhanced Student ID Card Manager")

# Check if logo exists
logo_path = "assets/logo.png"
if os.path.exists(logo_path):
    logo = Image.open(logo_path)
    st.sidebar.image(logo, width=100)

st.sidebar.title("Navigation")

# Navigation
page = st.sidebar.selectbox(
    "Choose Page",
    ["Add Student", "Manage Students", "Bulk Operations", "Import/Export"],
    key="navigation"
)

if st.sidebar.button("🔒 Logout"):
    logout()

# Helper Functions
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, default=str)

def int_to_roman(num):
    if not num or not str(num).isdigit():
        return str(num)
    num = int(num)
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman += syms[i]
            num -= val[i]
        i += 1
    return roman

def generate_pdf(info, img_path):
    pdf_filename = f"{info['roll_no'].replace(' ', '_')}_card.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=(CARD_WIDTH, CARD_HEIGHT))

    # FRONT SIDE
    front_bg_path = "assets/1.jpeg"
    if os.path.exists(front_bg_path):
        c.drawImage(front_bg_path, 0, 0, 189, 321)

    c.setFillColor(HexColor("#231f55"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(94.5, 140, info['name'].upper())
    c.drawCentredString(94.5, 113, info['father_name'].upper())

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    roman_class = int_to_roman(info['class'])
    c.drawCentredString(90.5, 95, "Level" + "-" + roman_class)

    c.setFillColor(HexColor("#231f55"))
    c.setFont("Helvetica", 9)
    c.drawString(65, 67, info['roll_no'])
    c.drawString(65, 52, info['gr_number'])
    c.drawString(65, 37, datetime.fromisoformat(info["date_of_birth"]).strftime("%d %B, %Y"))

    # Draw photo if exists
    if img_path and os.path.exists(img_path):
        img_x = CARD_WIDTH - 149
        img_y = CARD_HEIGHT - 161.5
        img_size = 103

        # Draw circular clipping path
        c.saveState()
        p = c.beginPath()
        center_x = img_x + img_size / 2
        center_y = img_y + img_size / 2
        radius = img_size / 2

        p.circle(center_x, center_y, radius)
        c.clipPath(p, stroke=0, fill=0)

        # Draw the image inside the circle
        c.drawImage(img_path, img_x, img_y, width=img_size, height=img_size, mask='auto')
        c.restoreState()

    c.showPage()

    # BACK SIDE
    back_bg_path = "assets/2.jpeg"
    if os.path.exists(back_bg_path):
        c.drawImage(back_bg_path, 0, 0, 189, 321)

    # Generate QR Code
    qr_data = f"""Name: {info['name']}
Father Name: {info['father_name']}
Roll No: {info['roll_no']}
GR NO: {info['gr_number']}
DOB: {datetime.fromisoformat(info["date_of_birth"]).strftime("%d %B, %Y")}
Issue: {datetime.fromisoformat(info["date_of_issue"]).strftime("%d %B, %Y")}
Expiry: {datetime.fromisoformat(info["date_of_expiry"]).strftime("%d %B, %Y")}
Phone: {info['phone']}"""

    qr_code = qr.QrCodeWidget(qr_data)
    bounds = qr_code.getBounds()
    width_qr = bounds[2] - bounds[0]
    height_qr = bounds[3] - bounds[1]

    qr_size = 80
    scale_x = qr_size / width_qr 
    scale_y = qr_size / height_qr

    d = Drawing(qr_size, qr_size, transform=[scale_x, 0, 0, scale_y, 0, 0])
    d.add(qr_code)
    d.drawOn(c, 50, 118)

    c.setFillColor(HexColor("#231f55"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(95, 104, datetime.fromisoformat(info["date_of_issue"]).strftime("%d %B, %Y"))
    c.drawString(95, 93, datetime.fromisoformat(info["date_of_expiry"]).strftime("%d %B, %Y"))

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(85.5, 62.5, info['phone'])

    c.save()
    return pdf_path

def delete_student(student_id):
    data = load_data()
    student_to_delete = None
    
    for i, student in enumerate(data):
        if student.get('id') == student_id:
            student_to_delete = student
            data.pop(i)
            break
    
    if student_to_delete:
        # # Delete associated files
        # if student_to_delete.get('photo_path') and os.path.exists(student_to_delete['photo_path']):
        #     os.remove(student_to_delete['photo_path'])
        
        pdf_filename = f"{student_to_delete['roll_no'].replace(' ', '_')}_card.pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_filename)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        save_data(data)
        return True
    return False

# PAGE: Add Student
if page == "Add Student":
    st.header("📝 Add New Student")
    
    # Form Inputs
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Student Name")
    with col2:
        father_name = st.text_input("Father Name")

    col1, col2 = st.columns(2)
    with col1:
        roll_no = st.text_input("Roll Number")
    with col2:
        student_class = st.text_input("Class")

    col1, col2 = st.columns(2)
    with col1:
        phone = st.text_input("Phone Number")
    with col2:
        gr_number = st.text_input("GR Number")

    col1, col2, col3 = st.columns(3)
    with col1:
        date_of_birth = st.date_input("Date of Birth", min_value=date(1990, 1, 1), max_value=date.today())
    with col2:
        date_of_issue = st.date_input("Date of Issue", min_value=date(2010, 1, 1), max_value=date(2035, 12, 31))
    with col3:
        date_of_expiry = st.date_input("Date of Expiry", min_value=date_of_issue, max_value=date(2040, 12, 31))

    # Image upload
    st.markdown("---")
    st.subheader("📸 Upload & Crop Student Photo")
    profile_photo = st.file_uploader("Upload a Profile Photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    cropped_img = None
    if profile_photo:
        img = Image.open(profile_photo)
        st.image(img, caption="Original Uploaded Image", width=200)

        cropped_img = st_cropper(
            img,
            aspect_ratio=(1, 1),
            box_color="#00ADB5",
            return_type="image",
            key="cropper"
        )

        st.image(cropped_img, caption="✅ Cropped Profile Photo", width=150)
    else:
        st.info("Please upload a photo to enable cropping.")

    # Generate button
    st.markdown("---")
    if st.button("🎫 Add Student & Generate ID Card"):
        if not name or not roll_no:
            st.error("Please enter at least Student Name and Roll Number.")
        else:
            # Check for duplicate roll number
            data = load_data()
            if any(student['roll_no'] == roll_no for student in data):
                st.error("A student with this roll number already exists!")
            else:
                img_path = None
                if cropped_img:
                    img_filename = f"{roll_no.replace(' ', '_')}.png"
                    img_path = os.path.join(PHOTO_DIR, img_filename)
                    cropped_img.save(img_path)

                student_info = {
                    "id": len(data) + 1,
                    "name": name,
                    "father_name": father_name,
                    "roll_no": roll_no,
                    "class": student_class,
                    "phone": phone,
                    "gr_number": gr_number,
                    "date_of_birth": date_of_birth.isoformat(),
                    "date_of_issue": date_of_issue.isoformat(),
                    "date_of_expiry": date_of_expiry.isoformat(),
                    "photo_path": img_path,
                    "created_at": datetime.now().isoformat()
                }

                data.append(student_info)
                save_data(data)

                pdf_file_path = generate_pdf(student_info, img_path)
                st.success("✅ Student Added & ID Card Generated Successfully!")
                
                with open(pdf_file_path, "rb") as pdf_file:
                    st.download_button(
                        "📥 Download ID Card PDF", 
                        data=pdf_file, 
                        file_name=os.path.basename(pdf_file_path),
                        mime="application/pdf"
                    )

# PAGE: Manage Students
elif page == "Manage Students":
    st.header("👥 Manage Students")
    
    data = load_data()
    
    if not data:
        st.info("No students found. Add some students first!")
    else:
        # Filters
        st.subheader("🔍 Filters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            name_filter = st.text_input("Filter by Name", placeholder="Enter student name...")
        with col2:
            class_filter = st.selectbox("Filter by Class", ["All"] + list(set([s['class'] for s in data if s['class']])))
        with col3:
            roll_filter = st.text_input("Filter by Roll Number", placeholder="Enter roll number...")
        
        # Apply filters
        filtered_data = data
        if name_filter:
            filtered_data = [s for s in filtered_data if name_filter.lower() in s['name'].lower()]
        if class_filter != "All":
            filtered_data = [s for s in filtered_data if s['class'] == class_filter]
        if roll_filter:
            filtered_data = [s for s in filtered_data if roll_filter in s['roll_no']]
        
        st.markdown("---")
        st.subheader(f"📋 Students List ({len(filtered_data)} students)")
        
        # Display students
        for i, student in enumerate(filtered_data):
            with st.expander(f"🎓 {student['name']} - Roll: {student['roll_no']} - Class: {student['class']}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**Name:** {student['name']}")
                    st.write(f"**Father's Name:** {student['father_name']}")
                    st.write(f"**Roll Number:** {student['roll_no']}")
                    st.write(f"**Class:** {student['class']}")
                
                with col2:
                    st.write(f"**Phone:** {student['phone']}")
                    st.write(f"**GR Number:** {student['gr_number']}")
                    st.write(f"**Date of Birth:** {datetime.fromisoformat(student['date_of_birth']).strftime('%d %B, %Y')}")
                    st.write(f"**Card Expiry:** {datetime.fromisoformat(student['date_of_expiry']).strftime('%d %B, %Y')}")
                
                with col3:
                    if student.get('photo_path') and os.path.exists(student['photo_path']):
                        st.image(student['photo_path'], width=100)
                
                # Action buttons
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    pdf_filename = f"{student['roll_no'].replace(' ', '_')}_card.pdf"
                    pdf_path = os.path.join(PDF_DIR, pdf_filename)
                    if os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as pdf_file:
                            st.download_button(
                                "📥 Download PDF",
                                data=pdf_file,
                                file_name=pdf_filename,
                                mime="application/pdf",
                                key=f"download_{student['id']}"
                            )
                    else:
                        if st.button("🔄 Regenerate PDF", key=f"regen_{student['id']}"):
                            pdf_path = generate_pdf(student, student.get('photo_path'))
                            st.success("PDF regenerated successfully!")
                            st.rerun()
                
                with col2:
                    if st.button("✏️ Edit", key=f"edit_{student['id']}"):
                        st.session_state.edit_mode = True
                        st.session_state.edit_student_id = student['id']
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{student['id']}", type="secondary"):
                        if delete_student(student['id']):
                            st.success("Student deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete student!")
                
                with col4:
                    checkbox_key = f"select_{student['id']}"
                    if st.checkbox("Select", key=checkbox_key):
                        if student['id'] not in st.session_state.selected_students:
                            st.session_state.selected_students.append(student['id'])
                    else:
                        if student['id'] in st.session_state.selected_students:
                            st.session_state.selected_students.remove(student['id'])

        # Edit Mode
        if st.session_state.edit_mode and st.session_state.edit_student_id:
            st.markdown("---")
            st.subheader("✏️ Edit Student")
            
            # Find student to edit
            student_to_edit = next((s for s in data if s['id'] == st.session_state.edit_student_id), None)
            
            if student_to_edit:
                with st.form("edit_student_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_name = st.text_input("Student Name", value=student_to_edit['name'])
                        edit_roll_no = st.text_input("Roll Number", value=student_to_edit['roll_no'])
                        edit_phone = st.text_input("Phone Number", value=student_to_edit['phone'])
                    
                    with col2:
                        edit_father_name = st.text_input("Father Name", value=student_to_edit['father_name'])
                        edit_class = st.text_input("Class", value=student_to_edit['class'])
                        edit_gr_number = st.text_input("GR Number", value=student_to_edit['gr_number'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        edit_dob = st.date_input("Date of Birth", value=datetime.fromisoformat(student_to_edit['date_of_birth']).date())
                    with col2:
                        edit_issue = st.date_input("Date of Issue", value=datetime.fromisoformat(student_to_edit['date_of_issue']).date())
                    with col3:
                        edit_expiry = st.date_input("Date of Expiry", value=datetime.fromisoformat(student_to_edit['date_of_expiry']).date())
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Save Changes"):
                            # Update student data
                            for i, student in enumerate(data):
                                if student['id'] == st.session_state.edit_student_id:
                                    data[i].update({
                                        'name': edit_name,
                                        'father_name': edit_father_name,
                                        'roll_no': edit_roll_no,
                                        'class': edit_class,
                                        'phone': edit_phone,
                                        'gr_number': edit_gr_number,
                                        'date_of_birth': edit_dob.isoformat(),
                                        'date_of_issue': edit_issue.isoformat(),
                                        'date_of_expiry': edit_expiry.isoformat(),
                                        'updated_at': datetime.now().isoformat()
                                    })
                                    break
                            
                            save_data(data)
                            # Regenerate PDF
                            generate_pdf(data[i], data[i].get('photo_path'))
                            
                            st.session_state.edit_mode = False
                            st.session_state.edit_student_id = None
                            st.success("Student updated successfully!")
                            st.rerun()
                    
                    with col2:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state.edit_mode = False
                            st.session_state.edit_student_id = None
                            st.rerun()

# PAGE: Bulk Operations
elif page == "Bulk Operations":
    st.header("📦 Bulk Operations")
    
    data = load_data()
    selected_count = len(st.session_state.selected_students)
    
    st.info(f"Selected Students: {selected_count}")
    
    if selected_count > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Download Selected PDFs", type="primary"):
                # Create ZIP file with selected PDFs
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for student_id in st.session_state.selected_students:
                        student = next((s for s in data if s['id'] == student_id), None)
                        if student:
                            pdf_filename = f"{student['roll_no'].replace(' ', '_')}_card.pdf"
                            pdf_path = os.path.join(PDF_DIR, pdf_filename)
                            if os.path.exists(pdf_path):
                                zip_file.write(pdf_path, pdf_filename)
                            else:
                                # Generate PDF if it doesn't exist
                                pdf_path = generate_pdf(student, student.get('photo_path'))
                                zip_file.write(pdf_path, pdf_filename)
                
                zip_buffer.seek(0)
                st.download_button(
                    "📥 Download ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"selected_id_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip"
                )
        
        with col2:
            if st.button("🔄 Regenerate Selected PDFs"):
                progress_bar = st.progress(0)
                for i, student_id in enumerate(st.session_state.selected_students):
                    student = next((s for s in data if s['id'] == student_id), None)
                    if student:
                        generate_pdf(student, student.get('photo_path'))
                    progress_bar.progress((i + 1) / selected_count)
                st.success(f"Regenerated {selected_count} PDF(s) successfully!")
        
        with col3:
            if st.button("🗑️ Delete Selected", type="secondary"):
                deleted_count = 0
                for student_id in st.session_state.selected_students.copy():
                    if delete_student(student_id):
                        deleted_count += 1
                st.session_state.selected_students = []
                st.success(f"Deleted {deleted_count} student(s) successfully!")
                st.rerun()

    
    # Bulk PDF Generation
    st.markdown("---")
    st.subheader("📄 Generate All PDFs")
    
    if st.button("🎫 Generate All ID Cards"):
        if data:
            progress_bar = st.progress(0)
            success_count = 0
            
            for i, student in enumerate(data):
                try:
                    generate_pdf(student, student.get('photo_path'))
                    success_count += 1
                except Exception as e:
                    st.error(f"Failed to generate PDF for {student['name']}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(data))
            
            st.success(f"Generated {success_count} out of {len(data)} ID cards successfully!")
        else:
            st.info("No students found to generate PDFs for.")

# PAGE: Import/Export
elif page == "Import/Export":
    st.header("📊 Import/Export Data")
    
    # Export Section
    st.subheader("📤 Export Data")
    data = load_data()
    
    if data:
        # Convert to DataFrame for export
        df = pd.DataFrame(data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export to Excel
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Students', index=False)
            excel_buffer.seek(0)
            
            st.download_button(
                "📥 Export to Excel",
                data=excel_buffer.getvalue(),
                file_name=f"students_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            # Export to CSV
            csv_buffer = df.to_csv(index=False)
            st.download_button(
                "📥 Export to CSV",
                data=csv_buffer,
                file_name=f"students_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    else:
        st.info("No data to export.")
    
    # Import Section
    st.markdown("---")
    st.subheader("📤 Import Data")
    
    uploaded_file = st.file_uploader(
        "Upload Excel or CSV file",
        type=['xlsx', 'xls', 'csv'],
        help="Upload a file with student data. Required columns: name, father_name, roll_no, class, phone, gr_number, date_of_birth, date_of_issue, date_of_expiry"
    )
    
    if uploaded_file:
        try:
            # Read the file
            if uploaded_file.name.endswith('.csv'):
                import_df = pd.read_csv(uploaded_file)
            else:
                import_df = pd.read_excel(uploaded_file)
            
            st.write("Preview of imported data:")
            st.dataframe(import_df.head())
            
            # Validate required columns
            required_columns = ['name', 'father_name', 'roll_no', 'class', 'phone', 'gr_number', 'date_of_birth', 'date_of_issue', 'date_of_expiry', 'photo_path']
            missing_columns = [col for col in required_columns if col not in import_df.columns]
            
            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    import_mode = st.radio(
                        "Import Mode",
                        ["Add new students only", "Replace all data", "Update existing + add new"]
                    )
                
                with col2:
                    if st.button("🔄 Import Data", type="primary"):
                        try:
                            current_data = load_data()
                            
                            if import_mode == "Replace all data":
                                # Clear existing data and files
                                if os.path.exists(PHOTO_DIR):
                                    shutil.rmtree(PHOTO_DIR)
                                if os.path.exists(PDF_DIR):
                                    shutil.rmtree(PDF_DIR)
                                os.makedirs(PHOTO_DIR, exist_ok=True)
                                os.makedirs(PDF_DIR, exist_ok=True)
                                new_data = []
                            else:
                                new_data = current_data.copy()
                            
                            imported_count = 0
                            updated_count = 0
                            
                            for _, row in import_df.iterrows():
                                student_data = {
                                    'id': len(new_data) + 1,
                                    'name': str(row['name']),
                                    'father_name': str(row['father_name']),
                                    'roll_no': str(row['roll_no']),
                                    'class': str(row['class']),
                                    'phone': str(row['phone']),
                                    'gr_number': str(row['gr_number']),
                                    'date_of_birth': pd.to_datetime(row['date_of_birth']).date().isoformat(),
                                    'date_of_issue': pd.to_datetime(row['date_of_issue']).date().isoformat(),
                                    'date_of_expiry': pd.to_datetime(row['date_of_expiry']).date().isoformat(),
                                    'photo_path': str(row['photo_path']) if 'photo_path' in row and pd.notna(row['photo_path']) else None,
                                    'created_at': datetime.now().isoformat()
                                }
                                
                                if import_mode == "Update existing + add new":
                                    # Check if student exists (by roll number)
                                    existing_idx = next((i for i, s in enumerate(new_data) if s['roll_no'] == student_data['roll_no']), None)
                                    if existing_idx is not None:
                                        # Update existing student
                                        student_data['id'] = new_data[existing_idx]['id']
                                        student_data['photo_path'] = new_data[existing_idx].get('photo_path')
                                        student_data['updated_at'] = datetime.now().isoformat()
                                        new_data[existing_idx] = student_data
                                        updated_count += 1
                                    else:
                                        # Add new student
                                        new_data.append(student_data)
                                        imported_count += 1
                                else:
                                    # Add new students only
                                    if not any(s['roll_no'] == student_data['roll_no'] for s in new_data):
                                        new_data.append(student_data)
                                        imported_count += 1
                            
                            save_data(new_data)
                            
                            # Show results
                            if import_mode == "Replace all data":
                                st.success(f"Data replaced successfully! Imported {len(import_df)} students.")
                            elif import_mode == "Update existing + add new":
                                st.success(f"Import completed! Added {imported_count} new students, updated {updated_count} existing students.")
                            else:
                                st.success(f"Import completed! Added {imported_count} new students (skipped {len(import_df) - imported_count} duplicates).")
                            
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error importing data: {str(e)}")
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
    


# Sidebar Statistics
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Statistics")
data = load_data()
st.sidebar.metric("Total Students", len(data))

if data:
    # Class distribution
    class_counts = {}
    for student in data:
        class_name = student.get('class', 'Unknown')
        class_counts[class_name] = class_counts.get(class_name, 0) + 1
    
    st.sidebar.write("**Students by Class:**")
    for class_name, count in sorted(class_counts.items()):
        st.sidebar.write(f"• Class {class_name}: {count}")
    
    # Recent additions
    recent_students = sorted(
        [s for s in data if s.get('created_at')], 
        key=lambda x: x['created_at'], 
        reverse=True
    )[:3]
    
    if recent_students:
        st.sidebar.write("**Recent Additions:**")
        for student in recent_students:
            created_date = datetime.fromisoformat(student['created_at']).strftime('%m/%d')
            st.sidebar.write(f"• {student['name']} ({created_date})")

# Clear selections button
if st.session_state.selected_students:
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear Selections"):
        st.session_state.selected_students = []
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🎓 Enhanced Student ID Card Manager v2.0</p>
        <p>Features: Multi-student management • Bulk operations • Excel import/export • Advanced filtering</p>
    </div>
    """, 
    unsafe_allow_html=True
)