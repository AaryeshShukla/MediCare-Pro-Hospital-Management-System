from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from flask_cors import CORS
from models import db, User, Department, Doctor, Patient, Appointment, Treatment
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
# use instance path database for consistency and avoid locked file
db_file = os.path.join(app.instance_path, 'hms.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False, 'timeout': 30}
}
app.config['JWT_SECRET_KEY'] = 'super-secret'  # change in production

# utility to update schema in place

def ensure_schema():
    # make sure instance folder exists first
    os.makedirs(app.instance_path, exist_ok=True)
    db_path = os.path.join(app.instance_path, 'hms.db')
    if os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(doctor)")
            cols = [row[1] for row in cur.fetchall()]
            if 'name' not in cols:
                cur.execute("ALTER TABLE doctor ADD COLUMN name VARCHAR(100)")
                conn.commit()
                print('Added missing doctor.name column')
            conn.close()
        except Exception as e:
            print('schema update failed', e)
    # nothing to do if file doesn't exist; it will be created by SQLAlchemy

# run schema check before DB is initialized
ensure_schema()

db.init_app(app)
jwt = JWTManager(app)
CORS(app)


with app.app_context():
    ensure_schema()
    # instance folder created by ensure_schema already
    db.create_all()
    # Create admin if not exists
    if not User.query.filter_by(role='admin').first():
        admin = User(username='admin', password=generate_password_hash('admin123'), role='admin', email='admin@hms.com')
        db.session.add(admin)
        db.session.commit()
    # Create sample department if not exists
    if not Department.query.first():
        dept = Department(name='General Medicine', description='General medical care')
        db.session.add(dept)
        db.session.commit()

# ensure sessions are removed after each request
@app.teardown_appcontext

def shutdown_session(exception=None):
    db.session.remove()


# Routes

@app.route('/')
def index():
    return send_from_directory(os.path.join(app.root_path, '..', 'frontend'), 'index.html')

@app.route('/admin')
def admin_page():
    return send_from_directory(os.path.join(app.root_path, '..', 'frontend'), 'admin.html')

@app.route('/doctor')
def doctor_page():
    return send_from_directory(os.path.join(app.root_path, '..', 'frontend'), 'doctor.html')

@app.route('/patient')
def patient_page():
    return send_from_directory(os.path.join(app.root_path, '..', 'frontend'), 'patient.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
        return jsonify(access_token=access_token, role=user.role)
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/register_patient', methods=['POST'])
def register_patient():
    data = request.get_json() or {}
    username = str(data.get('username','')).strip()
    password = str(data.get('password','')).strip()
    email = str(data.get('email','')).strip()
    name = str(data.get('name','')).strip()
    contact = str(data.get('contact','')).strip()
    if not username or not password or not name:
        return jsonify({'message': 'username, password and name required'}), 400
    hashed_password = generate_password_hash(password)
    user = User(username=username, password=hashed_password, role='patient', email=email)
    db.session.add(user)
    db.session.commit()
    patient = Patient(user_id=user.id, name=name, contact=contact)
    db.session.add(patient)
    db.session.commit()
    return jsonify({'message': 'Patient registered'})

@app.route('/add_doctor', methods=['POST'])
@jwt_required()
def add_doctor():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    data = request.get_json() or {}
    # ensure string values
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()
    email = str(data.get('email', '')).strip()
    name = str(data.get('name', '')).strip()
    specialization = str(data.get('specialization', '')).strip()
    if not username or not password or not name:
        return jsonify({'message': 'username, password and name are required'}), 400
    hashed_password = generate_password_hash(password)
    user = User(username=username, password=hashed_password, role='doctor', email=email)
    db.session.add(user)
    db.session.commit()
    dept = Department.query.first()  # Use first department for simplicity
    doctor = Doctor(user_id=user.id, name=name, specialization=specialization, department_id=dept.id if dept else None)
    db.session.add(doctor)
    db.session.commit()
    return jsonify({'message': 'Doctor added'})

@app.route('/admin/stats', methods=['GET'])
@jwt_required()
def admin_stats():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    doctors = Doctor.query.count()
    patients = Patient.query.count()
    appointments = Appointment.query.count()
    return jsonify({'doctors': doctors, 'patients': patients, 'appointments': appointments})

@app.route('/doctor/dashboard', methods=['GET'])
@jwt_required()
def doctor_dashboard():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return jsonify({'message': 'Doctor not found'}), 404
    appointments = Appointment.query.filter_by(doctor_id=doctor.id, status='booked').count()
    patients_assigned = db.session.query(Appointment.patient_id).filter_by(doctor_id=doctor.id).distinct().count()
    return jsonify({'upcoming_appointments': appointments, 'patients_assigned': patients_assigned})

@app.route('/doctor/appointments', methods=['GET'])
@jwt_required()
def get_doctor_appointments():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return jsonify({'message': 'Doctor not found'}), 404
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
    result = []
    for a in appointments:
        patient = Patient.query.get(a.patient_id)
        result.append({
            'id': a.id,
            'patient_name': patient.name if patient else 'Unknown',
            'date': str(a.date),
            'time': str(a.time),
            'status': a.status
        })
    return jsonify(result)

@app.route('/doctor/patients', methods=['GET'])
@jwt_required()
def get_doctor_patients():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return jsonify({'message': 'Doctor not found'}), 404
    # Get unique patients assigned to this doctor
    patient_ids = db.session.query(Appointment.patient_id).filter_by(doctor_id=doctor.id).distinct().all()
    patients = []
    for (pid,) in patient_ids:
        patient = Patient.query.get(pid)
        if patient:
            patients.append({'id': patient.id, 'name': patient.name})
    return jsonify(patients)

@app.route('/patient/dashboard', methods=['GET'])
@jwt_required()
def patient_dashboard():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'patient':
        return jsonify({'message': 'Unauthorized'}), 403
    patient = Patient.query.filter_by(user_id=user_id).first()
    if not patient:
        return jsonify({'message': 'Patient not found'}), 404
    upcoming = Appointment.query.filter_by(patient_id=patient.id, status='booked').count()
    past = Appointment.query.filter_by(patient_id=patient.id, status='completed').count()
    return jsonify({'upcoming_appointments': upcoming, 'past_appointments': past})

@app.route('/departments', methods=['GET'])
def get_departments():
    depts = Department.query.all()
    return jsonify([{'id': d.id, 'name': d.name, 'description': d.description} for d in depts])

@app.route('/doctors', methods=['GET'])
@jwt_required()
def get_doctors():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    doctors = Doctor.query.all()
    return jsonify([{'id': d.id, 'name': d.name, 'specialization': d.specialization} for d in doctors])

@app.route('/patients', methods=['GET'])
@jwt_required()
def get_patients():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    patients = Patient.query.all()
    return jsonify([{'id': p.id, 'name': p.name or ''} for p in patients])

@app.route('/appointments', methods=['GET'])
@jwt_required()
def get_appointments():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    appointments = Appointment.query.all()
    result = []
    for a in appointments:
        patient = Patient.query.get(a.patient_id)
        doctor = Doctor.query.get(a.doctor_id)
        result.append({
            'id': a.id,
            'patient_name': patient.name if patient else '',
            'doctor_name': doctor.name if doctor else '',
            'date': str(a.date),
            'time': str(a.time),
            'status': a.status
        })
    return jsonify(result)

@app.route('/doctor/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_doctor(id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    doctor = Doctor.query.get(id)
    if doctor:
        user = User.query.get(doctor.user_id)
        db.session.delete(doctor)
        if user:
            db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'Doctor deleted'})
    return jsonify({'message': 'Doctor not found'}), 404

@app.route('/patient/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_patient(id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    patient = Patient.query.get(id)
    if patient:
        user = User.query.get(patient.user_id)
        db.session.delete(patient)
        if user:
            db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'Patient deleted'})
    return jsonify({'message': 'Patient not found'}), 404

@app.route('/appointment/<int:id>/complete', methods=['POST'])
@jwt_required()
def complete_appointment(id):
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return jsonify({'message': 'Doctor not found'}), 404
    appointment = Appointment.query.filter_by(id=id, doctor_id=doctor.id).first()
    if not appointment:
        return jsonify({'message': 'Appointment not found'}), 404
    appointment.status = 'completed'
    db.session.commit()
    return jsonify({'message': 'Appointment marked as completed'})

@app.route('/appointment/<int:id>/cancel', methods=['POST'])
@jwt_required()
def cancel_appointment(id):
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return jsonify({'message': 'Doctor not found'}), 404
    appointment = Appointment.query.filter_by(id=id, doctor_id=doctor.id).first()
    if not appointment:
        return jsonify({'message': 'Appointment not found'}), 404
    appointment.status = 'cancelled'
    db.session.commit()
    return jsonify({'message': 'Appointment cancelled'})

@app.route('/doctor/availability', methods=['GET'])
@jwt_required()
def get_doctor_availability():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return jsonify({'message': 'Doctor not found'}), 404
    
    # Return availability as JSON object
    import json
    availability = {}
    if doctor.availability:
        try:
            availability = json.loads(doctor.availability)
        except json.JSONDecodeError:
            availability = {}
    
    return jsonify(availability)

@app.route('/doctor/availability', methods=['POST'])
@jwt_required()
def set_doctor_availability():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return jsonify({'message': 'Doctor not found'}), 404
    
    # Store availability as JSON string
    import json
    doctor.availability = json.dumps(data)
    db.session.commit()
    
    return jsonify({'message': 'Availability set successfully'})

@app.route('/treatment', methods=['POST'])
@jwt_required()
def add_treatment():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
    data = request.get_json()
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return jsonify({'message': 'Doctor not found'}), 404
    treatment = Treatment(
        appointment_id=int(data.get('appointment_id', data.get('patient_id'))),  # Try appointment_id first, fallback to patient_id for compatibility
        diagnosis=data.get('diagnosis', ''),
        prescription=data.get('prescription', ''),
        notes=data.get('notes', ''),
    )
    db.session.add(treatment)
    db.session.commit()
    return jsonify({'message': 'Treatment record added'})

@app.route('/patient/appointments', methods=['GET'])
@jwt_required()
def get_patient_appointments():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'patient':
        return jsonify({'message': 'Unauthorized'}), 403
    patient = Patient.query.filter_by(user_id=user_id).first()
    if not patient:
        return jsonify({'message': 'Patient not found'}), 404
    appointments = Appointment.query.filter_by(patient_id=patient.id).all()
    result = []
    for a in appointments:
        doctor = Doctor.query.get(a.doctor_id)
        result.append({
            'id': a.id,
            'doctor_name': doctor.name if doctor else 'Unknown',
            'date': str(a.date),
            'time': str(a.time),
            'status': a.status
        })
    return jsonify(result)

@app.route('/patient/history', methods=['GET'])
@jwt_required()
def get_patient_history():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'patient':
        return jsonify({'message': 'Unauthorized'}), 403
    patient = Patient.query.filter_by(user_id=user_id).first()
    if not patient:
        return jsonify({'message': 'Patient not found'}), 404
    # Get treatments through appointments
    treatments = Treatment.query.join(Appointment).filter(Appointment.patient_id == patient.id).all()
    result = []
    for t in treatments:
        appointment = Appointment.query.get(t.appointment_id)
        doctor = Doctor.query.get(appointment.doctor_id) if appointment else None
        result.append({
            'id': t.id,
            'visit_no': t.id,  # Using ID as visit number for now
            'doctor_name': doctor.name if doctor else 'Unknown',
            'diagnosis': t.diagnosis,
            'prescription': t.prescription,
            'date': str(appointment.date) if appointment else str(t.id)
        })
    return jsonify(result)

@app.route('/public/doctors', methods=['GET'])
def get_public_doctors():
    doctors = Doctor.query.all()
    return jsonify([{'id': d.id, 'name': d.name, 'specialization': d.specialization} for d in doctors])

@app.route('/appointment', methods=['POST'])
@jwt_required()
def book_appointment():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'patient':
        return jsonify({'message': 'Unauthorized'}), 403
    data = request.get_json()
    patient = Patient.query.filter_by(user_id=user_id).first()
    if not patient:
        return jsonify({'message': 'Patient not found'}), 404
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=int(data.get('doctor_id')),
        date=datetime.strptime(data.get('date'), '%Y-%m-%d').date(),
        time=datetime.strptime(data.get('time'), '%H:%M').time(),
        status='booked'
    )
    db.session.add(appointment)
    db.session.commit()
    return jsonify({'message': 'Appointment booked successfully'})

@app.route('/appointment/<int:id>/cancel', methods=['POST'])
@jwt_required()
def cancel_patient_appointment(id):
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims.get('role') != 'patient':
        return jsonify({'message': 'Unauthorized'}), 403
    patient = Patient.query.filter_by(user_id=user_id).first()
    if not patient:
        return jsonify({'message': 'Patient not found'}), 404
    appointment = Appointment.query.filter_by(id=id, patient_id=patient.id).first()
    if not appointment:
        return jsonify({'message': 'Appointment not found'}), 404
    appointment.status = 'cancelled'
    db.session.commit()
    return jsonify({'message': 'Appointment cancelled'})

# Add more routes as needed

if __name__ == '__main__':
    app.run(debug=True)