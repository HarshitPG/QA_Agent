# Concert Booking — Feature Rules (concert_rules.md)

1. Ticket types:

   - "General" (GEN): no seat assignment
   - "Reserved" (RES): seat assigned by row and seat number
   - "VIP" (VIP): includes backstage pass flag

2. Quantity rules:

   - Max tickets per booking = 6 for GEN, 4 for RES, 2 for VIP.
   - If user attempts to add more than allowed, the system must show inline validation: "Maximum X tickets allowed per booking."

3. Discount codes:

   - SAVE10 — 10% off the total (applies to subtotal before fees).
   - FREETIER — waives the 'service_fee' only for GEN tickets.
   - VIPUP — when combined with a VIP ticket, gives complimentary merchandise (no price change).
   - All discount codes expire at a documented date; unknown codes must return 400 from `POST /apply_coupon` with message "Invalid or expired coupon".

4. Fees:

   - Service fee = $2 per ticket (applies to all ticket types unless waived).
   - Processing fee = 3% of subtotal (applies to card payments).

5. Payment:

   - Supported payment methods: CreditCard, PayPal.
   - CreditCard requires card number (16 digits), expiry (MM/YY), CVV (3 digits).
   - On payment success show "Booking Confirmed!" with booking reference.
   - On payment failure show inline error "Payment failed: <reason>".

6. Seat selection:

   - Reserved tickets require selecting an available seat.
   - Seat availability must be checked in real-time via `GET /seats?event_id=<id>`.

7. Form validation:

   - Name: required, min 2 characters.
   - Email: must contain '@' and a valid domain.
   - Phone: optional, if supplied must be 10 digits.
   - Terms & Conditions checkbox: required to enable Submit.

8. Concurrency:

   - Seat reservations are optimistic: selection holds for 5 minutes; if hold expires, seat becomes available again.

9. Accessibility:

   - All input controls must have accessible labels and error messages should use `aria-live="polite"`.

10. Logging & Source grounding:

- All generated test cases must include `Grounded_In: <document>` pointing to `concert_rules.md`, `ui_guidelines.txt`, or `api_schema.json`.
