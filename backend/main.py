from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)
app = FastAPI()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

def db():
    c = sqlite3.connect("data.db")
    c.row_factory = sqlite3.Row
    return c

def get_schema():
    conn = db()
    schema = ""
    for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        cols = conn.execute(f"PRAGMA table_info({t[0]})").fetchall()
        schema += f"{t[0]}({', '.join(c[1] for c in cols)})\n"
    conn.close()
    return schema

@app.get("/")
def root(): return {"status": "running"}

@app.get("/graph")
def graph():
    conn = db()
    nodes, links = [], []
    COLORS = {
        "orders":     "#378ADD",
        "deliveries": "#1D9E75",
        "invoices":   "#D85A30",
        "journal":    "#E8A838",
        "payments":   "#7F77DD",
        "customers":  "#888780"
    }

    # Fetch 30 Orders, absolutely guaranteeing our test case IDs are present so we can test the Auto-Highlight and Zoom feature!
    order_rows = conn.execute("""
        SELECT * FROM (
            SELECT DISTINCT o.salesorder, o.salesordertype, o.soldtoparty, o.totalnetamount, o.overalldeliverystatus 
            FROM orders o
            INNER JOIN delivery_items d ON o.salesorder = d.referencesddocument
            INNER JOIN invoice_items i ON d.deliverydocument = i.referencesddocument
            WHERE o.salesorder IN ('740550', '740566')
        )
        UNION ALL
        SELECT * FROM (
            SELECT o.salesorder, o.salesordertype, o.soldtoparty, o.totalnetamount, o.overalldeliverystatus 
            FROM orders o
            INNER JOIN delivery_items d ON o.salesorder = d.referencesddocument
            INNER JOIN invoice_items i ON d.deliverydocument = i.referencesddocument
            WHERE o.salesorder NOT IN ('740550', '740566')
            GROUP BY o.soldtoparty
            LIMIT 28
        )
    """).fetchall()
    order_ids = []
    customer_ids = set()

    for row in order_rows:
        d = dict(row)
        order_ids.append(d['salesorder'])
        if d.get('soldtoparty'):
            customer_ids.add(str(d['soldtoparty']))
        nodes.append({
            "id": f"orders_{d['salesorder']}", "label": f"Order {d['salesorder']}",
            "type": "Orders", "color": COLORS["orders"],
            "data": {k: str(v) for k, v in d.items()}
        })
        if d.get('soldtoparty'):
            links.append({"source": f"customers_{d['soldtoparty']}", "target": f"orders_{d['salesorder']}"})

    if not order_ids:
        conn.close()
        return {"nodes": nodes, "links": links}

    # Customers
    if customer_ids:
        c_placeholders = ','.join(['?']*len(customer_ids))
        cust_rows = conn.execute(f"SELECT businesspartner, businesspartnername, customer FROM customers WHERE businesspartner IN ({c_placeholders}) OR customer IN ({c_placeholders})", list(customer_ids) + list(customer_ids)).fetchall()
        for row in cust_rows:
            d = dict(row)
            bp = d.get('businesspartner') or d.get('customer', '')
            nodes.append({
                "id": f"customers_{bp}", "label": f"{d.get('businesspartnername', bp)[:20]}",
                "type": "Customers", "color": COLORS["customers"],
                "data": {k: str(v) for k, v in d.items()}
            })

    # Deliveries
    if order_ids:
        o_placeholders = ','.join(['?']*len(order_ids))
        deliv_items = conn.execute(f"SELECT DISTINCT deliverydocument, referencesddocument FROM delivery_items WHERE referencesddocument IN ({o_placeholders})", order_ids).fetchall()
        deliv_ids = list(set([str(row[0]) for row in deliv_items if row[0]]))

        for row in deliv_items:
            if row[0] and row[1]:
                links.append({"source": f"orders_{row[1]}", "target": f"deliveries_{row[0]}"})

        if deliv_ids:
            d_placeholders = ','.join(['?']*len(deliv_ids))
            deliv_rows = conn.execute(f"SELECT deliverydocument, creationdate, overallgoodsmovementstatus FROM deliveries WHERE deliverydocument IN ({d_placeholders})", deliv_ids).fetchall()
            for row in deliv_rows:
                d = dict(row)
                nodes.append({
                    "id": f"deliveries_{d['deliverydocument']}", "label": f"Delivery {d['deliverydocument']}",
                    "type": "Deliveries", "color": COLORS["deliveries"],
                    "data": {k: str(v) for k, v in d.items()}
                })

    # Invoices
    if deliv_ids:
        d_placeholders = ','.join(['?']*len(deliv_ids))
        inv_items = conn.execute(f"SELECT DISTINCT billingdocument, referencesddocument FROM invoice_items WHERE referencesddocument IN ({d_placeholders})", deliv_ids).fetchall()
        inv_ids = list(set([str(row[0]) for row in inv_items if row[0]]))

        for row in inv_items:
            if row[0] and row[1]:
                links.append({"source": f"deliveries_{row[1]}", "target": f"invoices_{row[0]}"})

        if inv_ids:
            i_placeholders = ','.join(['?']*len(inv_ids))
            inv_rows = conn.execute(f"SELECT billingdocument, billingdocumenttype, soldtoparty, totalnetamount, accountingdocument FROM invoices WHERE billingdocument IN ({i_placeholders})", inv_ids).fetchall()
            for row in inv_rows:
                d = dict(row)
                nodes.append({
                    "id": f"invoices_{d['billingdocument']}", "label": f"Invoice {d['billingdocument']}",
                    "type": "Invoices", "color": COLORS["invoices"],
                    "data": {k: str(v) for k, v in d.items()}
                })

            # Journal Entries
            je_rows = conn.execute(f"""SELECT accountingdocument, referencedocument, amountintransactioncurrency, 
            accountingdocumenttype, companycode, fiscalyear, postingdate, documentdate,
            glaccount, customer, profitcenter, costcenter, transactioncurrency,
            amountincompanycodecurrency, companycodecurrency, financialaccounttype
            FROM journal_entries WHERE referencedocument IN ({i_placeholders})""", inv_ids).fetchall()
            for row in je_rows:
                d = dict(row)
                nodes.append({
                    "id": f"journal_{d['accountingdocument']}", "label": f"Journal {d['accountingdocument']}",
                    "type": "Journal", "color": COLORS["journal"],
                    "data": {k: str(v) for k, v in d.items()}
                })
                if d.get('referencedocument'):
                    links.append({"source": f"invoices_{d['referencedocument']}", "target": f"journal_{d['accountingdocument']}"})

            # Payments
            pay_rows = conn.execute(f"SELECT accountingdocument, invoicereference, amountintransactioncurrency, salesdocument FROM payments WHERE invoicereference IN ({i_placeholders})", inv_ids).fetchall()
            for row in pay_rows:
                d = dict(row)
                nodes.append({
                    "id": f"payments_{d['accountingdocument']}", "label": f"Payment {d['accountingdocument']}",
                    "type": "Payments", "color": COLORS["payments"],
                    "data": {k: str(v) for k, v in d.items()}
                })
                if d.get('invoicereference'):
                    links.append({"source": f"invoices_{d['invoicereference']}", "target": f"payments_{d['accountingdocument']}"})

    conn.close()
    return {"nodes": nodes, "links": links}

class Q(BaseModel):
    question: str


import re

def clean_question(q):
    q = q.lower().strip()

    q = q.replace("salesorder", "sales order")
    q = q.replace("sales_order", "sales order")
    q = q.replace("invoice no", "invoice")
    q = q.replace("billing doc", "billing document")

    return q

@app.post("/query")
def query(req: Q):
    try:

        user_question = clean_question(req.question)

        # ---------------------------------
        # SMART FALLBACK HANDLER
        # ---------------------------------

        order_match = re.search(r'\b7\d+\b', user_question)

        if order_match:

            order_id = order_match.group()

            conn = db()

            # ---------------------------------
            # SIMPLE ORDER DETAILS
            # ---------------------------------

            if (
    user_question == order_id
    or (
        "sales order" in user_question
        and "invoice" not in user_question
        and "billing" not in user_question
        and "delivery" not in user_question
        and "customer" not in user_question
        and "flow" not in user_question
        and "trace" not in user_question
    )
    or "show order" in user_question
):

                rows = conn.execute("""
                SELECT salesorder,
                       soldtoparty,
                       totalnetamount,
                       overalldeliverystatus
                FROM orders
                WHERE salesorder = ?
                """, (order_id,)).fetchall()

                conn.close()

                if rows:

                    data = [dict(r) for r in rows]

                    return {
                        "answer":
                        f"Sales order {order_id} found successfully.",
                        "data": data,
                        "sql":
                        f"SELECT * FROM orders WHERE salesorder='{order_id}'",
                        "highlight_nodes":
                        [f"orders_{order_id}"]
                    }

            # ---------------------------------
            # TRACE FULL FLOW
            # ---------------------------------

            if "trace" in user_question or "full flow" in user_question:

                rows = conn.execute("""
                SELECT
                    o.salesorder,
                    di.deliverydocument,
                    ii.billingdocument,
                    je.accountingdocument
                FROM orders o
                LEFT JOIN delivery_items di
                    ON di.referencesddocument = o.salesorder
                LEFT JOIN invoice_items ii
                    ON ii.referencesddocument = di.deliverydocument
                LEFT JOIN journal_entries je
                    ON je.referencedocument = ii.billingdocument
                WHERE o.salesorder = ?
                """, (order_id,)).fetchall()

                conn.close()

                if rows:

                    data = [dict(r) for r in rows]

                    return {
                        "answer":
                        f"Full business flow traced for sales order {order_id}.",
                        "data": data,
                        "sql": "Manual trace query",
                        "highlight_nodes":
                        [f"orders_{order_id}"]
                    }

            # ---------------------------------
            # CUSTOMER QUERY
            # ---------------------------------

            if "customer" in user_question:

                rows = conn.execute("""
                SELECT
                    o.salesorder,
                    o.soldtoparty,
                    c.businesspartnername
                FROM orders o
                LEFT JOIN customers c
                    ON o.soldtoparty = c.businesspartner
                WHERE o.salesorder = ?
                """, (order_id,)).fetchall()

                conn.close()

                if rows:

                    data = [dict(r) for r in rows]

                    customer_name = data[0].get(
                        "businesspartnername",
                        "Unknown"
                    )

                    return {
                        "answer":
                        f"The customer for sales order {order_id} is {customer_name}.",
                        "data": data,
                        "sql": "Manual customer query",
                        "highlight_nodes":
                        [f"orders_{order_id}"]
                    }

            # ---------------------------------
            # DELIVERY QUERY
            # ---------------------------------

            if "delivery" in user_question:

                rows = conn.execute("""
                SELECT
                    di.deliverydocument,
                    d.overallgoodsmovementstatus
                FROM delivery_items di
                LEFT JOIN deliveries d
                    ON di.deliverydocument = d.deliverydocument
                WHERE di.referencesddocument = ?
                """, (order_id,)).fetchall()

                conn.close()

                if rows:

                    data = [dict(r) for r in rows]

                    return {
                        "answer":
                        f"Delivery information found for sales order {order_id}.",
                        "data": data,
                        "sql": "Manual delivery query",
                        "highlight_nodes":
                        [f"orders_{order_id}"]
                    }

                return {
                    "answer":
                    f"No delivery exists yet for sales order {order_id}.",
                    "data": [],
                    "sql": ""
                }

            # ---------------------------------
            # BILLING / INVOICE QUERY
            # ---------------------------------

            if (
                "billing" in user_question
                or "invoice" in user_question
            ):

                rows = conn.execute("""
                SELECT
                    ii.billingdocument
                FROM delivery_items di
                LEFT JOIN invoice_items ii
                    ON di.deliverydocument = ii.referencesddocument
                WHERE di.referencesddocument = ?
                """, (order_id,)).fetchall()

                conn.close()

                if rows:

                    data = [dict(r) for r in rows]

                    return {
                        "answer":
                        f"Billing documents found for sales order {order_id}.",
                        "data": data,
                        "sql": "Manual billing query",
                        "highlight_nodes":
                        [f"orders_{order_id}"]
                    }

                return {
                    "answer":
                    f"No billing document exists yet for sales order {order_id}.",
                    "data": [],
                    "sql": ""
                }

            # ---------------------------------
            # DELIVERY STATUS
            # ---------------------------------

            if "delivery status" in user_question:

                rows = conn.execute("""
                SELECT
                    deliverydocument,
                    overallgoodsmovementstatus
                FROM deliveries
                LIMIT 10
                """).fetchall()

                conn.close()

                data = [dict(r) for r in rows]

                return {
                    "answer":
                    "Delivery status records fetched successfully.",
                    "data": data,
                    "sql": "Manual delivery status query"
                }

        schema = get_schema()

        SYSTEM = f"""You are a data analyst for an SAP Order-to-Cash business system.
ONLY answer questions about this database. NOTHING ELSE.

Schema:
{schema}

EXACT COLUMN RELATIONSHIPS (use these exactly, never guess):
- orders.salesorder = unique sales order ID
- orders.soldtoparty = customer ID → links to customers.businesspartner
- customers.businesspartnername = customer name
- delivery_items.referencesddocument = sales order ID → links to orders.salesorder
- delivery_items.deliverydocument = delivery ID → links to deliveries.deliverydocument
- invoice_items.referencesddocument = delivery document ID → links to delivery_items.deliverydocument
- invoice_items.billingdocument = billing document ID → links to invoices.billingdocument
- invoice_items.material = product/material ID
- journal_entries.referencedocument = billing document ID → links to invoices.billingdocument
- journal_entries.accountingdocument = journal entry number
- payments.invoicereference = billing document ID → links to invoices.billingdocument
- payments.salesdocument = sales order ID → links to orders.salesorder
- order_items.salesorder = sales order ID → links to orders.salesorder
- order_items.material = product/material ID

EXACT SQL TEMPLATES - USE THESE EXACTLY FOR THESE QUERY TYPES:

1. TRACE FULL FLOW OF A BILLING DOCUMENT (Sales Order → Delivery → Billing → Journal Entry):
SQL: SELECT o.salesorder, o.totalnetamount, di.deliverydocument, ii.billingdocument, je.accountingdocument, p.amountintransactioncurrency FROM invoices i LEFT JOIN invoice_items ii ON i.billingdocument = ii.billingdocument LEFT JOIN delivery_items di ON ii.referencesddocument = di.deliverydocument LEFT JOIN orders o ON di.referencesddocument = o.salesorder LEFT JOIN journal_entries je ON je.referencedocument = i.billingdocument LEFT JOIN payments p ON p.invoicereference = i.billingdocument WHERE i.billingdocument = 'BILLING_DOC_ID' LIMIT 5

2. ORDERS DELIVERED BUT NOT BILLED (incomplete flow):
SQL: SELECT DISTINCT o.salesorder, o.totalnetamount, o.overalldeliverystatus FROM orders o WHERE o.salesorder IN (SELECT DISTINCT referencesddocument FROM delivery_items WHERE referencesddocument != '') AND o.salesorder NOT IN (SELECT DISTINCT di.referencesddocument FROM delivery_items di JOIN invoice_items ii ON di.deliverydocument = ii.referencesddocument WHERE di.referencesddocument != '') LIMIT 20

3. ORDERS BILLED BUT NOT DELIVERED (incomplete flow):
SQL: SELECT DISTINCT o.salesorder, o.totalnetamount FROM orders o WHERE o.salesorder NOT IN (SELECT DISTINCT referencesddocument FROM delivery_items WHERE referencesddocument != '') AND o.salesorder IN (SELECT DISTINCT di.referencesddocument FROM delivery_items di JOIN invoice_items ii ON di.deliverydocument = ii.referencesddocument WHERE di.referencesddocument != '') LIMIT 20

4. PRODUCTS WITH HIGHEST BILLING DOCUMENTS:
SQL: SELECT ii.material, COUNT(DISTINCT ii.billingdocument) as billing_count FROM invoice_items ii WHERE ii.material != '' GROUP BY ii.material ORDER BY billing_count DESC LIMIT 10

5. TRACE FULL FLOW OF A SALES ORDER:
SQL: SELECT o.salesorder, o.totalnetamount, di.deliverydocument, ii.billingdocument, je.accountingdocument FROM orders o LEFT JOIN delivery_items di ON di.referencesddocument = o.salesorder LEFT JOIN invoice_items ii ON ii.referencesddocument = di.deliverydocument LEFT JOIN journal_entries je ON je.referencedocument = ii.billingdocument WHERE o.salesorder = 'SALES_ORDER_ID' LIMIT 5

6. FIND JOURNAL ENTRY FOR BILLING DOCUMENT:
SQL: SELECT accountingdocument, referencedocument, amountintransactioncurrency FROM journal_entries WHERE referencedocument = 'BILLING_DOC_ID'

7. UNPAID INVOICES:
SQL: SELECT i.billingdocument, i.totalnetamount, i.soldtoparty FROM invoices i LEFT JOIN payments p ON p.invoicereference = i.billingdocument WHERE p.invoicereference IS NULL LIMIT 20

8. CUSTOMER WITH MOST ORDERS:
SQL: SELECT c.businesspartnername, COUNT(DISTINCT o.salesorder) as order_count FROM orders o JOIN customers c ON o.soldtoparty = c.businesspartner GROUP BY c.businesspartnername ORDER BY order_count DESC LIMIT 5

STRICT RULES:
1. ALWAYS use the exact column names from the schema above — NEVER guess column names
2. ALWAYS use the exact JOIN paths shown above — NEVER join tables directly if they need an intermediate table
3. Write ONE complete SQL query only
4. Never use markdown code blocks in SQL
5. Replace placeholder values like 'BILLING_DOC_ID' and 'SALES_ORDER_ID' with the actual value from the user question
6. If question is completely unrelated to business data respond EXACTLY:
   "This system is designed to answer questions about the Order-to-Cash dataset only."

RESPOND IN THIS EXACT FORMAT:
SQL: SELECT ... FROM ...
ANSWER: Based on the data, [explanation]"""

        r = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=1000,
            messages=[{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": req.question}])
        full = r.choices[0].message.content.strip()

        if "This system is designed" in full:
            return {"answer": full, "data": [], "sql": ""}

        if "SQL:" in full:
            sql = full.split("SQL:")[1].split("ANSWER:")[0].strip()
            sql = sql.replace("```sql", "").replace("```", "").strip().rstrip(";").strip()
            
            try:
                conn = db()
                rows = conn.execute(sql).fetchall()
                data = [dict(row) for row in rows]
                conn.close()
                
                if not data:
                    return {"answer": "No records found matching your query.", "data": [], "sql": sql}
                
                # Formulate the concise answer from the actual DB result
                sys2 = (
                    "You are a helpful SAP data assistant. Answer the user confidently in one single sentence using ONLY the database result. "
                    "CRITICAL: In our system, 'accountingdocument' IS the Journal Entry or Payment number. "
                    "Do NOT tell the user a document is 'not available' if you clearly see its 'accountingdocument' value in the data."
                )
                prompt2 = f"User Question: {req.question}\nDatabase Result: {data[:5]}\n\nAnswer:"
                
                r2 = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    max_tokens=200,
                    messages=[{"role": "system", "content": sys2},
                            {"role": "user", "content": prompt2}])
                
                final_ans = r2.choices[0].message.content.strip()
                
                highlight = []
                for row in data:
                    if row.get('salesorder'): highlight.append(f"orders_{row['salesorder']}")
                    if row.get('deliverydocument'): highlight.append(f"deliveries_{row['deliverydocument']}")
                    if row.get('billingdocument'): highlight.append(f"invoices_{row['billingdocument']}")
                    if row.get('accountingdocument'):
                        highlight.append(f"journal_{row['accountingdocument']}")
                        highlight.append(f"payments_{row['accountingdocument']}")
                    if row.get('businesspartner'): highlight.append(f"customers_{row['businesspartner']}")
                
                return {"answer": final_ans, "data": data, "sql": sql, "highlight_nodes": list(set(highlight))}
                
            except Exception as e:
                return {"answer": "Error executing SQL query.", "data": [], "sql": sql, "error": str(e)}

        return {"answer": full, "data": [], "sql": ""}
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        return {"answer": f"Server Crash: {err_msg}", "data": [], "sql": ""}


# ---------------------------------
# ANALYTICS API
# ---------------------------------

@app.get("/analytics")
def analytics():

    conn = db()

    total_orders = conn.execute("""
    SELECT COUNT(*) FROM orders
    """).fetchone()[0]

    total_customers = conn.execute("""
    SELECT COUNT(*) FROM customers
    """).fetchone()[0]

    total_invoices = conn.execute("""
    SELECT COUNT(*) FROM invoices
    """).fetchone()[0]

    total_payments = conn.execute("""
    SELECT COUNT(*) FROM payments
    """).fetchone()[0]

    total_revenue = conn.execute("""
    SELECT ROUND(SUM(totalnetamount), 2)
    FROM orders
    """).fetchone()[0]

    conn.close()

    return {
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_invoices": total_invoices,
        "total_payments": total_payments,
        "total_revenue": total_revenue
    }
    
