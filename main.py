from fastapi import FastAPI
from fastapi import UploadFile, File, Form, HTTPException
from database import get_db
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import io
import pandas as pd
from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader

load_dotenv()

# ── Cloudinary config (add these 3 keys to your .env) ──
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def upload_to_cloudinary(file_bytes: bytes, filename: str, folder: str) -> str:
    """Upload bytes to Cloudinary and return the secure URL."""
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        public_id=os.path.splitext(filename)[0],
        resource_type="auto",   # handles images, videos, PDFs
        overwrite=True
    )
    return result["secure_url"]

app = FastAPI()
origins = ["*"]
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
from pydantic import BaseModel

class ReportModel(BaseModel):

    school_id: int
    student_id: int
    student_name: str
    class_name: str
    subject: str
    mentor: str
    date: str
    attendance: int
    mark: int
    remarks: str

@app.get("/get-report-dates")
def get_report_dates(school_id: int, class_name: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    if class_name == "ALL":
        cursor.execute("""
            SELECT DISTINCT date
            FROM class_reports
            WHERE school_id=%s
            AND date IS NOT NULL
            ORDER BY date DESC
        """, (school_id,))
    else:
        cursor.execute("""
            SELECT DISTINCT date
            FROM class_reports
            WHERE school_id=%s
            AND class_name=%s
            AND date IS NOT NULL
            ORDER BY date DESC
        """, (school_id, class_name))
    rows = cursor.fetchall()
    dates = []
    for row in rows:
        if row["date"]:
            dates.append(str(row["date"]))
    return {
        "dates": dates
    }
@app.post("/submit-report")
def submit_report(report: ReportModel):
    db = get_db()
    cursor = db.cursor()
    query = """
    INSERT INTO class_reports
    (
        school_id,
        student_id,
        student_name,
        class_name,
        subject,
        mentor,
        date,
        attendance,
        mark,
        remarks
    )
    VALUES
    (
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
    )
    """
    values = (

        report.school_id,
        report.student_id,
        report.student_name,
        report.class_name,
        report.subject,
        report.mentor,
        report.date,
        report.attendance,
        report.mark,
        report.remarks
    )
    cursor.execute(query, values)
    db.commit()

    return {
        "message": "Report saved successfully"
    }
@app.post("/register")
def register(name:str,email:str,password:str,role:str):

    db = get_db()
    cursor = db.cursor()

    query = "INSERT INTO users (name,email,password,role) VALUES (%s,%s,%s,%s)"

    cursor.execute(query,(name,email,password,role))

    db.commit()

    return {"message":"User created"}



@app.post("/login")
def login(email:str,password:str):

    db = get_db()

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s",(email,))

    user = cursor.fetchone()

    if not user:
        return {"message":"User not found"}

    if user["password"] != password:
        return {"message":"Wrong password"}

    return {
        "message":"Login success",
        "role": user["role"]
    }    

@app.post("/create-school")
def create_school(school_name: str, location: str, board: str, username: str, password: str):
    
    db = get_db()
    cursor = db.cursor()

    query = """
    INSERT INTO schools (school_name, location, board, username, password)
    VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(query, (school_name, location, board, username, password))
    db.commit()

    school_id = cursor.lastrowid   # important line

    return {
        "message": "School created successfully",
        "school_id": school_id
    }


@app.post("/create-class")
def create_class(class_name: str, school_id: int):

    db = get_db()
    cursor = db.cursor()

    query = """
    INSERT INTO classes (class_name, school_id)
    VALUES (%s,%s)
    """

    cursor.execute(query, (class_name, school_id))
    db.commit()

    return {"message": "Class created"}

@app.post("/create-assignment")
def create_assignment(title:str, description:str, class_id:int, teacher_id:int):
    db = get_db()
    cursor = db.cursor()

    query = "INSERT INTO assignments (title,description,class_id,teacher_id) VALUES (%s,%s,%s,%s)"
    cursor.execute(query,(title,description,class_id,teacher_id))

    db.commit()

    return {"message":"Assignment created"}    


@app.post("/submit-assignment")
async def submit_assignment(assignment_id: int, student_id: int, file: UploadFile = File(...)):

    file_bytes = await file.read()
    file_url = upload_to_cloudinary(file_bytes, file.filename, folder="assignments")

    db = get_db()
    cursor = db.cursor()

    query = "INSERT INTO submission (assignment_id,student_id,file_path) VALUES (%s,%s,%s)"
    cursor.execute(query, (assignment_id, student_id, file_url))

    db.commit()

    return {"message": "Assignment submitted"}


@app.get("/assignments")
def get_assignments():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM assignments")

    data = cursor.fetchall()

    return data


@app.get("/submissions")
def get_submissions():
    

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM submissions")

    data = cursor.fetchall()

    return data


@app.post("/create-staff")
def create_staff(username:str,password:str,school_id:int=1):

    db = get_db()
    cursor = db.cursor()

    query = """
    INSERT INTO staff(username,password,school_id)
    VALUES(%s,%s,%s)
    """

    cursor.execute(query,(username,password,school_id))

    db.commit()

    return {"message":"Staff created successfully"}

@app.post("/create-student")
def create_student(name:str,email:str,password:str,class_id:int,school_id:int):

    db = get_db()
    cursor = db.cursor()

    query = "INSERT INTO users (name,email,password,role,school_id) VALUES (%s,%s,%s,'student',%s)"
    cursor.execute(query,(name,email,password,school_id))

    db.commit()

    return {"message":"Student created"}


@app.post("/mark-attendance")
def mark_attendance(
    student_id: int,
    class_name: str,
    status: str
):

    db = get_db()
    cursor = db.cursor()
    today = date.today()
    query = """
    INSERT INTO attendance
    (student_id, class_id, date, status)
    VALUES (%s, %s, %s, %s)
    """

    cursor.execute(
        query,
        (
            student_id,
            class_name,
            today,
            status
        )
    )

    db.commit()
    return {
        "message": "Attendance Marked"
    }


@app.post("/add-marks")
def add_marks(student_id:int,assignment_id:int,marks:int,remarks:str):

    db = get_db()
    cursor = db.cursor()

    query = "INSERT INTO marks (student_id,assignment_id,marks,remarks) VALUES (%s,%s,%s,%s)"
    cursor.execute(query,(student_id,assignment_id,marks,remarks))

    db.commit()

    return {"message":"Marks added"}


@app.get("/attendance-percentage/{student_id}")
def attendance_percentage(student_id:int):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM attendance WHERE student_id=%s",(student_id,))
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as present FROM attendance WHERE student_id=%s AND status='Present'",(student_id,))
    present = cursor.fetchone()["present"]

    percentage = (present/total)*100 if total > 0 else 0

    return {"attendance_percentage": percentage}


@app.get("/total-students")
def total_students():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='student'")

    data = cursor.fetchone()

    return data


@app.get("/total-staff")
def total_staff():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='staff'")

    data = cursor.fetchone()

    return data


@app.get("/total-assignments")
def total_assignments():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM assignments")

    data = cursor.fetchone()

    return data


@app.get("/total-schools")
def total_schools():

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM schools")

    data = cursor.fetchone()

    return data

@app.post("/school-login")
def school_login(username: str, password: str):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM schools WHERE username=%s AND password=%s",
        (username, password)
    )

    school = cursor.fetchone()

    if not school:
        return {"error": "Invalid login"}

    return {
        "school_id": school["id"],          # ✅ correct
        "school_name": school["username"]  # ✅ FIXED
    }

@app.get("/get-classes")
def get_classes(school_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    query = """
    SELECT DISTINCT class
    FROM students
    ORDER BY class
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    classes = []
    for row in rows:
        classes.append(row["class"])
    return {
        "classes": classes
    }



@app.post("/upload-students")
async def upload_students(file: UploadFile = File(...), school_id: int = Form(...)):

    # read uploaded file
    contents = await file.read()

    # read excel
    df = pd.read_excel(io.BytesIO(contents))

    db = get_db()
    cursor = db.cursor()

    for index, row in df.iterrows():

        # skip empty rows
        if pd.isna(row["first_name"]):
            continue

        first_name = row["first_name"]
        last_name = row["last_name"]
        student_class = row["class"]
        section = row["section"]

        query = """
        INSERT INTO students(first_name,last_name,class,section,school_id)
        VALUES(%s,%s,%s,%s,%s)
        """

        cursor.execute(query, (
            first_name,
            last_name,
            student_class,
            section,
            school_id
        ))

    db.commit()

    return {"message": "Students uploaded successfully"}


@app.get("/get-students")
def get_students(school_id: int, class_name: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    if class_name == "ALL":

        cursor.execute(
            "SELECT * FROM students WHERE school_id=%s",
            (school_id,)
        )
    else:
        cursor.execute(
            "SELECT * FROM students WHERE school_id=%s AND `class`=%s",
            (school_id, class_name)
        )
    students = cursor.fetchall()
    return {"students": students}



@app.get("/school/profile/{school_id}")
def get_profile(school_id: int):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT school_name, username FROM schools WHERE id=%s",
        (school_id,)
    )

    school = cursor.fetchone()

    db.close()

    return school   


@app.get("/get-report-dates")
def get_report_dates():

    db = get_db()

    cursor = db.cursor(dictionary=True)

    query = """
    SELECT DISTINCT date
    FROM attendance
    ORDER BY date DESC
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    dates = []
    for row in rows:
        dates.append(str(row["date"]))
    return {
        "dates": dates
    }
    
@app.get("/get-reports")
def get_reports(class_name: str, date: str):

    db = get_db()
    cursor = db.cursor(dictionary=True)
    if class_name == "ALL":

        query = """
        SELECT *
        FROM class_reports
        WHERE date=%s
        """

        cursor.execute(query, (date,))

    else:

        query = """
        SELECT *
        FROM class_reports
        WHERE class_name=%s
        AND date=%s
        """

        cursor.execute(query, (class_name, date))

    reports = cursor.fetchall()
    formatted_reports = []

    for r in reports:

        formatted_reports.append({
            "student": r["student_name"],
            "subject": r["subject"],
            "mentor": r["mentor"],
            "attendance": r["attendance"],
            "mark": r["mark"],
            "remarks": r["remarks"]
        })

    return {
        "reports": formatted_reports
    }

@app.post("/staff-login")
def staff_login(username: str, password: str):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = "SELECT * FROM staff WHERE username=%s AND password=%s"
    cursor.execute(query, (username, password))
    staff = cursor.fetchone()

    if not staff:
        return {"message": "Invalid login"}

    # ✅ School name எடுக்கணும்
    cursor.execute(
        "SELECT school_name FROM schools WHERE id=%s",
        (staff["school_id"],)
    )
    school = cursor.fetchone()

    return {
        "message"    : "Login success",
        "staff_id"   : staff["id"],
        "school_id"  : 1,
        "school_name": school["school_name"]  # ✅ இது add பண்ணு
    }


@app.post("/admin-login")
def admin_login(username:str,password:str):

    db=get_db()
    cursor=db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s AND role='admin'",(username,))
    user=cursor.fetchone()

    if not user or user["password"]!=password:
        raise HTTPException(status_code=401,detail="Invalid login")

    return {"message":"Login success","admin_id":user["id"]}


@app.get("/class-reports-summary")
def class_reports_summary(school_id:int,class_name:str,month:str):

    db=get_db()
    cursor=db.cursor(dictionary=True)

    cursor.execute("""
    SELECT s.first_name,
           c.subject,
           c.mentor,
           c.attendance,
           c.mark,
           c.remarks
    FROM class_reports c
    JOIN students s ON s.id=c.student_id
    WHERE c.school_id=%s
    AND c.class=%s
    AND c.month=%s
    """,(school_id,class_name,month))

    rows=cursor.fetchall()

    if not rows:
        return {
        "top_student":"-",
        "avg_mark":0,
        "avg_attendance":0,
        "total_students":0,
        "reports":[]
        }

    total_marks=sum(r["mark"] for r in rows)
    total_attendance=sum(r["attendance"] for r in rows)

    avg_mark=total_marks/len(rows)
    avg_attendance=total_attendance/len(rows)

    top_student=max(rows,key=lambda x:x["mark"])["first_name"]

    return{
    "top_student":top_student,
    "avg_mark":round(avg_mark,2),
    "avg_attendance":round(avg_attendance,2),
    "total_students":len(rows),
    "reports":rows
    }



from pydantic import BaseModel






class Report(BaseModel):
    student_id:int
    school_id:int
    class_name:str
    subject:str
    mentor:str
    attendance:int
    mark:int
    remarks:str
    month:str



from fastapi import FastAPI
from pydantic import BaseModel
from database import get_db



class Report(BaseModel):
    student_id:int
    school_id:int
    class_name:str
    subject:str
    mentor:str
    attendance:int
    mark:int
    remarks:str
    month:str

@app.get("/get-reports")
def get_reports(class_name:str, month:str):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT student_name as student,
               subject,
               mentor,
               attendance,
               mark,
               remarks
        FROM class_reports
        WHERE class_name=%s AND month=%s
    """,(class_name,month))

    data = cursor.fetchall()

    return {"reports":data}


@app.post("/upload-gallery")
async def upload_gallery(
    school_id: int = Form(...),
    class_name: str = Form(...),
    month: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        file_bytes = await file.read()
        file_url = upload_to_cloudinary(file_bytes, file.filename, folder="gallery")

        filename = file.filename.lower()
        if filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
            file_type = "image"
        elif filename.endswith(".mp4"):
            file_type = "video"
        elif filename.endswith((".pdf", ".doc", ".docx")):
            file_type = "document"
        else:
            file_type = "other"

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO gallery (school_id, class_name, month, file_path, file_type)
            VALUES (%s,%s,%s,%s,%s)
        """, (school_id, class_name, month, file_url, file_type))

        db.commit()

        return {"message": "File uploaded successfully"}

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return {"message": str(e)}
    

@app.get("/get-gallery")
def get_gallery(school_id: int, class_name: str, month: str):

   
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT file_path, file_type
        FROM gallery
        WHERE school_id=%s
        AND class_name=%s
        AND month=%s
    """, (school_id, class_name, month))

    data = cursor.fetchall()

    cursor.close()
    

    return data

@app.get("/all-students")
def all_students(school_id: int):

    db = get_db()

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM students WHERE school_id=%s",
        (school_id,)
    )

    students = cursor.fetchall()

    return {"students": students}



@app.post("/log-session")
def log_session(data: dict):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # get staff username
    cursor.execute(
        "SELECT username FROM staff WHERE id=%s",
        (data["staff_id"],)
    )

    staff = cursor.fetchone()

    staff_name = staff["username"]

    cursor.execute("""
        INSERT INTO session_logs
        (staff_id, staff_name, school_id, month, date, hours, topic)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """,(
        data["staff_id"],
        staff_name,
        data["school_id"],
        data["month"],
        data["date"],
        data["hours"],
        data["topic"]
    ))

    db.commit()

    return {"message":"Session logged successfully"}






@app.get("/get-session-attendance")
def get_session_attendance(school_id: int, month: str):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT staff_name,
        SUM(hours) AS total_hours,
        COUNT(*) AS sessions
        FROM session_logs
        WHERE school_id=%s AND month=%s
        GROUP BY staff_name
    """,(school_id,month))

    summary = cursor.fetchall()

    cursor.execute("""
        SELECT * FROM session_logs
        WHERE school_id=%s AND month=%s
        ORDER BY date DESC
    """,(school_id,month))

    logs = cursor.fetchall()

    return {
        "summary": summary,
        "logs": logs
    }

@app.get("/school-session")
def school_session(school_id: int, month: str):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Staff summary
    cursor.execute("""
        SELECT staff_name,
        SUM(hours) AS total_hours,
        COUNT(*) AS sessions
        FROM session_logs
        WHERE school_id=%s AND month=%s
        GROUP BY staff_name
    """,(school_id,month))

    summary = cursor.fetchall()

    # Session logs
    cursor.execute("""
        SELECT staff_name,date,hours,topic
        FROM session_logs
        WHERE school_id=%s AND month=%s
        ORDER BY date DESC
    """,(school_id,month))

    logs = cursor.fetchall()

    return {
        "summary": summary,
        "logs": logs
    }




import shutil
from fastapi import FastAPI, UploadFile, File, Form

import os



@app.post("/upload-lecture")
async def upload_lecture(
    school_id: int = Form(...),
    class_name: str = Form(...),
    subject: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    video: UploadFile = File(...)
):
    file_bytes = await video.read()
    file_url = upload_to_cloudinary(file_bytes, video.filename, folder="lectures")

    db = get_db()
    cursor = db.cursor()

    query = """
    INSERT INTO lectures
    (school_id, class_name, subject, title, description, video)
    VALUES (%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(query, (school_id, class_name, subject, title, description, file_url))
    db.commit()

    return {"message": "Lecture uploaded successfully"}

@app.get("/get-lectures")
def get_lectures(class_name: str, school_id: int):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    class_name = str(int(float(class_name)))

    cursor.execute("""
    SELECT * FROM lectures
    WHERE class_name=%s AND school_id=%s
    """, (class_name, school_id))

    data = cursor.fetchall()

    return data


@app.post("/student-login")
def student_login(
    student_id: int = Form(...),
    school_id: int = Form(...)
):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM students
        WHERE id=%s AND school_id=%s
    """,(student_id, school_id))

    student = cursor.fetchone()

    if not student:
        return {"message":"Student not found"}

    return {
        "message":"Login success",
        "student_id": student["id"],
        "name": student["first_name"],
        "class": student["class"],
        "school_id": student["school_id"]
    }




@app.post("/upload-book")
async def upload_book(
    school_id: int = Form(...),
    class_name: str = Form(...),
    subject: str = Form(...),
    title: str = Form(...),
    author: str = Form(""),
    file: UploadFile = File(...)
):
    file_bytes = await file.read()
    file_url = upload_to_cloudinary(file_bytes, file.filename, folder="books")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO books (school_id, class_name, subject, title, author, file_path)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (school_id, class_name, subject, title, author, file_url))

    db.commit()
    return {"message": "Book uploaded successfully"}


# Get books
@app.get("/get-books")
def get_books(school_id: int, class_name: str):

    db = get_db()
    cursor = db.cursor(dictionary=True)

    class_name = str(int(float(class_name)))

    cursor.execute("""
        SELECT * FROM books
        WHERE school_id=%s AND class_name=%s
    """, (school_id, class_name))

    return cursor.fetchall()



# ── CREATE TEST ──
@app.post("/create-test")
def create_test(data: dict):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO tests (school_id, class_name, subject, title, duration, created_by)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        data["school_id"],
        data["class_name"],
        data["subject"],
        data["title"],
        data["duration"],
        data["staff_id"]
    ))
    db.commit()
    test_id = cursor.lastrowid

    for q in data["questions"]:
        cursor.execute("""
            INSERT INTO test_questions
            (test_id, question, option_a, option_b, option_c, option_d, correct_answer)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            test_id,
            q["question"],
            q["option_a"],
            q["option_b"],
            q["option_c"],
            q["option_d"],
            q["correct_answer"]
        ))
    db.commit()

    return {"message": "Test created successfully", "test_id": test_id}


# ── GET TESTS ──
@app.get("/get-tests")
def get_tests(school_id: int, class_name: str):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    class_name = str(int(float(class_name)))
    cursor.execute("""
        SELECT * FROM tests
        WHERE school_id=%s AND class_name=%s
    """, (school_id, class_name))
    return cursor.fetchall()


# ── GET TEST QUESTIONS ──
@app.get("/get-test-questions")
def get_test_questions(test_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM test_questions WHERE test_id=%s", (test_id,)
    )
    return cursor.fetchall()


# ── SUBMIT TEST ──
@app.post("/submit-test")
def submit_test(data: dict):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO test_results (test_id, student_id, school_id, score, total)
        VALUES (%s,%s,%s,%s,%s)
    """, (
        data["test_id"],
        data["student_id"],
        data["school_id"],
        data["score"],
        data["total"]
    ))
    db.commit()
    return {"message": "Test submitted", "score": data["score"], "total": data["total"]}


# ── GET RESULTS ──
@app.get("/get-results")
def get_results(student_id: int, school_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT tr.*, t.title, t.subject
        FROM test_results tr
        JOIN tests t ON tr.test_id = t.id
        WHERE tr.student_id=%s AND tr.school_id=%s
        ORDER BY tr.submitted_at DESC
    """, (student_id, school_id))
    return cursor.fetchall()
