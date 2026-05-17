import pandas as pd
import numpy as np
import os
import re

def clean_numeric_string(val):
    """Clean a numeric string, converting Brazilian comma format (1.200,50) or dollar formats to clean float."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    # Remove currency symbols and white spaces
    val_str = re.sub(r'[R\$\s\xa0]', '', val_str)
    
    if not val_str:
        return 0.0
        
    try:
        # Check if it has a comma and a period, e.g., 1.200,50
        if ',' in val_str and '.' in val_str:
            # If period comes before comma, it's BR format: 1.200,50
            if val_str.find('.') < val_str.find(','):
                val_str = val_str.replace('.', '').replace(',', '.')
            else:
                # US format: 1,200.50
                val_str = val_str.replace(',', '')
        elif ',' in val_str:
            # Just comma: 1200,50 -> 1200.50
            val_str = val_str.replace(',', '.')
            
        return float(val_str)
    except ValueError:
        return 0.0

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map df column names to unified lowercased standard schema."""
    # Define mapping variations
    mapping = {
        'product': ['produto', 'product', 'nome', 'nome do produto', 'item', 'descricao', 'descrição', 'mercadoria', 'artigo', 'título', 'titulo', 'serviço', 'servico'],
        'category': ['categoria', 'category', 'grupo', 'secao', 'seção', 'classificacao', 'classificação', 'departamento', 'linha', 'tipo', 'família', 'familia'],
        'price': ['preço', 'price', 'valor', 'preco', 'preço unitário', 'preco unitario', 'valor unitário', 'valor unitario', 'preço de venda', 'preco de venda', 'vlr', 'vl unit', 'faturamento', 'receita', 'total'],
        'cost': ['custo', 'cost', 'custo unitário', 'custo unitario', 'valor de custo', 'preço de custo', 'preco de custo', 'vlr custo'],
        'quantity': ['quantidade', 'quantity', 'qtd', 'qtd vendida', 'quantidade vendida', 'unidades', 'vendas', 'volume', 'qtde', 'quant', 'qnt', 'qntd'],
        'date': ['data', 'date', 'data venda', 'data da venda', 'periodo', 'período', 'competencia', 'competência', 'emissão', 'emissao', 'criado em', 'registro', 'dt_venda', 'dt']
    }
    
    col_map = {}
    for col in df.columns:
        col_lower = str(col).strip().lower()
        
        # Exact match first
        matched = False
        for std_key, variations in mapping.items():
            if col_lower in variations:
                col_map[col] = std_key
                matched = True
                break
                
        # If not exact, try robust substring match
        if not matched:
            for std_key, variations in mapping.items():
                if any(len(v) >= 3 and v in col_lower for v in variations):
                    col_map[col] = std_key
                    break
    
    df_renamed = df.rename(columns=col_map)
    return df_renamed

def process_uploaded_file(file_path: str) -> pd.DataFrame:
    """Read, clean and normalize an uploaded Excel or CSV file."""
    # Check extension
    _, ext = os.path.splitext(file_path.lower())
    
    if ext == '.csv':
        try:
            # Try reading with utf-8, then latin1, and let pandas guess separator
            df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
        except Exception:
            df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin1')
    elif ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Formato de arquivo não suportado. Envie apenas .xlsx, .xls ou .csv.")
        
    if df.empty:
        raise ValueError("O arquivo enviado está vazio.")
        
    # Normalize columns
    df = normalize_columns(df)
    
    # Check if core mandatory columns are present (only Product and Price are strictly needed)
    required_cols = ['product', 'price']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        raise ValueError(
            f"As colunas obrigatórias fundamentais não foram encontradas no arquivo.\n"
            f"Colunas ausentes: {', '.join(missing_cols)}.\n"
            f"Por favor, verifique se a planilha possui colunas equivalentes para: Produto e Preço/Valor."
        )
        
    # Fill smart defaults for missing supplementary columns
    if 'category' not in df.columns:
        df['category'] = 'Geral'
    if 'cost' not in df.columns:
        df['cost'] = np.nan
    if 'quantity' not in df.columns:
        df['quantity'] = 1
    if 'date' not in df.columns:
        df['date'] = pd.Timestamp.now().strftime("%Y-%m-%d")
        
    # Clean up rows - Drop rows where core info is missing
    df = df.dropna(subset=['product', 'price'], how='any')
    
    # Clean strings
    df['product'] = df['product'].astype(str).str.strip()
    df['category'] = df['category'].astype(str).str.strip().replace('', 'Geral')
    df['category'] = df['category'].fillna('Geral')
    
    # Clean numeric columns
    df['price'] = df['price'].apply(clean_numeric_string)
    
    if df['cost'].isna().all():
        df['cost'] = df['price'] * 0.60  # Default cost to 60% of price
    else:
        df['cost'] = df['cost'].apply(clean_numeric_string)
        # Default single missing costs to 60% of price
        df['cost'] = df.apply(lambda row: row['price'] * 0.60 if pd.isna(row['cost']) or row['cost'] == 0 else row['cost'], axis=1)

    df['quantity'] = df['quantity'].apply(lambda x: int(clean_numeric_string(x)))
    
    # Ensure quantity is positive
    df['quantity'] = df['quantity'].clip(lower=1)
    
    # Calculate financial formulas
    df['revenue'] = df['price'] * df['quantity']
    df['profit'] = df['revenue'] - (df['cost'] * df['quantity'])
    df['margin'] = df.apply(lambda row: (row['profit'] / row['revenue']) if row['revenue'] > 0 else 0.0, axis=1)
    
    # Normalize dates
    parsed_dates = []
    for d in df['date']:
        # if the default string was applied, skip parsing
        if str(d) == pd.Timestamp.now().strftime("%Y-%m-%d"):
            parsed_dates.append(str(d))
            continue
            
        try:
            p_date = pd.to_datetime(d, errors='coerce')
            if pd.isna(p_date):
                # Try parsing with dayfirst=True for Brazilian format
                p_date = pd.to_datetime(d, dayfirst=True, errors='coerce')
            
            if pd.isna(p_date):
                parsed_dates.append(pd.Timestamp.now().strftime("%Y-%m-%d"))
            else:
                parsed_dates.append(p_date.strftime("%Y-%m-%d"))
        except Exception:
            parsed_dates.append(pd.Timestamp.now().strftime("%Y-%m-%d"))
            
    df['date'] = parsed_dates
    
    # Select only standard fields
    final_cols = ['product', 'category', 'price', 'cost', 'quantity', 'revenue', 'profit', 'margin', 'date']
    df = df[final_cols]
    
    return df
