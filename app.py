from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_  
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = "secretkey123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(25), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    dept_id = db.Column(db.Integer, db.ForeignKey('departments.dept_id'), nullable=True)
    experience = db.Column(db.Integer, nullable=True)
    qualifications = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)  
    blacklisted = db.Column(db.Boolean, default=False)

    department = db.relationship("Department", back_populates="doctors")

    patient_appointments = db.relationship(
        "Appointment",
        foreign_keys="Appointment.user_id",
        back_populates="patient"
    )

    doctor_appointments = db.relationship(
        "Appointment",
        foreign_keys="Appointment.doctor_id",
        back_populates="doctor"
    )


class Department(db.Model):
    __tablename__ = 'departments'
    dept_id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    doctors = db.relationship("User", back_populates="department")
class Treatment(db.Model):
    __tablename__ = "treatment"
    id = db.Column(db.Integer, primary_key=True)
    treat_name = db.Column(db.String(50))
    description = db.Column(db.Text)
    dept_id = db.Column(db.Integer, db.ForeignKey('departments.dept_id'), nullable=True)
    department = db.relationship('Department')
    appointment = db.relationship("Appointment", back_populates="treatment")
class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Booked')

    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))      
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))    
    treatment_id = db.Column(db.Integer, db.ForeignKey("treatment.id"))

    treatment = db.relationship("Treatment", back_populates="appointment")

    patient = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="patient_appointments"
    )
    doctor = db.relationship(
        "User",
        foreign_keys=[doctor_id],
        back_populates="doctor_appointments"
    )

class Availability(db.Model):
    __tablename__ = 'availability'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)         
    start_time = db.Column(db.String(20), nullable=False)   
    end_time = db.Column(db.String(20), nullable=False)      
    is_active = db.Column(db.Boolean, default=True)

    doctor = db.relationship('User')


@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == "POST":
        name = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(username=name, email=email).first()
        if user:
            flash("You are already registered. Please log in.", "warning")
            return redirect(url_for('login'))
        new_user = User(username=name, email=email, password=password, role="patient")
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('registration.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        name = request.form['fullname']
        password = request.form['password']
        user = User.query.filter_by(username=name, password=password).first()
        if user and user.blacklisted:
            flash("Your account has been blacklisted. Please contact the administrator.", "danger")
            return render_template('login.html')
        if user and user.role == "patient":
            session['name'] = user.username
            session['id'] = user.user_id 
            session['role'] = user.role
            flash("Login successful. Welcome to your dashboard.", "success")
            return redirect(url_for('patient_dashboard'))
        
        elif user and user.role == "doctor":
            session['name'] = user.username
            session['id'] = user.user_id 
            session['role'] = user.role
            flash("Login successful. Welcome doctor.", "success")
            return redirect(url_for('doctor_dashboard'))
        
        elif user and user.role == "admin":
            session['name'] = user.username
            session['id'] = user.user_id 
            session['role'] = user.role
            flash("Login successful. Welcome admin.", "success")
            return redirect(url_for('admin_dashboard'))
        flash("Invalid username or password.", "danger")
        return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/patient_dashboard', methods=['GET', 'POST'])
def patient_dashboard():
    if 'id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    patient_id = session['id']
    appointments = Appointment.query.filter_by(user_id=patient_id).filter(Appointment.status != 'Cancelled').all()
    departments = Department.query.all()
    return render_template('patient_dashboard.html', appointments=appointments, departments=departments)

@app.route('/department/<int:dept_id>')
def department_detail(dept_id):
    dept = Department.query.get_or_404(dept_id)
    doctors = User.query.filter_by(role='doctor', dept_id=dept_id).all()
    return render_template('department_detail.html', department=dept, doctors=doctors)

@app.route('/patient/book_appointment', methods=['GET', 'POST'])
def book_appointment_step1():
    if 'id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    treatments = Treatment.query.all()

    if request.method == 'POST':
        treatment_id = request.form.get('treatment_id')
        if not treatment_id:
            flash("Please select a treatment.", "danger")
            return render_template('book_step1.html', treatments=treatments)

        return redirect(url_for('book_appointment_step2', treatment_id=int(treatment_id)))

    return render_template('book_step1.html', treatments=treatments)

@app.route('/patient/book_appointment/<int:treatment_id>/time', methods=['GET', 'POST'])
def book_appointment_step2(treatment_id):
    if 'id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    treatment = Treatment.query.get_or_404(treatment_id)

    if request.method == 'POST':
        sel_date = request.form.get('date')
        sel_time = request.form.get('time')

        if not sel_date or not sel_time:
            flash("Please choose both date and time.", "danger")
            return render_template(
                'book_step2.html',
                treatment=treatment,
                sel_date=sel_date,
                sel_time=sel_time
            )

        return redirect(url_for(
            'book_appointment_step3',
            treatment_id=treatment_id,
            date=sel_date,
            time=sel_time
        ))

    return render_template(
        'book_step2.html',
        treatment=treatment,
        sel_date=None,
        sel_time=None
    )

@app.route('/patient/book_appointment/<int:treatment_id>/doctors')
def book_appointment_step3(treatment_id):
    if 'id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    treatment = Treatment.query.get_or_404(treatment_id)
    dept_id = treatment.dept_id
    sel_date = request.args.get('date')
    sel_time = request.args.get('time')

    if not sel_date or not sel_time:
        flash("Please choose date and time first.", "danger")
        return redirect(url_for('book_appointment_step2', treatment_id=treatment_id))

    q_avail = (
        db.session.query(User)
        .join(Availability, Availability.doctor_id == User.user_id)
        .filter(
            User.role == 'doctor',
            User.dept_id == dept_id,
            Availability.date == sel_date,
            Availability.start_time <= sel_time,
            Availability.end_time >= sel_time,
            Availability.is_active == True
        )
    )

    busy_ids = [
        a.doctor_id for a in Appointment.query.filter_by(
            date=sel_date, time=sel_time, status='Booked'
        ).all()
    ]
    if busy_ids:
        q_avail = q_avail.filter(~User.user_id.in_(busy_ids))
    doctors = q_avail.all()

    return render_template(
        'book_step3.html',
        treatment=treatment,
        doctors=doctors,
        sel_date=sel_date,
        sel_time=sel_time
    )

@app.route('/patient/confirm_appointment', methods=['POST'])
def confirm_appointment():
    if 'id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    patient_id = session['id']
    treatment_id = int(request.form.get('treatment_id'))
    doctor_id = int(request.form.get('doctor_id'))
    date = request.form.get('date')
    time = request.form.get('time')

    appt = Appointment(
        date=date,
        time=time,
        user_id=patient_id,
        doctor_id=doctor_id,
        treatment_id=treatment_id,
        status='Booked'
    )
    db.session.add(appt)
    db.session.commit()
    flash("Appointment booked successfully.", "success")
    return redirect(url_for('patient_dashboard'))



@app.route('/patient/appointments/<int:appt_id>/cancel', methods=['POST'])
def cancel_appointment(appt_id):
    if 'id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    appt = Appointment.query.get_or_404(appt_id)
    if appt.user_id != session['id']:
        return redirect(url_for('patient_dashboard'))

    db.session.delete(appt)
    db.session.commit()
    flash("Appointment cancelled.", "success")
    return redirect(url_for('patient_dashboard'))

@app.route('/patient/profile', methods=['GET', 'POST'])
def patient_profile():
    if 'id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    user = User.query.get_or_404(session['id'])

    if request.method == "POST":
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        new_password = request.form.get('password')
        if new_password:
            user.password = new_password  

        db.session.commit()
        session['name'] = user.username
        flash("Profile updated successfully.", "success")
        return redirect(url_for('patient_dashboard'))

    return render_template('patient_profile.html', user=user)

@app.route('/patient/history')
def patient_history():
    if 'id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    patient_id = session['id']
    appointments = Appointment.query.filter_by(user_id=patient_id).all()

    return render_template('patient_history.html', appointments=appointments, hide_history_link=True)

@app.route('/patient/ai_advice', methods=['GET', 'POST'])
def patient_ai_advice():
    if 'id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    departments = Department.query.all()
    recommended_doctors = []
    selected_dept = None
    patient_text = ""

    if request.method == 'POST':
        dept_id = request.form.get('dept_id')
        patient_text = request.form.get('needs') or ""
        if not dept_id:
            flash("Please select a department.", "danger")
        else:
            selected_dept = Department.query.get(dept_id)

            docs = User.query.filter_by(role='doctor', dept_id=dept_id).all()

            if docs:
                corpus = []
                doc_ids = []
                for d in docs:
                    desc_parts = [
                        d.qualifications or "",
                        (str(d.experience) + " years experience") if d.experience else "",
                        d.description or ""
                    ]
                    corpus.append(" ".join(desc_parts))
                    doc_ids.append(d)

                corpus_with_patient = [patient_text] + corpus
                vectorizer = TfidfVectorizer(stop_words='english')
                tfidf = vectorizer.fit_transform(corpus_with_patient)

                sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
                scored = sorted(
                    zip(doc_ids, sims),
                    key=lambda x: x[1],
                    reverse=True
                )
                recommended_doctors = scored[:3]

    return render_template(
        'patient_ai_advice.html',
        departments=departments,
        recommended_doctors=recommended_doctors,
        selected_dept=selected_dept,
        patient_text=patient_text
    )

@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    doctor_id = session['id']
    upcoming_appointments = Appointment.query.all()

    patient_ids = {appt.user_id for appt in upcoming_appointments if appt.user_id}
    assigned_patients = User.query.filter(
        User.user_id.in_(patient_ids),
        User.role == 'patient'
    ).all()

    return render_template('doctor_dashboard.html', upcoming_appointments=upcoming_appointments, assigned_patients=assigned_patients)

@app.route('/doctor/patient/<int:patient_id>/history')
def doctor_patient_history(patient_id):
    if 'id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    patient = User.query.filter_by(user_id=patient_id, role='patient').first_or_404()
    appointments = Appointment.query.filter_by(user_id=patient_id).all()

    return render_template(
        'patient_history.html',
        appointments=appointments,
        hide_history_link=True,
        viewed_patient=patient
    )

@app.route('/doctor/profile/<int:doctor_id>')
def doctor_profile_public(doctor_id):
    doctor = User.query.filter_by(user_id=doctor_id, role='doctor').first_or_404()
    return render_template('doctor_profile.html', doctor=doctor)

@app.route('/doctor/availability', methods=['GET', 'POST'])
def doctor_availability():
    if 'id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    doctor_id = session['id']

    if request.method == 'POST':
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if not date or not start_time or not end_time:
            flash("Please choose date, start time, and end time.", "danger")
            return redirect(url_for('doctor_availability'))

        if end_time <= start_time:
            flash("End time must be later than start time.", "danger")
            return redirect(url_for('doctor_availability'))

        slot = Availability(
            doctor_id=doctor_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )
        db.session.add(slot)
        db.session.commit()
        flash("Your availability has been saved.", "success")
        return redirect(url_for('doctor_availability'))

    availabilities = Availability.query.filter_by(
        doctor_id=doctor_id, is_active=True
    ).order_by(Availability.date, Availability.start_time).all()

    return render_template('doctor_availability.html', availabilities=availabilities)

@app.route('/doctor/appointment/<int:appt_id>/edit', methods=['GET', 'POST'])
def edit_appointment(appt_id):
    if 'id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    appt = Appointment.query.get_or_404(appt_id)

    if request.method == 'POST':
        appt.date = request.form.get('date') or appt.date
        appt.time = request.form.get('time') or appt.time
        appt.status = request.form.get('status') or appt.status
        db.session.commit()
        flash("Appointment updated.", "success")
        return redirect(url_for('doctor_dashboard'))

    return render_template('edit_appointment.html', appt=appt)

@app.route('/doctor/appointments/<int:appt_id>/complete', methods=['POST'])
def mark_appointment_complete(appt_id):
    if 'id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    appt = Appointment.query.get_or_404(appt_id)
    appt.status = 'Completed'
    db.session.commit()
    flash("Appointment marked as completed.", "success")
    return redirect(url_for('doctor_dashboard'))   

@app.route('/doctor/appointments/<int:appt_id>/cancel', methods=['POST'])
def doctor_cancel_appointment(appt_id):
    if 'id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    appt = Appointment.query.get_or_404(appt_id)

    appt.status = 'Cancelled'
    db.session.commit()
    flash("Appointment cancelled.", "success")
    return redirect(url_for('doctor_dashboard'))


@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    doctors = User.query.filter_by(role='doctor').all()
    patients = User.query.filter_by(role='patient').all()
    appointments = Appointment.query.all()
    return render_template(
        'admin_dashboard.html', 
        doctors=doctors,
        patients=patients,
        appointments=appointments
    )

@app.route('/admin_dashboard/create_doctor', methods=['GET', 'POST'])
def create_doctor():
    departments = Department.query.all()

    if request.method == "POST":
        name = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        dept_id = request.form.get('dept_id')
        qualification = request.form.get('qualification')
        experience = request.form.get('experience')
        description = request.form.get('description')   

        new_doctor = User(
            username=name,
            email=email,
            password=password,
            role="doctor",
            dept_id=dept_id,
            qualifications=qualification,
            experience=experience or None,
            description=description
        )
        db.session.add(new_doctor)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('create_doctor.html', departments=departments)

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    departments = Department.query.all()

    if request.method == "POST":
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        new_password = request.form.get('password')
        if new_password:
            user.password = new_password

        user.dept_id = request.form.get('dept_id') or None
        user.qualifications = request.form.get('qualifications')
        user.experience = request.form.get('experience') or None
        user.description = request.form.get('description') 

        db.session.commit()
        flash("User updated successfully.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_user.html', user=user, departments=departments)

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/blacklist/<int:user_id>')
def blacklist_user(user_id):
    user = User.query.get_or_404(user_id)
    user.blacklisted = True
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/unblacklist/<int:user_id>')
def unblacklist_user(user_id):
    user = User.query.get_or_404(user_id)
    user.blacklisted = False
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/patient/<int:patient_id>/history')
def admin_patient_history(patient_id):
    if 'id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    patient = User.query.filter_by(user_id=patient_id, role='patient').first_or_404()
    appointments = Appointment.query.filter_by(user_id=patient_id).all()

    return render_template(
        'patient_history.html',
        appointments=appointments,
        hide_history_link=True,
        viewed_patient=patient
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if Department.query.count() == 0:
            db.session.add_all([
                Department(
                    dept_name="General Medicine",
                    description=(
                        "Handles common illnesses such as fever, cold, infections, and routine checkups. "
                        "At CareWell Hospital, the General Medicine team is known for accurate diagnosis and "
                        "personalised follow-up care, ensuring patients recover quickly and safely."
                    )
                ),
                Department(
                    dept_name="Cardiology",
                    description=(
                        "Specialises in heart-related conditions including hypertension, chest pain, and heart disease. "
                        "CareWell Hospital’s Cardiology unit combines modern diagnostics with experienced cardiologists, "
                        "making it a trusted centre for complex cardiac cases."
                    )
                ),
                Department(
                    dept_name="Neurology",
                    description=(
                        "Treats disorders of the brain, spinal cord, and nerves such as seizures, stroke, and migraines. "
                        "CareWell Hospital is recognised for prompt stroke management and comprehensive neuro-rehabilitation, "
                        "helping patients regain independence faster."
                    )
                ),
                Department(
                    dept_name="Orthopedics",
                    description=(
                        "Deals with bone, joint, and muscle problems such as fractures, sports injuries, and arthritis. "
                        "At CareWell Hospital, the Orthopedics team focuses on early mobilisation and evidence-based "
                        "treatment so patients return to normal activity as soon as possible."
                    )
                ),
                Department(
                    dept_name="Pediatrics",
                    description=(
                        "Provides medical care for infants, children, and adolescents. "
                        "CareWell Hospital’s child-friendly environment, vaccination programs, and 24×7 paediatric support "
                        "make it a safe choice for families."
                    )
                ),
                Department(
                    dept_name="Oncology",
                    description=(
                        "Focuses on the diagnosis and treatment of cancers and related conditions. "
                        "CareWell Hospital offers coordinated oncology care with tumour boards and supportive services, "
                        "so patients receive compassionate treatment at every stage of their journey."
                    )
                ),
                Department(
                    dept_name="Dermatology",
                    description=(
                        "Treats skin, hair, and nail disorders such as rashes, allergies, and chronic skin diseases. "
                        "At CareWell Hospital, Dermatology combines clinical expertise with modern procedures to give "
                        "patients safe and effective results."
                    )
                ),
                Department(
                    dept_name="Ophthalmology",
                    description=(
                        "Specialises in eye and vision problems, including cataracts, glaucoma, and refractive errors. "
                        "CareWell Hospital’s Ophthalmology team uses advanced diagnostics and surgical techniques to "
                        "protect and enhance patients’ vision."
                    )
                ),
            ])
            db.session.commit()

        gm = Department.query.filter_by(dept_name="General Medicine").first()
        card = Department.query.filter_by(dept_name="Cardiology").first()
        neuro = Department.query.filter_by(dept_name="Neurology").first()
        ortho = Department.query.filter_by(dept_name="Orthopedics").first()
        ped = Department.query.filter_by(dept_name="Pediatrics").first()
        onco = Department.query.filter_by(dept_name="Oncology").first()
        derm = Department.query.filter_by(dept_name="Dermatology").first()
        oph = Department.query.filter_by(dept_name="Ophthalmology").first()
        if Treatment.query.count() == 0:
            db.session.add_all([
                Treatment(
                    treat_name="General Checkup",
                    description="Routine health checkup for fever, cold, infections, and overall wellness.",
                    dept_id=gm.dept_id
                ),
                Treatment(
                    treat_name="Chronic Disease Follow-up",
                    description="Follow-up visit for diabetes, hypertension, thyroid and other long-term conditions.",
                    dept_id=gm.dept_id
                ),
                Treatment(
                    treat_name="Cardiology Consultation",
                    description="Evaluation of chest pain, palpitations, shortness of breath and other heart symptoms.",
                    dept_id=card.dept_id
                ),
                Treatment(
                    treat_name="ECG and Cardiac Risk Assessment",
                    description="Electrocardiogram and basic cardiac risk profiling for heart disease prevention.",
                    dept_id=card.dept_id
                ),
                Treatment(
                    treat_name="Neurology Consultation",
                    description="Assessment of headache, seizures, stroke, weakness and other nervous system problems.",
                    dept_id=neuro.dept_id
                ),
                Treatment(
                    treat_name="Stroke Follow-up Clinic",
                    description="Regular review and rehabilitation planning for patients recovering from stroke.",
                    dept_id=neuro.dept_id
                ),
                Treatment(
                    treat_name="Fracture and Injury Care",
                    description="Management of fractures, sprains, sports injuries and trauma to bones or joints.",
                    dept_id=ortho.dept_id
                ),
                Treatment(
                    treat_name="Joint Pain & Arthritis Clinic",
                    description="Evaluation and treatment of chronic joint pain, back pain and arthritis.",
                    dept_id=ortho.dept_id
                ),
                Treatment(
                    treat_name="Pediatric Consultation",
                    description="General consultation for infants, children and adolescents for common illnesses.",
                    dept_id=ped.dept_id
                ),
                Treatment(
                    treat_name="Vaccination & Growth Check",
                    description="Immunization, growth monitoring and developmental assessment for children.",
                    dept_id=ped.dept_id
                ),
                Treatment(
                    treat_name="Oncology Consultation",
                    description="Initial and follow-up consultation for patients with suspected or confirmed cancers.",
                    dept_id=onco.dept_id
                ),
                Treatment(
                    treat_name="Chemotherapy Session",
                    description="Day-care administration and monitoring of chemotherapy as per oncologist’s plan.",
                    dept_id=onco.dept_id
                ),
                Treatment(
                    treat_name="Dermatology Consultation",
                    description="Evaluation of rashes, allergies, acne, infections and other skin, hair, or nail issues.",
                    dept_id=derm.dept_id
                ),
                Treatment(
                    treat_name="Skin Procedure / Minor Surgery",
                    description="Minor dermatological procedures such as mole removal, biopsy or cauterization.",
                    dept_id=derm.dept_id
                ),
                Treatment(
                    treat_name="Eye & Vision Checkup",
                    description="Comprehensive evaluation of vision, refraction and common eye complaints.",
                    dept_id=oph.dept_id
                ),
                Treatment(
                    treat_name="Cataract / Eye Surgery Evaluation",
                    description="Pre-surgical assessment and counselling for cataract or other eye surgeries.",
                    dept_id=oph.dept_id
                ),
            ])
            db.session.commit()

        existing_admin = User.query.filter_by(username="admin").first()
        if not existing_admin:
            admin_db = User(
                username="admin",
                password="admin4321",
                email="adm@gmail.com",
                role="admin"
            )
            db.session.add(admin_db)
            db.session.commit()

    app.run(debug=True)