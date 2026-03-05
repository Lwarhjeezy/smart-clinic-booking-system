import os
import uvicorn
import bcrypt
import templates
from fastapi import FastAPI, HTTPException, Request, Depends, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi import Form
import mysql.connector
from datetime import date, time, datetime, timedelta
from typing import List, Optional
from starlette.middleware.sessions import SessionMiddleware
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from dotenv import load_dotenv


app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="a-secure-secret-key-that-should-be-in-env-vars")


app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables for SMTP
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# data validation
class LoginRequest(BaseModel):
    username: str
    password: str

class AppointmentRequest(BaseModel):
    service_type: str
    appointment_date: str
    appointment_time: str
    reason: str
    full_name: str
    student_number: str

class Appointment(BaseModel):
    appointment_id: int
    full_name: str
    student_number: str
    service_type: str
    appointment_date: date
    appointment_time: time
    reason: str
    staff_name: str
    status: str


def format_appointments(appointments):
    formatted_list = []
    for appt in appointments:
        formatted_appt = dict(appt)
        if isinstance(appt['appointment_date'], date):
            formatted_appt['formatted_date'] = appt['appointment_date'].strftime('%Y-%m-%d')
        else:
            formatted_appt['formatted_date'] = ""
        
        
        if isinstance(appt['appointment_time'], time):
            formatted_appt['formatted_time'] = appt['appointment_time'].strftime('%I:%M %p')
        elif isinstance(appt['appointment_time'], timedelta):
           
            total_seconds = int(appt['appointment_time'].total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_appt['formatted_time'] = f"{hours:02d}:{minutes:02d}"
        else:
            formatted_appt['formatted_time'] = ""
            
        formatted_list.append(formatted_appt)
    return formatted_list

# Database connection
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="@Lwandile1",
        database="clinic_booking_system2"
    )

def send_email(to_email: str, subject: str, message: str):
    """Send plain text email via Outlook SMTP."""
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")

#--- Authentication + Routing ---

@app.get("/", response_class=HTMLResponse)
def get_login_page(request: Request):
    return templates.TemplateResponse("loginpage.html", {"request": request})

import bcrypt  

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Check for admin 
        cursor.execute("SELECT * FROM admintb WHERE username = %s AND user_password = %s", (username, password))
        admin = cursor.fetchone()
        if admin:
            print(" Admin login successful, session:", request.session)
            request.session["username"] = username
            request.session["role"] = "admin"
            return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

        # Check for student or staff 
        cursor.execute(
            "SELECT * FROM Users WHERE student_number = %s OR email = %s",
            (username, username)
        )
        user = cursor.fetchone()
        if user:
           
            stored_hash = user["password_hash"].strip()
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
                request.session["username"] = username
                request.session["role"] = user["role"]
                print(f" {user['role'].capitalize()} login successful for {username}")
                if user["role"] == "student":
                    return RedirectResponse(url="/student/home", status_code=status.HTTP_303_SEE_OTHER)
                elif user["role"] == "staff":
                    
                    return RedirectResponse(url="/staff/dashboard", status_code=status.HTTP_303_SEE_OTHER)
                else:
                    # Fallback for other roles
                    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
            else:
                print(f"Login failed: Invalid password for user {username}")
                return templates.TemplateResponse("loginpage.html", {"request": request, "error": "Invalid username or password"})
        else:
            print(f"Login failed: No user found for username {username}")
            return templates.TemplateResponse("loginpage.html", {"request": request, "error": "Invalid username or password"})
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cursor.close()
        db.close()


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

#--- Student Functionality ---

@app.get("/student/home", response_class=HTMLResponse)
async def student_home(request: Request):
    if not request.session.get("username") or request.session.get("role") != "student":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        username = request.session["username"]
        cursor.execute(
            "SELECT * FROM Users WHERE student_number = %s OR email = %s",
            (username, username)
        )
        user = cursor.fetchone()
        if not user:
            # redirect to login
            request.session.clear()
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
        return templates.TemplateResponse(
            "home_page.html",
            {
                "request": request,
                "user": user  
            }
        )
    finally:
        cursor.close()
        db.close()

@app.get("/student/dashboard", response_class=HTMLResponse)
async def student_dashboard(request: Request):
    if not request.session.get("username") or request.session.get("role") != "student":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        username = request.session["username"]
        
        cursor.execute("SELECT COUNT(*) as count FROM Appointment WHERE student_id = (SELECT user_id FROM Users WHERE student_number = %s OR email = %s)", (username, username))
        notification_count = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT * FROM Users WHERE student_number = %s OR email = %s",
            (username, username)
        )
        user = cursor.fetchone()
        if not user:
            # redirect to login
            request.session.clear()
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        cursor.execute(
            """
            SELECT 
                a.appointment_id, 
                u.full_name, 
                u.student_number, 
                a.service_type,  -- Assumes column added; if not, replace with a.reason AS service_type
                s.staff_name, 
                a.appointment_date, 
                a.appointment_time, 
                a.reason, 
                a.status
            FROM Appointment a
            JOIN Users u ON a.student_id = u.user_id
            JOIN Staff s ON a.staff_id = s.staff_id
            WHERE a.student_id = %s 
              AND a.appointment_date >= CURDATE()
            ORDER BY a.appointment_date ASC, a.appointment_time ASC
            """,
            (user['user_id'],)
        )
        appointments = cursor.fetchall()
        
        formatted_appointments = format_appointments(appointments)
        return templates.TemplateResponse(
            "studentdash.html",
            {
                "request": request,
                "user": user,  
                "upcoming_appointments": formatted_appointments,
                "notification_count": notification_count
            }
        )
    except mysql.connector.Error as db_err:
        print(f"Database error: {db_err}")
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

@app.get("/student/services", response_class=HTMLResponse)
async def student_services(request: Request):
    if not request.session.get("username") or request.session.get("role") != "student":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("service.html", {"request": request})

@app.get("/booking", response_class=HTMLResponse)
def get_booking_page(request: Request):
    """
    Renders the appointment booking page.
    """
    if not request.session.get("username") or request.session.get("role") != "student":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT service_name FROM service")
        services = cursor.fetchall()
        # Get appointment_date from query params (default to today if not provided)
        appointment_date = request.query_params.get("date")
        if not appointment_date:
            appointment_date = date.today().strftime("%Y-%m-%d")

        cursor.execute("SELECT appointment_time FROM Appointment WHERE appointment_date = %s AND status NOT IN ('Cancelled', 'Rejected')", (appointment_date,))
        rows = cursor.fetchall()
        def format_timedelta(td):
            if isinstance(td, timedelta):
                total_seconds = int(td.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return f"{hours:02d}:{minutes:02d}"
            return ""

        booked_slots = [format_timedelta(row["appointment_time"]) for row in rows]

        return templates.TemplateResponse(
            "booking.html",
            {
                "request": request,
                "booked_slots": booked_slots,
                "services": services,
                "selected_date": appointment_date
            }
        )
    finally:
        cursor.close()
        db.close()

@app.post("/book_appointment")
async def book_appointment(
    request: Request,
    service_type: str = Form(...),
    appointment_date: str = Form(...),
    appointment_time: str = Form(...)
):

    if not request.session.get("username") or request.session.get("role") != "student":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get student
        username = request.session["username"]
        cursor.execute(
            "SELECT user_id, full_name, student_number FROM Users WHERE student_number = %s OR email = %s",
            (username, username)
        )
        student = cursor.fetchone()
        
        if not student:
            cursor_services = db.cursor(dictionary=True)
            cursor_services.execute("SELECT service_name FROM service")
            services = cursor_services.fetchall()
            cursor_services.close()
            
            return templates.TemplateResponse(
                "booking.html", 
                {
                    "request": request, 
                    "error": "Student information not found. Please contact support.",
                    "services": services
                }
            )
        
        student_id, full_name, student_number = student
        
        # Check if the selected time slot is available
        cursor.execute(
            "SELECT COUNT(*) FROM Appointment WHERE appointment_date = %s AND appointment_time = %s AND status NOT IN ('Cancelled', 'Rejected')",
            (appointment_date, appointment_time)
        )
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            cursor_services = db.cursor(dictionary=True)
            cursor_services.execute("SELECT service_name FROM service")
            services = cursor_services.fetchall()
            cursor_services.close()
            
            return templates.TemplateResponse(
                'booking.html',
                {
                    "request": request,
                    "error": "Selected time slot is not available. Please choose another time.",
                    "services": services
                }
            )

        # Assign a staff member
        cursor.execute("SELECT staff_id FROM Staff LIMIT 1")
        staff = cursor.fetchone()
        if not staff:
            cursor_services = db.cursor(dictionary=True)
            cursor_services.execute("SELECT service_name FROM service")
            services = cursor_services.fetchall()
            cursor_services.close()
            
            return templates.TemplateResponse(
                "booking.html", 
                {
                    "request": request, 
                    "error": "No staff available at the moment. Please try again later.",
                    "services": services
                }
            )
        
        staff_id = staff[0]
        
        # Insert the appointment
        cursor.execute(
            "INSERT INTO Appointment (student_id, staff_id, service_type, appointment_date, appointment_time, status) VALUES (%s, %s, %s, %s, %s, 'pending')",
            (student_id, staff_id, service_type, appointment_date, appointment_time)
        )
        db.commit() 

        # start of addition for email functionality:
        # Construct student email
        student_email = f"{student_number}@stu.unizulu.ac.za"
        # Email content
        subject = "Clinic Appointment Confirmation"
        message = (
            f"Dear {full_name},\n\n"
            f"Your appointment has been successfully booked.\n\n"
            f"Details:\n"
            f"Date: {appointment_date}\n"
            f"Time: {appointment_time}\n"
            f"Service: {service_type}\n\n"
            f"Thank you for using the Smart Clinic Booking System."
        )
        send_email(student_email, subject, message)
        # end of addition for email functionality

        request.session["booking_success"] = True
        return RedirectResponse(url="/student/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        db.rollback()
        print(f"Error booking appointment: {str(e)}")
        
        # Get services 
        cursor_services = db.cursor(dictionary=True)
        cursor_services.execute("SELECT service_name FROM service")
        services = cursor_services.fetchall()
        cursor_services.close()
        
        return templates.TemplateResponse(
            "booking.html", 
            {
                "request": request, 
                "error": "An error occurred while booking your appointment. Please try again.",
                "services": services
            }
        )
    finally:
        cursor.close()
        db.close()
        
@app.get("/home_page", response_class=HTMLResponse)
def home_page(request: Request):
    if not request.session.get("username"):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    User = request.session.get("user")

    return templates.TemplateResponse("home_page.html", {"request": request, "User": User})

#--- Admin/Staff Functionality ---

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if not request.session.get("username") or request.session.get("role") != "admin":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        today = date.today()
        # Fetch today appointments
        cursor.execute(
            "SELECT appointment.*, Users.student_number FROM appointment JOIN Users ON appointment.student_id = Users.user_id WHERE appointment_date = %s ORDER BY appointment_time",
            (today,)
        )
        appointments = cursor.fetchall()

        # Fetch all appointments
        cursor.execute("SELECT appointment.*, Users.student_number FROM appointment JOIN Users ON appointment.student_id = Users.user_id ORDER BY appointment_date ASC, appointment_time ASC")
        all_appointments = cursor.fetchall()
        
        # Format the appointments for 
        formatted_today_appointments = format_appointments(appointments)
        formatted_all_appointments = format_appointments(all_appointments)
        
        # Calculate missing variables
        total_appointments = len(appointments)
        completed_appointments = len([appt for appt in appointments if getattr(appt, 'status', None) == 'completed'])
        current_date = today.strftime('%B %d, %Y')
        username = request.session.get('username', 'Admin')

        cursor.execute("SELECT COUNT(*) as count FROM appointment WHERE status = 'completed'")
        completed_appointments = cursor.fetchone().get("count", 0)
        
        cursor.execute("select COUNT(*) as today_count from appointment where appointment_date = %s", (today,))
        today_appointments = cursor.fetchone().get("today_count", 0)
        
        cursor.execute("SELECT * FROM Users")
        Users = cursor.fetchall()

        return templates.TemplateResponse(
            "adminpage.html",
            {
                "request": request,
                "completed_appointments": completed_appointments,
                "today_appointments": today_appointments,
                "appointment": formatted_today_appointments,
                "all_appointment": formatted_all_appointments,
                "session": request.session,
                "date": current_date,
                "total_appointments": total_appointments,
                "completed_appointments": completed_appointments,
                "username": username,
                "Users": Users
            }
        )
    finally:
        cursor.close()
        db.close()

@app.post("/cancel_appointment/{appointment_id}")
async def cancel_appointment(request: Request, appointment_id: int):
    if not request.session.get("username"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel appointments")
    
    user_role = request.session.get("role")
    db = get_db()
    cursor = db.cursor()
    try:
        # If student, only allow canceling their own appointment
        if user_role == "student":
            username = request.session["username"]
            
            # Get student user_id
            cursor2 = db.cursor(dictionary=True)
            cursor2.execute("SELECT user_id FROM Users WHERE student_number = %s OR email = %s", (username, username))
            student = cursor2.fetchone()
            cursor2.close()
            if not student:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student not found")
            # Only update if the appointment belongs to this student
            cursor.execute(
                "UPDATE appointment SET status = 'Cancelled' WHERE appointment_id = %s AND student_id = %s",
                (appointment_id, student["user_id"])
            )
            db.commit()
            '''
            #start of email functionality
            # Fetch appointment info for the email
            #cursor3 = db.cursor(dictionary=True)
            cursor2.execute("""
                SELECT service_type, appointment_date, appointment_time 
                FROM appointment 
                WHERE appointment_id = %s
            """, (appointment_id,))
            appointment = cursor2.fetchone()
            cursor2.close()

            if appointment:
                service_type = appointment["service_type"]
                appointment_date = appointment["appointment_date"]
                appointment_time = appointment["appointment_time"]

                # Determine student email
                student_email = student["email"] or f"{student['student_number']}@stu.unizulu.ac.za"

                # Email content
                subject = "Clinic Appointment Cancellation"
                message = (
                    f"Dear {student['full_name']},\n\n"
                    f"You appointment has been successfully cancelled.\n\n"
                    f"Details:\n"
                    f"Date: {appointment_date}\n"
                    f"Time: {appointment_time}\n"
                    f"Service: {service_type}\n\n"
                    f"If this was a mistake, please book again using the clinic booking system.\n\n"
                    f"Thank you,\nSmart Clinic Team"
                )

                send_email(student_email, subject, message)
                print(f"✅ Cancellation email sent to {student_email}")
            '''

            return {"message": "Appointment cancelled and confirmation email sent successfully"}
        # If admin, allow cancelling any appointment
        elif user_role == "admin":
            cursor.execute(
                "UPDATE appointment SET status = 'Rejected' WHERE appointment_id = %s",
                (appointment_id,)
            )
            db.commit()
            return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel appointments")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        cursor.close()
        db.close()

@app.get("/appointments", response_class=HTMLResponse, name="view_all_appointments")
async def view_appointments(request: Request, nurse: Optional[str] = None, status_filter: Optional[str] = None):
    
    if not request.session.get("username") or request.session.get("role") != "admin":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        query = "SELECT * FROM appointment WHERE 1=1"
        params = []
        
        if nurse and nurse != "All":
            query += " AND staff_name = %s"
            params.append(nurse)
        
        if status_filter and status_filter != "All":
            query += " AND status = %s"
            params.append(status_filter)
            
        query += " ORDER BY appointment_date DESC, appointment_time DESC"
        
        cursor.execute(query, params)
        appointments = cursor.fetchall()
        

        formatted_appointments = format_appointments(appointments)
        
        return templates.TemplateResponse(
            "adminpage.html",
            {
                "request": request,
                "appointment": [],  
                "all_appointment": formatted_appointments
            }
        )
    finally:
        cursor.close()
        db.close()

@app.post("/update_status/{appointment_id}")
async def update_appointment_status(request: Request, appointment_id: int, status_update: str = Form(..., alias="status")):
    """
    Allows a staff member to update the status of an appointment.
    """
    if not request.session.get("username") or request.session.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update status")
        
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "UPDATE appointment SET status = %s WHERE appointment_id = %s",
            (status_update.lower(), appointment_id)
        )
        db.commit()

        #start of email functionality
        cursor.execute("""
            SELECT u.full_name, u.student_number, u.email, a.service_type, a.appointment_date, a.appointment_time
            FROM Appointment a
            JOIN Users u ON a.student_id = u.user_id
            WHERE a.appointment_id = %s
        """, (appointment_id,))
        appointment_info = cursor.fetchone()

        if appointment_info:
            full_name = appointment_info["full_name"]
            student_number = appointment_info["student_number"]
            student_email = appointment_info["email"] or f"{student_number}@stu.unizulu.ac.za"
            service_type = appointment_info["service_type"]
            appointment_date = appointment_info["appointment_date"]
            appointment_time = appointment_info["appointment_time"]

            # Compose the email message
            subject = f"Clinic Appointment Status Update: {status_update.capitalize()}"
            message = (
                f"Dear {full_name},\n\n"
                f"The status of your appointment has been updated to {status_update.capitalize()}.\n\n"
                f"Details:\n"
                f"Date: {appointment_date}\n"
                f"Time: {appointment_time}\n"
                f"Service: {service_type}\n\n"
                f"Thank you for using the Smart Clinic Booking System."
            )

            # Send the email notification
            send_email(student_email, subject, message)
            print(f"✅ Status update email sent to {student_email}")

        return {"message": "Status updated successfully and notification email sent!"}
        
    except Exception as e:
        db.rollback()
        print(f"Error updating status or sending email: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        cursor.close()
        db.close()
        
@app.post("/add-service")
async def add_service_post(request: Request, service_name: str = Form(...)):
    if not request.session.get("username") or request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO service (service_name) VALUES (%s)", (service_name,))
        db.commit()
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()
        
@app.get("/add-service", response_class=HTMLResponse, name="add_service_page")
async def add_service_page(request: Request):
    if not request.session.get("username") or request.session.get("role") != "admin":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        
        cursor.execute("SELECT service_name FROM Service")
        services = cursor.fetchall()
        
        return templates.TemplateResponse(
            "add_service.html",
            {
                "request": request,
                "services": services,
                "username": request.session.get('username', 'Admin')
            }
        )
    finally:
        cursor.close()
        db.close()
@app.post("/delete_service/{service_id}")
async def delete_service(request: Request, service_id: int):
    if not request.session.get("username") or request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM service WHERE service_id = %s", (service_id,))
        db.commit()
        return {"message": "Service deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()
        
# ...existing code...

# AJAX endpoint to get booked slots for a given date
from fastapi.responses import JSONResponse

@app.get("/get_booked_slots")
async def get_booked_slots(date: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT appointment_time FROM Appointment WHERE appointment_date = %s AND status NOT IN ('Cancelled', 'Rejected')", (date,))
        rows = cursor.fetchall()
        def format_timedelta(td):
            if isinstance(td, timedelta):
                total_seconds = int(td.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return f"{hours:02d}:{minutes:02d}"
            return str(td)
        booked_slots = [format_timedelta(row["appointment_time"]) for row in rows]
        return JSONResponse({"booked_slots": booked_slots})
    finally:
        cursor.close()
        db.close()

@app.get("/student/notification", response_class=HTMLResponse)
async def notification_page(request: Request):
    error = None
    booking_success = request.session.pop("booking_success", None)
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        username = request.session["username"]
        cursor.execute("SELECT user_id FROM Users WHERE student_number = %s OR email = %s", (username, username))
        user = cursor.fetchone()
        if not user:
            error = "Student not found."
            appointments = []
            notification_count = 0
        else:
            cursor.execute("""
                SELECT COUNT(*) as count FROM Appointment
                WHERE student_id = %s AND LOWER(status) = 'pending'
            """, (user["user_id"],))
            notification_count = cursor.fetchone()["count"]

            cursor.execute("""
                SELECT a.*, s.staff_name, u.student_number
                FROM Appointment a
                JOIN Staff s ON a.staff_id = s.staff_id
                JOIN Users u ON a.student_id = u.user_id
                WHERE a.student_id = %s
                ORDER BY a.appointment_date DESC, a.appointment_time DESC
            """, (user["user_id"],))
            appointments = cursor.fetchall()

        return templates.TemplateResponse(
            "notification.html",
            {
                "request": request,
                "appointments": appointments,
                "error": error,
                "booking_success": booking_success,
                "notification_count": notification_count
            }
        )
    finally:
        cursor.close()
        db.close()

#--- AI Symptom Checker Functionality ---
import os
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Tuple
from rapidfuzz import process
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, "NaiveBayes_model.pkl")
symptoms_path = os.path.join(BASE_DIR, "symptom_list.pkl")
encoder_path = os.path.join(BASE_DIR, "label_encoder.pkl")
triage_path = os.path.join(BASE_DIR, "triage_map.pkl")

# Load model, symptoms, triage, and encoder safely
try:
    model = joblib.load(model_path)
    symptoms = joblib.load(symptoms_path)
    label_encoder = joblib.load(encoder_path)
    triage_map = joblib.load(triage_path)

except FileNotFoundError:
    raise RuntimeError("Model, symptom list, label encoder or triage map not found! Check file paths.")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change to ["http://localhost:3000"] in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (POST, GET, etc.)
    allow_headers=["*"],  # Allow all headers
)


class SymptomRequest(BaseModel):
    user_symptoms: list

def normalize_symptoms(user_symptoms: List[str], official_symptoms: List[str]) -> Tuple[List[str], List[str]]:
    """
    Improved normalization using fuzzy matching:
    - Handles plural/singular forms (e.g., coughing → cough)
    - Handles minor typos (e.g., runny nose vs running nose)
    - Handles synonyms if they're close enough phonetically
    """

    normalized_symptoms = set()
    unmatched_symptoms = []

    for user_symptom in user_symptoms:
        processed_symptom = user_symptom.lower().strip().replace(" ", "_")

        # Step 1: Try direct match first
        if processed_symptom in official_symptoms:
            normalized_symptoms.add(processed_symptom)
            continue

        # Step 2: Fuzzy match using similarity scoring
        best_match, score, _ = process.extractOne(processed_symptom, official_symptoms)

        # If the similarity is above 80%, accept the match
        if score >= 80:
            normalized_symptoms.add(best_match)
        else:
            unmatched_symptoms.append(user_symptom)

    return list(normalized_symptoms), unmatched_symptoms

def predict_from_symptoms(user_symptoms):
    try:
        # Normalize the incoming symptoms to match the official symptom list
        cleaned_symptoms, unknown_symptoms = normalize_symptoms(user_symptoms, symptoms)

        # If no recognized symptoms are left after cleaning, we cannot predict.
        if not cleaned_symptoms:
            raise HTTPException(
                status_code=400,
                detail=f"Could not make a prediction. All provided symptoms were unrecognized: {', '.join(user_symptoms)}"
            )

        # Create a binary vector from the cleaned symptom list
        input_vector = [1 if s in cleaned_symptoms else 0 for s in symptoms]
        input_vector = np.array(input_vector).reshape(1, -1)

        # Ensure the input vector's dimensions match the model's expected features
        if input_vector.shape[1] != model.n_features_in_:
            raise HTTPException(
                status_code=400,
                detail=f"Feature mismatch: Model expects {model.n_features_in_} features, got {input_vector.shape[1]}"
            )

        # Get the numeric prediction from the model
        prediction_index = model.predict(input_vector)[0]

        # Map the numeric prediction back to the actual disease name
        predicted_disease = label_encoder.inverse_transform([prediction_index])[0]

        # Get the confidence score (probability) of the prediction
        probability = np.max(model.predict_proba(input_vector)) * 100
        
        # --- Integrated Triage Logic ---
        # Look up the triage level for the predicted disease from your triage map
        triage_code = triage_map.get(predicted_disease, None) # Default to None if not found
        triage_labels = {1: "Low. Your symptoms appear mild. Monitor your condition, use self-care, and book a routine appointment when convenient.",
                         2: "Moderate. Your symptoms may need medical attention. Please book a clinic visit as soon as possible.", 
                         3: "Urgent. Your symptoms may be serious. Seek immediate care — contact emergency medical services at 035 902 6599."
                         }
        triage_level = triage_labels.get(triage_code, "unclassified") # Default to 'unclassified'

        # Return all the results
        return predicted_disease, round(probability, 2), triage_level, unknown_symptoms

    except HTTPException:
        # Re-raise HTTP exceptions to be handled by FastAPI
        raise
    except Exception as e:
        # Handle any other unexpected errors during prediction
        print(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/predict")
def predict_endpoint(data: SymptomRequest):
    # Unpack the results from the prediction function
    prediction, probability,triage_level,unrecognized = predict_from_symptoms(data.user_symptoms)
    
    # Return a more informative response, including any symptoms that were ignored
    return {
        "predicted_disease": prediction,
        "confidence": f"{probability:.2f}%",
        "triage_level": triage_level,
        "unrecognized_symptoms": unrecognized
    }
        


@app.get("/student/home", response_class=HTMLResponse)
async def student_home(request: Request):
    if not request.session.get("username") or request.session.get("role") != "student":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("home_page.html", {"request": request})


@app.get("/symptoms")
def get_symptoms():
    return {"symptoms": symptoms}
    
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)