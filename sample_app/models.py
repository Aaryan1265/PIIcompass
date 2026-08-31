"""SYNTHETIC sample models for the fictional MapleHealth portal.

Not a real system. These classes exist so PIICompass has realistic ORM-style
construction sites to trace. They intentionally mirror schema.sql.
"""


class Patient:
    def __init__(self, first_name=None, last_name=None, date_of_birth=None,
                 national_insurance_no=None, email=None, phone=None,
                 address_line1=None, postal_code=None, notes=None, city_id=None):
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.national_insurance_no = national_insurance_no
        self.email = email
        self.phone = phone
        self.address_line1 = address_line1
        self.postal_code = postal_code
        self.notes = notes
        self.city_id = city_id


class EmergencyContact:
    def __init__(self, patient_id=None, contact_name=None, contact_phone=None,
                 contact_type=None, relationship=None):
        self.patient_id = patient_id
        self.contact_name = contact_name
        self.contact_phone = contact_phone
        self.contact_type = contact_type
        self.relationship = relationship


class Payment:
    def __init__(self, patient_id=None, card_number=None, card_expiry=None,
                 amount_cents=None, currency=None):
        self.patient_id = patient_id
        self.card_number = card_number
        self.card_expiry = card_expiry
        self.amount_cents = amount_cents
        self.currency = currency


class HealthRecord:
    def __init__(self, patient_id=None, diagnosis_code=None, blood_type=None,
                 consent_flag=False):
        self.patient_id = patient_id
        self.diagnosis_code = diagnosis_code
        self.blood_type = blood_type
        self.consent_flag = consent_flag


class Appointment:
    def __init__(self, patient_id=None, scheduled_for=None, clinician_name=None):
        self.patient_id = patient_id
        self.scheduled_for = scheduled_for
        self.clinician_name = clinician_name
