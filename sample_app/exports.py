"""SYNTHETIC export flow for the fictional MapleHealth portal.

Parsed, never executed. Writes patient identity and contact data to a CSV file,
a common exfiltration and retention blind spot.
"""
import csv


def export_patient_csv(patients, out_path):
    """Dump selected patient fields to a CSV file on disk."""
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["first_name", "last_name", "email", "national_insurance_no"])
        for patient in patients:
            writer.writerow([
                patient.first_name,
                patient.last_name,
                patient.email,
                patient.national_insurance_no,
            ])
