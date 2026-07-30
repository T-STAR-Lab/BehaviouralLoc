#!/usr/bin/env python3
"""Generate inventory.db with chemicals_stock and budget_logs tables."""
import sqlite3
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ---- chemicals_stock table ----
cur.execute("""
CREATE TABLE IF NOT EXISTS chemicals_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cas_number TEXT,
    category TEXT NOT NULL,
    current_stock_liters REAL NOT NULL,
    min_stock_liters REAL NOT NULL,
    unit_price REAL NOT NULL,
    supplier TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    last_restocked TEXT NOT NULL,
    storage_location TEXT NOT NULL,
    hazard_level TEXT DEFAULT 'low'
)
""")

today = datetime.date(2026, 3, 11)

chemicals = [
    # Expiring within 30 days (need restocking)
    ("Anhydrous Ethanol", "64-17-5", "solvent", 12.0, 50.0, 45.0, "SinoReagent Co.", today + datetime.timedelta(days=8), today - datetime.timedelta(days=170), "Cabinet A-03", "low"),
    ("LB Broth (Lennox)", "N/A", "culture_medium", 5.0, 20.0, 120.0, "BioMaster Ltd.", today + datetime.timedelta(days=15), today - datetime.timedelta(days=80), "Fridge B-01", "low"),
    ("Phosphate Buffered Saline 10X", "N/A", "buffer", 3.5, 15.0, 85.0, "SinoReagent Co.", today + datetime.timedelta(days=22), today - datetime.timedelta(days=150), "Cabinet A-05", "low"),
    ("Dimethyl Sulfoxide (DMSO)", "67-68-5", "solvent", 2.0, 10.0, 65.0, "ChemSupply Inc.", today + datetime.timedelta(days=12), today - datetime.timedelta(days=200), "Cabinet A-03", "low"),
    ("Trypsin-EDTA 0.25%", "9002-07-7", "enzyme", 1.0, 5.0, 280.0, "BioMaster Ltd.", today + datetime.timedelta(days=25), today - datetime.timedelta(days=60), "Fridge B-02", "low"),
    ("Fetal Bovine Serum", "N/A", "serum", 0.5, 3.0, 950.0, "BioMaster Ltd.", today + datetime.timedelta(days=18), today - datetime.timedelta(days=45), "Freezer C-01", "low"),
    ("Isopropanol", "67-63-0", "solvent", 8.0, 30.0, 38.0, "SinoReagent Co.", today + datetime.timedelta(days=5), today - datetime.timedelta(days=160), "Cabinet A-03", "low"),
    ("Chloroform", "67-66-3", "solvent", 4.0, 10.0, 72.0, "ChemSupply Inc.", today + datetime.timedelta(days=28), today - datetime.timedelta(days=90), "Hazmat D-01", "medium"),
    # NOT expiring within 30 days (should not be restocked)
    ("Sodium Chloride", "7647-14-5", "salt", 25.0, 10.0, 15.0, "SinoReagent Co.", today + datetime.timedelta(days=180), today - datetime.timedelta(days=30), "Cabinet A-01", "low"),
    ("Hydrochloric Acid 37%", "7647-01-0", "acid", 10.0, 5.0, 55.0, "ChemSupply Inc.", today + datetime.timedelta(days=120), today - datetime.timedelta(days=60), "Hazmat D-02", "high"),
    ("Acetone", "67-64-1", "solvent", 15.0, 10.0, 32.0, "SinoReagent Co.", today + datetime.timedelta(days=95), today - datetime.timedelta(days=45), "Cabinet A-03", "low"),
    ("Sodium Hydroxide Pellets", "1310-73-2", "base", 8.0, 5.0, 28.0, "SinoReagent Co.", today + datetime.timedelta(days=200), today - datetime.timedelta(days=20), "Cabinet A-02", "medium"),
    ("Methanol", "67-56-1", "solvent", 20.0, 15.0, 40.0, "ChemSupply Inc.", today + datetime.timedelta(days=150), today - datetime.timedelta(days=40), "Cabinet A-03", "medium"),
    ("Tris Base", "77-86-1", "buffer_component", 5.0, 3.0, 95.0, "BioMaster Ltd.", today + datetime.timedelta(days=250), today - datetime.timedelta(days=10), "Cabinet A-05", "low"),
    ("EDTA Disodium Salt", "6381-92-6", "chelator", 3.0, 2.0, 68.0, "BioMaster Ltd.", today + datetime.timedelta(days=300), today - datetime.timedelta(days=15), "Cabinet A-05", "low"),
]

for c in chemicals:
    cur.execute("""
        INSERT INTO chemicals_stock (name, cas_number, category, current_stock_liters,
            min_stock_liters, unit_price, supplier, expiry_date, last_restocked,
            storage_location, hazard_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (c[0], c[1], c[2], c[3], c[4], c[5], c[6],
          c[7].isoformat(), c[8].isoformat(), c[9], c[10]))

# ---- budget_logs table ----
cur.execute("""
CREATE TABLE IF NOT EXISTS budget_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT NOT NULL,
    description TEXT NOT NULL,
    item_name TEXT,
    quantity REAL,
    unit_price REAL,
    total_amount REAL NOT NULL,
    category TEXT DEFAULT 'procurement',
    approved_by TEXT DEFAULT 'Dr. Zhang',
    order_ref TEXT
)
""")

# Seed with some historical budget entries
budget_entries = [
    (today - datetime.timedelta(days=45), "Routine restock - solvents", "Anhydrous Ethanol", 50.0, 45.0, 2250.0, "procurement", "Dr. Zhang", "ORD-2026-0089"),
    (today - datetime.timedelta(days=45), "Routine restock - solvents", "Isopropanol", 30.0, 38.0, 1140.0, "procurement", "Dr. Zhang", "ORD-2026-0089"),
    (today - datetime.timedelta(days=30), "Culture medium restock", "LB Broth (Lennox)", 20.0, 120.0, 2400.0, "procurement", "Dr. Zhang", "ORD-2026-0102"),
    (today - datetime.timedelta(days=30), "Enzyme restock", "Trypsin-EDTA 0.25%", 5.0, 280.0, 1400.0, "procurement", "Dr. Zhang", "ORD-2026-0102"),
    (today - datetime.timedelta(days=15), "Serum purchase", "Fetal Bovine Serum", 3.0, 950.0, 2850.0, "procurement", "Dr. Zhang", "ORD-2026-0118"),
    (today - datetime.timedelta(days=10), "Equipment maintenance", None, None, None, 3500.0, "maintenance", "Dr. Zhang", None),
    (today - datetime.timedelta(days=5), "Safety equipment renewal", None, None, None, 1200.0, "safety", "Dr. Zhang", None),
]

for b in budget_entries:
    cur.execute("""
        INSERT INTO budget_logs (transaction_date, description, item_name, quantity,
            unit_price, total_amount, category, approved_by, order_ref)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (b[0].isoformat(), b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8]))

conn.commit()
conn.close()
print(f"Generated {DB_PATH}")
print(f"  chemicals_stock: {len(chemicals)} rows")
print(f"  budget_logs: {len(budget_entries)} rows")
