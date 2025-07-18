import pandas as pd
import os
import json
from datetime import datetime, timedelta

# Configurable start values
start_middleware_number = 68  # Change as needed
start_date = datetime(2025, 5, 30, 8, 11, 20)  # Starting InvoiceDate

# Read Excel
df = pd.read_excel('JSB LIGHTING DEC 24 INVOICES.xlsx')  # Change to your file name

# Ensure output directory exists
os.makedirs('exceltxt', exist_ok=True)

def round_decimal(value):
    try:
        return "{:.2f}".format(float(value))
    except ValueError:
        return value

for idx, row in df.iterrows():
    middleware_number = start_middleware_number + idx + 1
    relevant_invoice_number = str(row['INV NO.']).rstrip('/')

    invoice_date = start_date + timedelta(minutes=3 * idx)
    invoice_date_str = invoice_date.strftime('%Y-%m-%dT%H:%M:%S')

    json_data = {
        "TraderSystemInvoiceNumber": str(middleware_number),
        "MiddlewareInvoiceNumber": f"01705033400000000{middleware_number}",
        "RelevantInvoiceNumber": relevant_invoice_number,
        "QRCode": f"https://tims.kra.go.ke/01705033400000000{middleware_number}",
        "Discount": round_decimal("0.00"),
        "InvoiceType": "Original",
        "InvoiceCategory": "Credit Note",
        "InvoiceDate": invoice_date_str,
        "PINOfBuyer": str(row['PIN']),
        "ExemptionNumber": "",
        "TotalInvoiceAmount": round_decimal(str(row['AMOUNT(116)']).replace(',', '')),
        "TotalTaxableAmount": round_decimal(str(row['AMOUNT(100)']).replace(',', '')),
        "TotalTaxAmount": round_decimal(str(row['AMOUNT(16)']).replace(',', '')),
        "ItemDetails": [{
            "HSCode": "",
            "HSDesc": "DEP 1",
            "Category": "",
            "UnitPrice": round_decimal(str(row['AMOUNT(100)']).replace(',', '')),
            "Quantity": round_decimal("1.00"),
            "ItemAmount": round_decimal(str(row['AMOUNT(100)']).replace(',', '')),
            "TaxRate": round_decimal("16.00"),
            "TaxAmount": round_decimal(str(row['AMOUNT(16)']).replace(',', ''))
        }]
    }

    filename = f"exceltxt/{middleware_number}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        json_string = json.dumps(json_data, ensure_ascii=False, separators=(',', ':'))
        f.write(json_string + '\n')

print("Done! TXT files created in exceltxt folder.")