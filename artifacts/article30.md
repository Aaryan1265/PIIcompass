# Record of processing activities (GDPR Article 30(1))

Status: DRAFT - auto-generated from a code and schema scan; requires human review

## (a) Controller

- Name: TO BE COMPLETED BY THE CONTROLLER / DPO
- Contact: TO BE COMPLETED BY THE CONTROLLER / DPO
- Data protection officer: TO BE COMPLETED BY THE CONTROLLER / DPO

## (b) Purposes of processing

- add_emergency_contact: Maintaining emergency contact details for patients. Data: contact, identity.
- book_appointment: Scheduling appointments and sending reminders. Data: contact, identity.
- charge_patient: Taking payment for services and issuing receipts. Data: contact, financial.
- export_patient_csv: Bulk export of patient records for reporting. Data: contact, government_id, identity.
- record_health: Recording and managing clinical and health information. Data: health. (includes special-category data)
- register_patient: Registration and administration of patient accounts. Data: contact, government_id, identity, online_identifier.
- track_pageview: Website and product analytics. Data: contact, online_identifier.

## (c) Categories of data subjects

- Clinical staff
- Emergency contacts (third parties)
- Patients
- Staff users
- Website visitors

## (c) Categories of personal data

- Contact: analytics_events.geo_region, audit_log.actor_email, contacts.contact_phone, patients.address_line1, patients.email, patients.phone, patients.postal_code
- Financial: payments.card_expiry, payments.card_number
- Government identifier: patients.national_insurance_no
- Health (special category) [SPECIAL CATEGORY, Article 9]: health_records.blood_type, health_records.diagnosis_code
- Identity: appointments.clinician_name, cities.city_name, contacts.contact_name, patients.date_of_birth, patients.first_name, patients.last_name
- Online identifier: analytics_events.device_id, analytics_events.ip_address, analytics_events.session_id, analytics_events.user_agent

## (d) Categories of recipients

- Mailjet (transactional email) (processor, France): contact
- Mixpanel (product analytics) (processor, United States): contact, online_identifier
- Stripe Payments (payment processor) (processor, United States): financial
- Twilio SendGrid (transactional email) (processor, United States): contact

## (e) Transfers to third countries

- Mixpanel (product analytics) (United States): safeguard = Standard Contractual Clauses; data = contact, online_identifier
- Stripe Payments (payment processor) (United States): safeguard = Standard Contractual Clauses; data = financial
- Twilio SendGrid (transactional email) (United States): safeguard = Standard Contractual Clauses; data = contact

## (f) Retention

- TO BE COMPLETED BY THE CONTROLLER / DPO
- Retention periods cannot be inferred from code and must be set per data category and legal basis.

## (g) Technical and organisational security measures

Access to personal data is restricted on a need-to-know basis. Data in transit is protected with TLS. Payment card data is handled by a PCI-DSS compliant processor and is not stored in clear text. Application activity is recorded in an audit log. These are baseline measures inferred from the codebase and must be reviewed and completed by the controller.
