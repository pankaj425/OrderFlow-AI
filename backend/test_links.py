import sqlite3
import os
db_path = os.path.join(os.path.dirname(__file__), 'data.db')
c = sqlite3.connect(db_path)
print("Order:", c.execute("SELECT salesorder FROM orders WHERE salesorder='740550'").fetchall())
print("Delivery:", c.execute("SELECT deliverydocument FROM delivery_items WHERE referencesddocument='740550'").fetchall())
print("Invoice:", c.execute("SELECT billingdocument FROM invoice_items WHERE referencesddocument IN (SELECT deliverydocument FROM delivery_items WHERE referencesddocument='740550')").fetchall())
print("Journal:", c.execute("SELECT accountingdocument FROM journal_entries WHERE referencedocument IN (SELECT billingdocument FROM invoice_items WHERE referencesddocument IN (SELECT deliverydocument FROM delivery_items WHERE referencesddocument='740550'))").fetchall())
