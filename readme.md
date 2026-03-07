Smart Clinic Booking System

An AI-powered clinic appointment booking system with symptom checking capabilities, built for university health clinics.

🚀 Features

For Students
- AI Symptom Checker– Enter symptoms and get potential disease predictions with triage levels
- Online Appointment Booking– Book clinic appointments by service type, date, and time
- Real-time Notifications– Email confirmations and status updates via Outlook SMTP
- Appointment Management– View upcoming appointments and cancel if needed

For Admin/Staff
- Dashboard Overview– View today's appointments, completed visits, and statistics
- Appointment Control – Approve, reject, or complete appointments
- Service Management– Add or remove clinic services
- Student Management– View registered students and their appointment history

🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript, Jinja2 Templates |
| Database | MySQL |
| AI/ML | Scikit-learn (Naive Bayes), Joblib |
| Authentication| bcrypt, Session-based |
| Email| Outlook SMTP (Office 365) |

📁 Project Structure
smart-clinic-booking-system/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in repo)
├── NaiveBayes_model.pkl    # Trained ML model for symptom prediction
├── label_encoder.pkl       # Disease label encoder
├── symptom_list.pkl        # List of recognizable symptoms
├── triage_map.pkl          # Triage level mapping for diseases
├── static/                 # CSS, JavaScript, images
└── templates/              # HTML templates (Jinja2)
├── loginpage.html
├── home_page.html
├── studentdash.html
├── booking.html
├── adminpage.html
├── service.html
├── notification.html
└── add_service.html
plain
Copy

Installation

Prerequisites
- Python 3.8+
- MySQL Server
- Outlook/Hotmail account for SMTP
- 
1. Clone the Repository
bash
git clone https://github.com/Lwarhjeezy/smart-clinic-booking-system.git
cd smart-clinic-booking-system

3. Install Dependencies
bash
Copy
pip install -r requirements.txt

5. Set Up Environment Variables
Create a .env file in the root directory:
env
Copy
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_EMAIL=your-email@outlook.com
SMTP_PASSWORD=your-app-password
Note: Use an App Password if you have 2FA enabled.

6. Set Up Database
Create a MySQL database named clinic_booking_system2 and run the schema:
sql
Copy
Users table
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100),
    student_number VARCHAR(50) UNIQUE,
    email VARCHAR(100),
    password_hash VARCHAR(255),
    role ENUM('student', 'staff', 'admin')

);

Staff table
CREATE TABLE Staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    staff_name VARCHAR(100)
);

Appointment table
CREATE TABLE Appointment (
    appointment_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    staff_id INT,
    service_type VARCHAR(100),
    appointment_date DATE,
    appointment_time TIME,
    reason TEXT,
    status ENUM('pending', 'approved', 'rejected', 'completed', 'cancelled'),
    FOREIGN KEY (student_id) REFERENCES Users(user_id),
    FOREIGN KEY (staff_id) REFERENCES Staff(staff_id)
);

Service table
CREATE TABLE Service (
    service_id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(100)
);

Admin table (for hardcoded admin login)
CREATE TABLE admintb (
    username VARCHAR(50) PRIMARY KEY,
    user_password VARCHAR(100)
);

5. Run the Application
bash
Copy
uvicorn main:app --reload
Visit: http://127.0.0.1:8000
Default Login Credentials
Table
Role	Username	Password
Admin	admin	admin123 (change in production)
Students and staff use bcrypt-hashed passwords stored in the Users table.

🤖 AI Symptom Checker
The system uses a Naive Bayes classifier trained on symptom-disease data to:
Normalize user symptoms using fuzzy matching (handles typos, plurals)
Predict potential diseases with confidence scores
Assign triage levels:
🟢 Level 1 (Low) – Self-care, routine appointment
🟡 Level 2 (Moderate) – Book clinic visit soon
🔴 Level 3 (Urgent) – Seek immediate care

🎓 Academic Context
This project was developed as a Final Year Project for:
Course:     Final year Project
Institution: University of Zululand
Focus Areas: Full-Stack Development, AI Integration, Database Design, Project Management
🔮 Future Improvements:
Deploy to cloud (AWS/Heroku)
Add SMS notifications via Twilio
Implement real-time chat with nurses
Mobile app version (Flutter/React Native)
Electronic Health Records (EHR) integration

📄 License:
This project is for academic purposes. Contact me for collaboration or usage rights.

Authors :
Lwandile Ngidi
Neliswa Maphumulo
Nonhlanhla Ngobese
Yibanathi Ngcwangane
Bhekani Khumalo

📧 lwandile.ngid2@gmail.com
