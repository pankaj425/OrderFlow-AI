import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ------- TABLES -------

c.executescript("""
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS deliveries;
DROP TABLE IF EXISTS delivery_items;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS invoice_items;
DROP TABLE IF EXISTS journal_entries;
DROP TABLE IF EXISTS payments;

CREATE TABLE customers (
    businesspartner TEXT PRIMARY KEY,
    businesspartnername TEXT,
    customer TEXT,
    country TEXT,
    city TEXT
);

CREATE TABLE orders (
    salesorder TEXT PRIMARY KEY,
    salesordertype TEXT,
    soldtoparty TEXT,
    totalnetamount REAL,
    overalldeliverystatus TEXT,
    creationdate TEXT,
    currency TEXT
);

CREATE TABLE deliveries (
    deliverydocument TEXT PRIMARY KEY,
    creationdate TEXT,
    overallgoodsmovementstatus TEXT,
    shippingpoint TEXT
);

CREATE TABLE delivery_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deliverydocument TEXT,
    referencesddocument TEXT,
    deliveryitem TEXT,
    material TEXT,
    deliveredquantity REAL
);

CREATE TABLE invoices (
    billingdocument TEXT PRIMARY KEY,
    billingdocumenttype TEXT,
    soldtoparty TEXT,
    totalnetamount REAL,
    accountingdocument TEXT,
    billingdate TEXT,
    currency TEXT
);

CREATE TABLE invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    billingdocument TEXT,
    referencesddocument TEXT,
    billingitem TEXT,
    material TEXT,
    netamount REAL
);

CREATE TABLE journal_entries (
    accountingdocument TEXT PRIMARY KEY,
    referencedocument TEXT,
    amountintransactioncurrency REAL,
    accountingdocumenttype TEXT,
    companycode TEXT,
    fiscalyear TEXT,
    postingdate TEXT,
    documentdate TEXT,
    glaccount TEXT,
    customer TEXT,
    profitcenter TEXT,
    costcenter TEXT,
    transactioncurrency TEXT,
    amountincompanycodecurrency REAL,
    companycodecurrency TEXT,
    financialaccounttype TEXT
);

CREATE TABLE payments (
    accountingdocument TEXT PRIMARY KEY,
    invoicereference TEXT,
    amountintransactioncurrency REAL,
    salesdocument TEXT,
    paymentdate TEXT,
    paymentmethod TEXT
);
""")

# ------- CUSTOMERS -------
customer_data = [
    ("100001", "Acme Corporation", "C10001", "US", "New York"),
    ("100002", "Global Tech Ltd", "C10002", "DE", "Berlin"),
    ("100003", "SkyHigh Solutions", "C10003", "GB", "London"),
    ("100004", "Pacific Traders", "C10004", "JP", "Tokyo"),
    ("100005", "Euromart GmbH", "C10005", "FR", "Paris"),
    ("100006", "Sunrise Enterprises", "C10006", "IN", "Mumbai"),
    ("100007", "Delta Imports", "C10007", "AU", "Sydney"),
    ("100008", "Nordic Supplies", "C10008", "SE", "Stockholm"),
    ("100009", "Southern Cross Co", "C10009", "ZA", "Cape Town"),
    ("100010", "Apex Industries", "C10010", "CA", "Toronto"),
    ("100011", "BlueWave Systems", "C10011", "US", "Chicago"),
    ("100012", "RedBrick Ventures", "C10012", "BR", "Sao Paulo"),
    ("100013", "Summit Corp", "C10013", "MX", "Mexico City"),
    ("100014", "Horizon Trading", "C10014", "AE", "Dubai"),
    ("100015", "Crystal Tech", "C10015", "SG", "Singapore"),
]
c.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customer_data)

# ------- GENERATE ORDERS, DELIVERIES, INVOICES, JOURNALS, PAYMENTS -------
random.seed(42)

order_types = ["OR", "ZOR", "ZSTD", "RE"]
delivery_statuses = ["A", "B", "C"]
goods_movement_statuses = ["A", "B", "C"]
doc_types = ["RV", "DR", "DG"]
acct_doc_types = ["RV", "AB", "SA"]
currencies = ["USD", "EUR", "GBP", "JPY", "INR"]
company_codes = ["1000", "2000", "3000"]

# Fixed orders from pyc strings
fixed_orders = ["740550", "740566"]
all_order_ids = fixed_orders[:]
for i in range(1, 29):
    all_order_ids.append(str(740550 + i * 3 + random.randint(0, 2)))

all_order_ids = list(dict.fromkeys(all_order_ids))[:32]

base_date = datetime(2024, 1, 1)

inv_counter = 90000000
jnl_counter = 50000000
pay_counter = 70000000
del_counter = 80000000

for idx, order_id in enumerate(all_order_ids):
    party_bp = customer_data[idx % len(customer_data)][0]
    amount = round(random.uniform(5000, 250000), 2)
    currency = currencies[idx % len(currencies)]
    order_date = (base_date + timedelta(days=idx * 7)).strftime("%Y-%m-%d")
    del_status = delivery_statuses[idx % 3]

    c.execute("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?)", (
        order_id, order_types[idx % 4], party_bp,
        amount, del_status, order_date, currency
    ))

    # Delivery
    del_id = str(del_counter + idx)
    del_date = (base_date + timedelta(days=idx * 7 + 3)).strftime("%Y-%m-%d")
    gm_status = goods_movement_statuses[idx % 3]
    c.execute("INSERT OR IGNORE INTO deliveries VALUES (?,?,?,?)", (
        del_id, del_date, gm_status, f"SP0{(idx % 3) + 1}"
    ))
    c.execute("INSERT INTO delivery_items (deliverydocument, referencesddocument, deliveryitem, material, deliveredquantity) VALUES (?,?,?,?,?)", (
        del_id, order_id, f"{(idx % 10) + 1:06d}", f"MAT-{1000 + idx}", round(random.uniform(1, 100), 2)
    ))

    # Invoice
    inv_id = str(inv_counter + idx)
    inv_date = (base_date + timedelta(days=idx * 7 + 5)).strftime("%Y-%m-%d")
    acct_doc = str(jnl_counter + idx)
    c.execute("INSERT OR IGNORE INTO invoices VALUES (?,?,?,?,?,?,?)", (
        inv_id, doc_types[idx % 3], party_bp,
        amount, acct_doc, inv_date, currency
    ))
    c.execute("INSERT INTO invoice_items (billingdocument, referencesddocument, billingitem, material, netamount) VALUES (?,?,?,?,?)", (
        inv_id, del_id, f"{(idx % 10) + 1:06d}", f"MAT-{1000 + idx}", amount
    ))

    # Journal Entry
    post_date = (base_date + timedelta(days=idx * 7 + 6)).strftime("%Y-%m-%d")
    fy = "2024"
    glaccount = f"1100{idx % 10:02d}"
    profit_center = f"PC{1000 + (idx % 5)}"
    cost_center = f"CC{2000 + (idx % 5)}"
    company_code = company_codes[idx % 3]
    c.execute("INSERT OR IGNORE INTO journal_entries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        acct_doc, inv_id, amount,
        acct_doc_types[idx % 3], company_code, fy,
        post_date, inv_date,
        glaccount, party_bp,
        profit_center, cost_center,
        currency, amount, currency, "D"
    ))

    # Payment (90% of orders get paid)
    if idx % 10 != 0:
        pay_id = str(pay_counter + idx)
        pay_date = (base_date + timedelta(days=idx * 7 + 14)).strftime("%Y-%m-%d")
        c.execute("INSERT OR IGNORE INTO payments VALUES (?,?,?,?,?,?)", (
            pay_id, inv_id, amount,
            order_id, pay_date, "T"
        ))

conn.commit()
conn.close()
print(f"Database created at: {DB_PATH}")

# Verify
conn2 = sqlite3.connect(DB_PATH)
cur2 = conn2.cursor()
for tbl in ["customers", "orders", "deliveries", "delivery_items", "invoices", "invoice_items", "journal_entries", "payments"]:
    cur2.execute(f"SELECT COUNT(*) FROM {tbl}")
    print(f"  {tbl}: {cur2.fetchone()[0]} rows")
conn2.close()
