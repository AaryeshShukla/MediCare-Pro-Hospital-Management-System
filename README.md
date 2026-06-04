# 🏥 MediCare Pro — Hospital Management System

A full-stack Hospital Management System with role-based dashboards for Admins, Doctors, and Patients. Built with **Flask** (Python) on the backend and **Vue 3** + **Bootstrap 5** on the frontend.

---

## ✨ Features

### 👨‍💼 Admin Dashboard
- View real-time system statistics (doctors, patients, appointments)
- Add and remove physicians
- Browse the full patient registry
- Monitor all appointments across the system

### 👨‍⚕️ Doctor Portal
- View scheduled appointments with status badges
- Mark appointments as completed or cancelled
- Manage daily/weekly availability schedule
- Add diagnosis, prescription, and treatment notes
- Browse assigned patients

### 🧑‍⚕️ Patient Portal
- Self-registration and secure login
- Browse medical departments and available physicians
- Book, view, and cancel appointments
- View complete medical history and treatment records

---

## 🛠 Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | Python 3, Flask, Flask-SQLAlchemy |
| Auth      | Flask-JWT-Extended (JWT tokens)   |
| Database  | SQLite (via SQLAlchemy ORM)       |
| Frontend  | Vue 3 (CDN), Bootstrap 5          |
| CORS      | Flask-Cors                        |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/MediCare-Pro-Hospital-Management-System.git
cd MediCare-Pro-Hospital-Management-System
```

### 2. Set up the backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

The server will start at **http://localhost:5000**.

> The database and default admin account are created automatically on first run.

### 3. Open the frontend

Open your browser and navigate to:

```
http://localhost:5000
```

---

## 🔐 Default Credentials

| Role  | Username | Password   |
|-------|----------|------------|
| Admin | `admin`  | `admin123` |

> **Important:** Change the default admin password and the `JWT_SECRET_KEY` in `app.py` before deploying to production.

---

## 📁 Project Structure

```
MediCare-Pro/
├── backend/
│   ├── app.py            # Flask application, routes, and API logic
│   ├── models.py         # SQLAlchemy database models
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── index.html        # Login & patient registration page
│   ├── admin.html        # Admin dashboard
│   ├── doctor.html       # Physician portal
│   ├── patient.html      # Patient portal
│   └── ex.js             # Shared frontend utilities
└── README.md
```

---

## 🗄️ Database Models

| Model       | Description                              |
|-------------|------------------------------------------|
| `User`      | Authentication (admin, doctor, patient)  |
| `Department`| Hospital departments                     |
| `Doctor`    | Physician profiles with availability     |
| `Patient`   | Patient profiles linked to users         |
| `Appointment`| Bookings between patients and doctors   |
| `Treatment` | Diagnosis, prescription, and notes       |

---

## 🔌 API Endpoints

| Method | Endpoint                        | Role    | Description                    |
|--------|---------------------------------|---------|--------------------------------|
| POST   | `/login`                        | All     | Authenticate and get JWT token |
| POST   | `/register_patient`             | Public  | Register a new patient         |
| GET    | `/admin/stats`                  | Admin   | System-wide statistics         |
| POST   | `/add_doctor`                   | Admin   | Add a new physician            |
| GET    | `/doctors`                      | Admin   | List all doctors               |
| GET    | `/patients`                     | Admin   | List all patients              |
| DELETE | `/doctor/<id>`                  | Admin   | Remove a doctor                |
| DELETE | `/patient/<id>`                 | Admin   | Remove a patient               |
| GET    | `/doctor/dashboard`             | Doctor  | Doctor's stats overview        |
| GET    | `/doctor/appointments`          | Doctor  | Doctor's appointment list      |
| GET    | `/doctor/patients`              | Doctor  | Doctor's assigned patients     |
| GET/POST | `/doctor/availability`        | Doctor  | Get or set schedule            |
| POST   | `/appointment/<id>/complete`    | Doctor  | Mark appointment complete      |
| POST   | `/appointment/<id>/cancel`      | Doctor  | Cancel an appointment          |
| POST   | `/treatment`                    | Doctor  | Add treatment record           |
| GET    | `/patient/dashboard`            | Patient | Patient stats overview         |
| GET    | `/patient/appointments`         | Patient | Patient's appointments         |
| GET    | `/patient/history`              | Patient | Patient's medical history      |
| POST   | `/appointment`                  | Patient | Book a new appointment         |
| GET    | `/public/doctors`               | Public  | Browse available doctors       |
| GET    | `/departments`                  | Public  | List all departments           |

---

## ⚙️ Configuration

For production, update the following in `backend/app.py`:

```python
app.config['JWT_SECRET_KEY'] = 'your-strong-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@host/dbname'
```

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
