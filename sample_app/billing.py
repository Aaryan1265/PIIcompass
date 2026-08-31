"""SYNTHETIC billing flow for the fictional MapleHealth portal.

Parsed, never executed. Shows card data leaving to a US payment processor and a
receipt leaving to a US email vendor, both of which are cross-border transfers
from an EU controller's point of view.
"""
from models import Payment


def charge_patient(payload):
    """Take payment and email a receipt."""
    # Card data sent to the payment processor (third country: US).
    charge = stripe_client.charge(
        card_number=payload.card_number,
        card_expiry=payload.card_expiry,
        amount=payload.amount_cents,
    )

    payment = Payment(
        patient_id=payload.patient_id,
        card_number=payload.card_number,
        card_expiry=payload.card_expiry,
        amount_cents=payload.amount_cents,
        currency=payload.currency,
    )
    db.add(payment)

    # Receipt emailed via a US email vendor (third country: US).
    sendgrid_client.send(payload.email, "Your receipt")
    return charge
