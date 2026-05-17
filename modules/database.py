import sqlite3
import os
import pandas as pd
from datetime import datetime

# Define database file path dynamically relative to this file's folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "smartbi.db")

def get_connection():
    """Establish connection to SQLite database and ensure FK support is active."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize database tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create imports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            import_date TEXT NOT NULL,
            records_count INTEGER NOT NULL
        )
    """)
    
    # Create sales table with Cascade Delete on import_id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id TEXT NOT NULL,
            product TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL NOT NULL,
            quantity INTEGER NOT NULL,
            revenue REAL NOT NULL,
            profit REAL NOT NULL,
            margin REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (import_id) REFERENCES imports(import_id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def save_import(filename: str, import_id: str, df: pd.DataFrame) -> bool:
    """Save normalized sales DataFrame to database and record in imports history."""
    if df.empty:
        return False
        
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Insert import history record
        import_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records_count = len(df)
        
        cursor.execute(
            "INSERT INTO imports (import_id, filename, import_date, records_count) VALUES (?, ?, ?, ?)",
            (import_id, filename, import_date, records_count)
        )
        
        # Add import_id column to DataFrame for insertion
        df_to_save = df.copy()
        df_to_save['import_id'] = import_id
        
        # Rearrange columns to match sales table (excluding auto-increment id)
        columns_order = [
            'import_id', 'product', 'category', 'price', 
            'cost', 'quantity', 'revenue', 'profit', 'margin', 'date'
        ]
        
        df_to_save = df_to_save[columns_order]
        
        # Bulk insert
        df_to_save.to_sql('sales', conn, if_exists='append', index=False)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error saving import to database: {e}")
        raise e
    finally:
        conn.close()

def get_all_sales() -> pd.DataFrame:
    """Retrieve all sales records from database."""
    init_db()
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM sales", conn)
        return df
    finally:
        conn.close()

def get_import_history() -> pd.DataFrame:
    """Retrieve history of all imports."""
    init_db()
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM imports ORDER BY import_date DESC", conn)
        return df
    finally:
        conn.close()

def delete_import(import_id: str) -> bool:
    """Delete an import and its corresponding sales records via CASCADE."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM imports WHERE import_id = ?", (import_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error deleting import {import_id}: {e}")
        return False
    finally:
        conn.close()

def clear_all_data() -> bool:
    """Clear all sales and imports from the database."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM imports")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error clearing data: {e}")
        return False
    finally:
        conn.close()
