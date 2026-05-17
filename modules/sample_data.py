import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_corporate_sample_data() -> pd.DataFrame:
    """Generate a highly realistic corporate sales dataset for demonstration."""
    # Seed for reproducibility
    random.seed(42)
    np.random.seed(42)
    
    # Products catalog with price, cost, and category
    products_catalog = [
        # Eletrônicos (High faturamento, moderate margin)
        {"product": "Notebook Pro 15", "category": "Eletrônicos", "price": 5499.00, "cost": 4200.00},
        {"product": "Monitor UltraWide 34", "category": "Eletrônicos", "price": 2299.00, "cost": 2080.00}, # Critically low margin (9.5%)
        {"product": "Tablet SmartPad 10", "category": "Eletrônicos", "price": 1899.00, "cost": 1200.00},
        
        # Periféricos (High margin)
        {"product": "Teclado Mecânico RGB", "category": "Periféricos", "price": 450.00, "cost": 180.00},
        {"product": "Mouse Sem Fio Multi-Device", "category": "Periféricos", "price": 299.00, "cost": 110.00},
        {"product": "Headset Gamer Pro 7.1", "category": "Periféricos", "price": 649.00, "cost": 310.00},
        
        # Acessórios (Very high margin, low price)
        {"product": "Hub USB-C 8-in-1", "category": "Acessórios", "price": 389.00, "cost": 350.00}, # Low margin (10%)
        {"product": "Suporte Articulado Monitor", "category": "Acessórios", "price": 180.00, "cost": 65.00},
        {"product": "Carregador GaN 65W Duo", "category": "Acessórios", "price": 220.00, "cost": 95.00},
        
        # Móveis de Escritório
        {"product": "Cadeira Ergonômica Premium", "category": "Móveis", "price": 1499.00, "cost": 750.00},
        {"product": "Mesa Escritório Elevatória", "category": "Móveis", "price": 2899.00, "cost": 2100.00}
    ]
    
    # Generate records over the last 30 days
    today = datetime.now()
    records = []
    
    for i in range(120): # 120 sales transactions
        # Distribute dates realistically (more sales during weekdays, less on Sundays)
        days_ago = random.randint(0, 30)
        sale_date = today - timedelta(days=days_ago)
        
        # Weekend adjustment (reduce sales volume slightly)
        if sale_date.weekday() in [5, 6] and random.random() > 0.4:
            continue
            
        # Select product
        product_info = random.choice(products_catalog)
        
        # Quantity based on product type
        if product_info["price"] > 2000:
            quantity = random.randint(1, 2)
        elif product_info["price"] > 500:
            quantity = random.randint(1, 4)
        else:
            quantity = random.randint(2, 8)
            
        # Calculate finance columns
        price = product_info["price"]
        cost = product_info["cost"]
        revenue = price * quantity
        profit = revenue - (cost * quantity)
        margin = profit / revenue
        
        records.append({
            "product": product_info["product"],
            "category": product_info["category"],
            "price": price,
            "cost": cost,
            "quantity": quantity,
            "revenue": revenue,
            "profit": profit,
            "margin": margin,
            "date": sale_date.strftime("%Y-%m-%d")
        })
        
    df = pd.DataFrame(records)
    # Sort by date for neatness
    df = df.sort_values(by="date").reset_index(drop=True)
    return df
