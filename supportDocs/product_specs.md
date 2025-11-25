# E-Shop Checkout – Product Specifications

## 1. Product Catalog

### 1.1 Available Items

1. **Wireless Mouse**
   - ID: P001
   - Price: $25
2. **Mechanical Keyboard**
   - ID: P002
   - Price: $70
3. **USB-C Cable**
   - ID: P003
   - Price: $10

---

## 2. Shopping Cart Logic

### 2.1 Quantity Limits

- Minimum quantity per item: **1**
- Maximum quantity per item: **5**

### 2.2 Pricing

- Subtotal = Σ (item_price × quantity)
- Discount applies to subtotal only
- Shipping charges added after discount

---

## 3. Discount Code Rules

### 3.1 Valid Codes

| Code     | Description              | Discount         |
| -------- | ------------------------ | ---------------- |
| SAVE15   | Standard discount        | 15% off          |
| FREESHIP | Removes shipping charges | $0 shipping      |
| FLAT20   | Flat $20 off             | $20 off subtotal |

### 3.2 Invalid Conditions

- Expired codes: any code other than the above
- Code cannot be applied twice
- Only one coupon may be active at a time

---

## 4. Shipping Rules

### 4.1 Shipping Methods

- **Standard Shipping**: Free
- **Express Shipping**: $10

### 4.2 FREESHIP Coupon Interaction

- If FREESHIP is applied → shipping cost becomes $0

---

## 5. Payment Rules

### 5.1 Supported Methods

- Credit Card
- PayPal

### 5.2 Credit Card Validation

- Card number must be 16 digits
- CVV must be 3 digits
- Expiration date must be future date

---

## 6. Checkout Form Requirements

### Required fields:

- Name
- Email
- Address

### Email validation:

- Must contain "@"
- Must contain domain (e.g., ".com", ".net")

---

## 7. Success Conditions

Order is successful if:

- All mandatory fields are valid
- At least one product is in the cart
- A payment method is selected

Upon success:

- Display: **“Payment Successful!”**
