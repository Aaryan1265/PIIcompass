"""SYNTHETIC request handlers for the fictional MapleHealth portal.

These functions are never executed by PIICompass; they are parsed. Each handler
collects fields from an incoming request/payload and routes them to a data store
and, in some cases, to a third-party service. The names db, logger, request and
the vendor clients are intentionally left as free variables: the scanner reads
structure, not runtime behaviour.
"""
from models import Patient, EmergencyContact, HealthRecord, Appointment


def register_patient(payload, request):
    """Collect a new patient's details at sign-up."""
    patient = Patient(
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        national_insurance_no=payload.national_insurance_no,
        email=payload.email,
        phone=payload.phone,
        address_line1=payload.address_line1,
        postal_code=payload.postal_code,
        notes=payload.notes,
    )
    db.add(patient)

    # Operational log line that inadvertently includes names.
    logger.info("Registered patient %s %s", payload.first_name, payload.last_name)

    # Product analytics event sent to a third-party vendor.
    mixpanel_client.track("patient_registered", {
        "email": payload.email,
        "ip": request.ip_address,
    })
    return patient


def add_emergency_contact(payload):
    """Attach an emergency contact (a third party) to a patient."""
    contact = EmergencyContact(
        patient_id=payload.patient_id,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        contact_type=payload.contact_type,
        relationship=payload.relationship,
    )
    db.add(contact)
    return contact


def record_health(payload):
    """Store special-category health data for a patient (Article 9)."""
    record = HealthRecord(
        patient_id=payload.patient_id,
        diagnosis_code=payload.diagnosis_code,
        blood_type=payload.blood_type,
        consent_flag=payload.consent_flag,
    )
    db.add(record)
    return record


def book_appointment(payload):
    """Book an appointment and email a reminder via an EU email vendor."""
    appointment = Appointment(
        patient_id=payload.patient_id,
        scheduled_for=payload.scheduled_for,
        clinician_name=payload.clinician_name,
    )
    db.add(appointment)

    # Reminder email routed through an EU-resident processor (no transfer).
    mailjet_client.send(payload.email, "Appointment reminder")
    return appointment
