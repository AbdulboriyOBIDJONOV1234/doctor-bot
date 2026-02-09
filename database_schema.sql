-- Neurology Bot Database Schema
-- PostgreSQL Database Setup

-- ===================================
-- PATIENTS TABLE
-- ===================================
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    age INTEGER NOT NULL CHECK (age > 0 AND age < 120),
    phone VARCHAR(20) NOT NULL,
    location VARCHAR(200),
    language VARCHAR(2) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- ===================================
-- APPOINTMENTS TABLE
-- ===================================
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
    complaint TEXT NOT NULL,
    urgency VARCHAR(20) DEFAULT 'ROUTINE' CHECK (urgency IN ('EMERGENCY', 'URGENT', 'ROUTINE')),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED', 'RESCHEDULED')),
    doctor_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reminder_24h_sent BOOLEAN DEFAULT FALSE,
    reminder_1h_sent BOOLEAN DEFAULT FALSE
);

-- ===================================
-- DOCTOR SCHEDULE TABLE
-- ===================================
CREATE TABLE doctor_schedule (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    time_slot TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    appointment_id INTEGER REFERENCES appointments(id) ON DELETE SET NULL,
    UNIQUE(date, time_slot)
);

-- ===================================
-- MEDICAL HISTORY TABLE
-- ===================================
CREATE TABLE medical_history (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
    appointment_id INTEGER REFERENCES appointments(id),
    diagnosis TEXT,
    prescription TEXT,
    notes TEXT,
    follow_up_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================================
-- NOTIFICATIONS TABLE
-- ===================================
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER REFERENCES appointments(id) ON DELETE CASCADE,
    notification_type VARCHAR(20) CHECK (notification_type IN ('REMINDER_24H', 'REMINDER_1H', 'CONFIRMATION', 'CANCELLATION', 'EMERGENCY')),
    sent_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SENT', 'FAILED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================================
-- EMERGENCY LOGS TABLE
-- ===================================
CREATE TABLE emergency_logs (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id),
    complaint TEXT NOT NULL,
    symptoms TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    doctor_contacted BOOLEAN DEFAULT FALSE,
    patient_contacted BOOLEAN DEFAULT FALSE
);

-- ===================================
-- ANALYTICS TABLE
-- ===================================
CREATE TABLE analytics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_registrations INTEGER DEFAULT 0,
    total_appointments INTEGER DEFAULT 0,
    emergency_cases INTEGER DEFAULT 0,
    completed_appointments INTEGER DEFAULT 0,
    cancelled_appointments INTEGER DEFAULT 0,
    peak_hour TIME,
    common_complaints TEXT[],
    UNIQUE(date)
);

-- ===================================
-- INDEXES FOR PERFORMANCE
-- ===================================
CREATE INDEX idx_patients_telegram ON patients(telegram_id);
CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_date ON appointments(appointment_date);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_schedule_date ON doctor_schedule(date);
CREATE INDEX idx_emergency_logs_date ON emergency_logs(created_at);

-- ===================================
-- TRIGGERS FOR UPDATED_AT
-- ===================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_patients_updated_at BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointments_updated_at BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===================================
-- SAMPLE DATA FOR TESTING
-- ===================================
-- Insert doctor's available time slots for next 7 days
DO $$
DECLARE
    current_date DATE := CURRENT_DATE + INTERVAL '1 day';
    end_date DATE := CURRENT_DATE + INTERVAL '7 days';
    time_slots TIME[] := ARRAY['09:00', '10:00', '11:00', '12:00', '14:00', '15:00', '16:00', '17:00'];
    time_slot TIME;
BEGIN
    WHILE current_date <= end_date LOOP
        FOREACH time_slot IN ARRAY time_slots LOOP
            INSERT INTO doctor_schedule (date, time_slot, is_available)
            VALUES (current_date, time_slot, TRUE);
        END LOOP;
        current_date := current_date + INTERVAL '1 day';
    END LOOP;
END $$;

-- ===================================
-- USEFUL QUERIES FOR DOCTOR DASHBOARD
-- ===================================

-- Get today's appointments
-- SELECT p.first_name, p.last_name, p.phone, a.appointment_time, a.urgency, a.complaint
-- FROM appointments a
-- JOIN patients p ON a.patient_id = p.id
-- WHERE a.appointment_date = CURRENT_DATE
-- ORDER BY a.appointment_time;

-- Get pending appointments
-- SELECT a.id, p.first_name, p.last_name, p.phone, a.appointment_date, a.appointment_time, a.urgency
-- FROM appointments a
-- JOIN patients p ON a.patient_id = p.id
-- WHERE a.status = 'PENDING'
-- ORDER BY a.urgency DESC, a.created_at ASC;

-- Get emergency cases
-- SELECT e.*, p.first_name, p.last_name, p.phone
-- FROM emergency_logs e
-- JOIN patients p ON e.patient_id = p.id
-- WHERE DATE(e.created_at) = CURRENT_DATE
-- ORDER BY e.created_at DESC;

-- Get patient history
-- SELECT a.appointment_date, a.complaint, m.diagnosis, m.prescription
-- FROM appointments a
-- LEFT JOIN medical_history m ON a.id = m.appointment_id
-- WHERE a.patient_id = ? -- Replace with patient_id
-- ORDER BY a.appointment_date DESC;

-- Get daily statistics
-- SELECT 
--     COUNT(*) as total_appointments,
--     SUM(CASE WHEN urgency = 'EMERGENCY' THEN 1 ELSE 0 END) as emergency_count,
--     SUM(CASE WHEN urgency = 'URGENT' THEN 1 ELSE 0 END) as urgent_count,
--     SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_count
-- FROM appointments
-- WHERE appointment_date = CURRENT_DATE;