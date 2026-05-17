import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_custom_css():
    """Inject premium, customized CSS styling into Streamlit for glassmorphism and animations."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        
        /* Font Overrides */
        html, body, [class*="css"], .stMarkdown {
            font-family: 'Outfit', 'Inter', sans-serif;
        }
        
        /* Premium KPI Card Styling */
        .kpi-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 20px 24px;
            box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            margin-bottom: 12px;
        }
        
        .kpi-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 25px -4px rgba(15, 23, 42, 0.08);
            border-color: #cbd5e1;
        }
        
        .kpi-label {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            font-weight: 600;
            margin-bottom: 6px;
        }
        
        .kpi-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.2;
        }
        
        .kpi-change-positive {
            font-size: 0.8rem;
            color: #10b981;
            font-weight: 600;
            margin-top: 4px;
            display: flex;
            align-items: center;
        }

        .kpi-change-negative {
            font-size: 0.8rem;
            color: #ef4444;
            font-weight: 600;
            margin-top: 4px;
            display: flex;
            align-items: center;
        }
        
        /* Title styling */
        .premium-title {
            background: linear-gradient(to right, #0f172a, #2563eb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        /* Dark Theme compatibility for Streamlit cards */
        @media (prefers-color-scheme: dark) {
            .kpi-card {
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                border-color: #334155;
                box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.3);
            }
            .kpi-card:hover {
                border-color: #475569;
                box-shadow: 0 12px 25px -4px rgba(0, 0, 0, 0.4);
            }
            .kpi-value {
                color: #f8fafc;
            }
            .kpi-label {
                color: #94a3b8;
            }
        }
        </style>
    """, unsafe_allow_html=True)

def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render beautiful sidebar filters and return the filtered dataset."""
    st.sidebar.markdown("### 🔍 Filtros de Análise")
    
    # 1. Category Filter
    all_categories = ['Todos'] + sorted(df['category'].unique().tolist())
    selected_category = st.sidebar.selectbox("Filtrar por Categoria", all_categories)
    
    # 2. Date Range Filter
    df['date_parsed'] = pd.to_datetime(df['date'])
    min_date = df['date_parsed'].min().date()
    max_date = df['date_parsed'].max().date()
    
    # Check if dates are valid
    if min_date == max_date:
        # Avoid streamlit error for same start and end dates
        st.sidebar.info(f"Período único: {min_date.strftime('%d/%m/%Y')}")
        selected_dates = (min_date, max_date)
    else:
        selected_dates = st.sidebar.date_input(
            "Período de Vendas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
    # Apply filtering logic safely
    filtered_df = df.copy()
    
    # Category Filter Apply
    if selected_category != 'Todos':
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
        
    # Date Filter Apply
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        filtered_df = filtered_df[
            (filtered_df['date_parsed'].dt.date >= start_date) & 
            (filtered_df['date_parsed'].dt.date <= end_date)
        ]
        
    # Clean up parsed date column from result
    filtered_df = filtered_df.drop(columns=['date_parsed'])
    
    return filtered_df

def render_kpis(df: pd.DataFrame):
    """Render modern corporate KPI cards."""
    total_revenue = df['revenue'].sum()
    total_profit = df['profit'].sum()
    avg_margin = df['margin'].mean() * 100 if not df.empty else 0.0
    total_qty = df['quantity'].sum()
    
    # Format values
    faturamento_formatted = f"R$ {total_revenue:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
    lucro_formatted = f"R$ {total_profit:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
    margem_formatted = f"{avg_margin:.1f}%"
    vendas_formatted = f"{total_qty:,}".replace(',', '.')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Faturamento Total</div>
                <div class="kpi-value">{faturamento_formatted}</div>
                <div class="kpi-change-positive">🗠 Receita Bruta</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Lucro Estimado</div>
                <div class="kpi-value" style="color: #10b981;">{lucro_formatted}</div>
                <div class="kpi-change-positive">🛄 Retorno Líquido</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col3:
        # Determine color of margin based on health
        margin_color = "#2563eb"
        margin_icon = "🔵 Margem Saudável"
        if avg_margin < 15:
            margin_color = "#ef4444"
            margin_icon = "⚠️ Margem Alerta"
            
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Margem Média</div>
                <div class="kpi-value" style="color: {margin_color};">{margem_formatted}</div>
                <div class="kpi-change-positive" style="color: {margin_color};">{margin_icon}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Qtd. Comercializada</div>
                <div class="kpi-value">{vendas_formatted}</div>
                <div class="kpi-change-positive">📦 Unidades Vendidas</div>
            </div>
        """, unsafe_allow_html=True)

def render_charts(df: pd.DataFrame):
    """Render gorgeous, interactive Plotly charts."""
    st.markdown("### 📊 Análise Gráfica Detalhada")
    
    # Layout 1: Sales Evolution and Category Share
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Evolução Comercial por Período")
        # Sales and Profit evolution over time
        df_time = df.groupby('date').agg(
            faturamento=('revenue', 'sum'),
            lucro=('profit', 'sum')
        ).sort_index().reset_index()
        
        fig_time = go.Figure()
        
        # Area chart for Revenue
        fig_time.add_trace(go.Scatter(
            x=df_time['date'], 
            y=df_time['faturamento'],
            mode='lines',
            name='Faturamento',
            fill='tozeroy',
            line=dict(color='#2563EB', width=3),
            fillcolor='rgba(37, 99, 235, 0.1)'
        ))
        
        # Line for Profit
        fig_time.add_trace(go.Scatter(
            x=df_time['date'], 
            y=df_time['lucro'],
            mode='lines+markers',
            name='Lucro Estimado',
            line=dict(color='#10B981', width=3, dash='dash')
        ))
        
        fig_time.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=10, b=20),
            height=300,
            xaxis=dict(showgrid=True, gridcolor='#F1F5F9'),
            yaxis=dict(showgrid=True, gridcolor='#F1F5F9'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        st.plotly_chart(fig_time, use_container_width=True)
        
    with col2:
        st.markdown("#### Faturamento por Categoria")
        # Category share
        df_cat = df.groupby('category')['revenue'].sum().reset_index()
        
        fig_cat = px.pie(
            df_cat, 
            values='revenue', 
            names='category',
            color_discrete_sequence=['#2563EB', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
        )
        
        fig_cat.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hole=0.4,
            marker=dict(line=dict(color='#ffffff', width=2))
        )
        
        fig_cat.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=10, b=20),
            height=300,
            showlegend=False
        )
        st.plotly_chart(fig_cat, use_container_width=True)
        
    # Layout 2: Best Selling Products and Critical Margins
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("#### Top 10 Produtos por Faturamento")
        df_prod = df.groupby('product')['revenue'].sum().nlargest(10).reset_index().sort_values(by='revenue', ascending=True)
        
        fig_prod = px.bar(
            df_prod,
            x='revenue',
            y='product',
            orientation='h',
            labels={'revenue': 'Faturamento (R$)', 'product': 'Produto'},
            color_discrete_sequence=['#2563EB']
        )
        
        fig_prod.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=10, b=20),
            height=320,
            xaxis=dict(showgrid=True, gridcolor='#F1F5F9'),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_prod, use_container_width=True)
        
    with col4:
        st.markdown("#### Produtos com Margem de Alerta (Menor Margem)")
        # Group by product, average margin, and get those with smallest margin
        # Only show products with meaningful sales volume to avoid noise
        df_margin = df.groupby('product').agg(
            margem_media=('margin', 'mean'),
            faturamento=('revenue', 'sum')
        ).reset_index()
        
        # Convert margins to percentages
        df_margin['margem_media'] = df_margin['margem_media'] * 100
        
        # Grab lowest 10 margins
        df_margin = df_margin.nsmallest(10, 'margem_media').sort_values(by='margem_media', ascending=False)
        
        # Color based on margin threshold (< 15% is Red, else Orange)
        colors_list = ['#EF4444' if x < 15 else '#F59E0B' for x in df_margin['margem_media']]
        
        fig_margin = go.Figure(go.Bar(
            x=df_margin['margem_media'],
            y=df_margin['product'],
            orientation='h',
            marker_color=colors_list,
            text=df_margin['margem_media'].apply(lambda x: f"{x:.1f}%"),
            textposition='inside',
        ))
        
        fig_margin.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=10, b=20),
            height=320,
            xaxis=dict(title='Margem Média (%)', showgrid=True, gridcolor='#F1F5F9'),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig_margin, use_container_width=True)
