# Hospital Management System

Hospital Management System (HMS) is a Flask-based web application that enables admins, doctors, and patients to manage hospital operations including user management, appointment scheduling, and AI-powered doctor recommendations using NLP and TF-IDF techniques.

**Try it out:** https://danishshah07.pythonanywhere.com/

## Table of Contents
- [Features](#features)
- [Technologies](#technologies)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup)
- [How to Run](#how-to-run)
- [Credentials](#credentials)
- [Architecture](#database-schema)
- [Demo](#demo-video)
- [Author](#author)

## Features
- Role-based authentication for Admin, Doctor, and Patient users with secure password hashing and session management
- Admin dashboard: CRUD operations for doctors and patients, department management
- Doctor dashboard: View upcoming appointments, manage availability slots
- Patient dashboard: Book appointments with AI-recommended best doctors based on department descriptions
- Database schema supporting users, departments, treatments, appointments, and availability

## Technologies
| Technology | Library | Purpose |
|------------|---------|---------|
| Backend | Flask | Core web framework |
| Database | SQLite | Local data storage |
| ORM | SQLAlchemy | Database modeling |
| Templates | Jinja2 | Dynamic HTML rendering |
| AI | TF-IDF/NLP | Doctor recommendations |

## Prerequisites
- Python 3.8 or higher
- pip package manager
- Git (recommended for cloning)

## Setup
1. Clone or download the project files to your local machine
2. Open terminal and navigate to project directory: `cd hospital-management-system`
3. Create virtual environment: `python -m venv venv`
4. Activate virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
5. Install dependencies: `pip install flask sqlalchemy flask-sqlalchemy scikit-learn`

## How to Run
1. Ensure virtual environment is activated
2. Initialize database (first run auto-creates tables): `python app.py` (or similar main file)
3. Flask development server starts automatically
4. Open browser: `http://127.0.0.1:5000` or `http://localhost:5000`
5. Access login page and use provided credentials

## Credentials
### Admin Account
Username: admin
Password: admin4321

## Database Schema
- **User**: userid, username, email, password, role, deptid
- **Department**: deptid, deptname, description
- **Treatment**: id, treatname, description, deptid
- **Appointment**: id, date, time, status, userid, doctorid, treatmentid
- **Availability**: id, doctorid, date, starttime, endtime, isactive

## Demo Video
[Watch Demo](https://drive.google.com/file/d/19KtomNPQuEeJ3BmJnNNWtCWGmeAvDw3B/view?usp=sharing)

## Author
**Danish Shah**  
IIT Madras BS Data Science  
Roll: 23f3001327  
[Project Report](MAD1_Project_Report.pdf)

