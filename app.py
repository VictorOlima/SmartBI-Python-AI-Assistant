import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import uuid
import threading
from datetime import datetime
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import local modular services
from modules.database import (
    init_db, save_import, get_all_sales, get_import_history, delete_import, clear_all_data
)
from modules.importer import process_uploaded_file
from modules.ai_analysis import generate_ai_insights
from modules.report_generator import generate_pdf_report, generate_txt_report
from modules.sample_data import generate_corporate_sample_data

# Initialize DB on start
init_db()

# Set styling configurations
ctk.set_appearance_mode("Dark")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

class SmartBIApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("SmartBI • Python AI Assistant")
        self.geometry("1100x700")
        self.minsize(1050, 650)
        
        # Load local settings in memory/session state
        self.ai_config = {
            "api_provider": os.getenv("AI_PROVIDER", "openai").lower(),
            "api_key": os.getenv("AI_API_KEY", os.getenv("OPENAI_API_KEY", "")),
            "model": os.getenv("AI_MODEL", "gpt-4o-mini"),
            "api_url": os.getenv("AI_API_URL", "")
        }
        self.insights_cache = None
        self.active_tab = "dashboard"
        
        # Configure Grid Layout (Left Sidebar: 200px, Right Content: flexible)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Set ttk style for Table (Treeview) matching CTk dark theme
        self.setup_table_style()
        
        # Build layout elements
        self.create_sidebar()
        self.create_content_containers()
        
        # Initialize with dashboard or onboarding
        self.refresh_data()
        
    def setup_table_style(self):
        """Configure standard Tkinter Treeview to match modern slate dark theme."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Colors
        bg_color = "#1E293B"       # Slate 800
        header_bg = "#0F172A"      # Slate 900
        text_color = "#F8FAFC"     # Slate 50
        border_color = "#334155"   # Slate 700
        
        style.configure("Treeview", 
                        background=bg_color, 
                        foreground=text_color, 
                        rowheight=26, 
                        fieldbackground=bg_color,
                        bordercolor=border_color,
                        borderwidth=0)
        style.map("Treeview", background=[("selected", "#2563EB")])  # Blue select
        
        style.configure("Treeview.Heading", 
                        background=header_bg, 
                        foreground=text_color, 
                        relief="flat",
                        font=("Segoe UI", 9, "bold"),
                        bordercolor=border_color)
        
    def create_sidebar(self):
        """Create the left navigation panel."""
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#0F172A")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)
        
        # App Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="SmartBI 📊", 
            font=ctk.CTkFont(family="Outfit", size=24, weight="bold"),
            text_color="#2563EB"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        self.sublogo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Python AI Desktop", 
            font=ctk.CTkFont(family="Outfit", size=11, weight="bold"),
            text_color="#64748B"
        )
        self.sublogo_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Nav Buttons list
        self.nav_buttons = {}
        tabs = [
            ("📊 Dashboard", "dashboard"),
            ("📤 Importar Planilhas", "import"),
            ("🧠 Insights de IA", "ai"),
            ("📝 Relatórios", "reports"),
            ("⚙️ Configurações", "settings")
        ]
        
        for idx, (label, tab_name) in enumerate(tabs):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                anchor="w",
                fg_color="transparent",
                text_color="#94A3B8",
                height=40,
                corner_radius=8,
                command=lambda name=tab_name: self.switch_tab(name)
            )
            btn.grid(row=idx+2, column=0, padx=12, pady=5, sticky="ew")
            self.nav_buttons[tab_name] = btn
            
        # Theme toggle at the bottom
        self.appearance_label = ctk.CTkLabel(self.sidebar_frame, text="Modo de Aparência:", anchor="w")
        self.appearance_label.grid(row=8, column=0, padx=20, pady=(10, 0))
        
        self.appearance_option = ctk.CTkOptionMenu(
            self.sidebar_frame, 
            values=["Dark", "Light", "System"],
            command=self.change_appearance_mode
        )
        self.appearance_option.grid(row=9, column=0, padx=20, pady=(5, 20))
        
    def change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode)
        
    def create_content_containers(self):
        """Create frames for each view, stacked in the right grid cell."""
        self.container_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.container_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.container_frame.grid_columnconfigure(0, weight=1)
        self.container_frame.grid_rowconfigure(0, weight=1)
        
        # Dictionary holding frames
        self.frames = {}
        
        # Create and map each sub-frame
        self.frames["dashboard"] = self.create_dashboard_frame()
        self.frames["import"] = self.create_import_frame()
        self.frames["ai"] = self.create_ai_frame()
        self.frames["reports"] = self.create_reports_frame()
        self.frames["settings"] = self.create_settings_frame()
        self.frames["onboarding"] = self.create_onboarding_frame()
        
    def switch_tab(self, tab_name: str):
        """Perform navigation swaps and update active sidebar triggers."""
        # Clean current views
        for frame in self.frames.values():
            frame.grid_forget()
            
        # Check database data health
        if not self.has_data and tab_name in ["dashboard", "ai", "reports"]:
            self.active_tab = "onboarding"
            self.frames["onboarding"].grid(row=0, column=0, sticky="nsew")
        else:
            self.active_tab = tab_name
            self.frames[tab_name].grid(row=0, column=0, sticky="nsew")
            
        # Update Nav Sidebar Highlights
        for name, btn in self.nav_buttons.items():
            if name == tab_name:
                btn.configure(fg_color="#2563EB", text_color="#F8FAFC")  # Selected Accent Blue
            else:
                btn.configure(fg_color="transparent", text_color="#94A3B8")
                
        # Draw dynamic chart if returning to dashboard
        if tab_name == "dashboard" and self.has_data:
            self.draw_dashboard_charts()
            
    def refresh_data(self):
        """Pull fresh sales from SQLite DB and update application state."""
        self.sales_df = get_all_sales()
        self.has_data = not self.sales_df.empty
        
        # Auto navigate to onboarding if empty
        if not self.has_data:
            self.switch_tab("onboarding")
        else:
            self.switch_tab("dashboard")
            self.update_dashboard_kpis()
            self.populate_dashboard_table()
            
    # ----------------- TAB: ONBOARDING (NO DATA) -----------------
    def create_onboarding_frame(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure((0, 1, 2, 3), weight=1)
        
        # Card container
        card = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=16, border_width=1, border_color="#334155")
        card.grid(row=1, column=0, padx=40, pady=40, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        
        title = ctk.CTkLabel(
            card, 
            text="Bem-vindo ao SmartBI Desktop! 👋", 
            font=ctk.CTkFont(family="Outfit", size=24, weight="bold")
        )
        title.pack(pady=(30, 15))
        
        desc = ctk.CTkLabel(
            card,
            text=(
                "Esta é uma plataforma profissional de Business Intelligence com Inteligência Artificial.\n\n"
                "Como o banco de dados SQLite local está vazio, você pode popular a aplicação:\n"
                "1. Carregando dados corporativos fictícios de vendas com um clique no botão abaixo.\n"
                "2. Fazendo upload manual de planilhas comerciais (Excel/CSV) na aba de Importações."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=13),
            justify="center",
            text_color="#94A3B8"
        )
        desc.pack(pady=15, padx=30)
        
        demo_btn = ctk.CTkButton(
            card,
            text="✨ Carregar Dados de Demonstração (Demo Corporativa)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            height=40,
            command=self.inject_demo_data
        )
        demo_btn.pack(pady=(20, 30))
        
        return frame
        
    def inject_demo_data(self):
        """Generate and save mock business dataset."""
        df = generate_corporate_sample_data()
        import_id = f"demo_{uuid.uuid4().hex[:8]}"
        save_import("planilha_demonstracao_corporativa.xlsx", import_id, df)
        messagebox.showinfo("Sucesso!", "Dados de simulação corporativa injetados no SQLite com sucesso!")
        self.insights_cache = None
        self.refresh_data()
        
    # ----------------- TAB: DASHBOARD -----------------
    def create_dashboard_frame(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        frame.grid_rowconfigure(2, weight=1)  # Grid rows layout
        
        # 1. Header Metrics Cards
        self.kpi_widgets = {}
        kpis_def = [
            ("Faturamento Total", "#F8FAFC", 0),
            ("Lucro Estimado", "#10B981", 1),
            ("Margem Média", "#2563EB", 2),
            ("Unidades Vendidas", "#F8FAFC", 3)
        ]
        
        for title, color, idx in kpis_def:
            card = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
            card.grid(row=0, column=idx, padx=5, pady=5, sticky="nsew")
            
            lbl = ctk.CTkLabel(card, text=title.upper(), font=ctk.CTkFont(size=9, weight="bold"), text_color="#64748B")
            lbl.pack(anchor="w", padx=15, pady=(10, 2))
            
            val = ctk.CTkLabel(card, text="R$ 0,00", font=ctk.CTkFont(family="Outfit", size=18, weight="bold"), text_color=color)
            val.pack(anchor="w", padx=15, pady=(0, 10))
            self.kpi_widgets[title] = val
            
        # 2. Sidebar-like internal Filter Box
        self.filter_frame = ctk.CTkFrame(frame, height=45, fg_color="#1E293B")
        self.filter_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        
        f_lbl = ctk.CTkLabel(self.filter_frame, text="Filtro de Categoria:", font=ctk.CTkFont(size=11, weight="bold"))
        f_lbl.pack(side="left", padx=(15, 5), pady=10)
        
        self.cat_filter_var = ctk.StringVar(value="Todos")
        self.cat_filter_menu = ctk.CTkOptionMenu(
            self.filter_frame, 
            variable=self.cat_filter_var,
            values=["Todos"],
            command=self.apply_dashboard_filters,
            width=150
        )
        self.cat_filter_menu.pack(side="left", padx=5, pady=10)
        
        search_lbl = ctk.CTkLabel(self.filter_frame, text="Buscar Produto:", font=ctk.CTkFont(size=11, weight="bold"))
        search_lbl.pack(side="left", padx=(30, 5), pady=10)
        
        self.search_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="Digite o nome...", width=200)
        self.search_entry.pack(side="left", padx=5, pady=10)
        
        self._search_timer = None
        self.search_entry.bind("<KeyRelease>", self.on_search_keyrelease)
        
        # 3. Double Plot Canvas Frame
        self.charts_frame = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12)
        self.charts_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        
        # 4. Data Grid Explorer (Right side of Charts)
        self.table_frame = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12)
        self.table_frame.grid(row=2, column=2, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(1, weight=1)
        
        t_lbl = ctk.CTkLabel(self.table_frame, text="📋 EXPLORADOR DE VENDAS REGISTRADAS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2563EB")
        t_lbl.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        
        # Treeview grid
        cols = ('date', 'product', 'category', 'revenue', 'margin')
        self.tree = ttk.Treeview(self.table_frame, columns=cols, show='headings', selectmode="browse")
        
        self.tree.heading('date', text='Data')
        self.tree.heading('product', text='Produto')
        self.tree.heading('category', text='Categoria')
        self.tree.heading('revenue', text='Faturamento')
        self.tree.heading('margin', text='Margem')
        
        self.tree.column('date', width=80, anchor='center')
        self.tree.column('product', width=130, anchor='w')
        self.tree.column('category', width=90, anchor='center')
        self.tree.column('revenue', width=90, anchor='e')
        self.tree.column('margin', width=60, anchor='center')
        
        # Scrollbars
        scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        
        self.tree.grid(row=1, column=0, padx=(15, 0), pady=(0, 15), sticky="nsew")
        scroll.grid(row=1, column=1, padx=(0, 15), pady=(0, 15), sticky="ns")
        
        return frame
        
    def update_dashboard_kpis(self):
        """Update value labels dynamically."""
        if not self.has_data:
            return
            
        df = self.get_filtered_dataframe()
        
        total_revenue = df['revenue'].sum()
        total_profit = df['profit'].sum()
        avg_margin = df['margin'].mean() * 100 if not df.empty else 0.0
        total_qty = df['quantity'].sum()
        
        faturamento_formatted = f"R$ {total_revenue:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
        lucro_formatted = f"R$ {total_profit:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
        margem_formatted = f"{avg_margin:.1f}%"
        vendas_formatted = f"{total_qty:,}".replace(',', '.')
        
        self.kpi_widgets["Faturamento Total"].configure(text=faturamento_formatted)
        self.kpi_widgets["Lucro Estimado"].configure(text=lucro_formatted)
        
        margin_widget = self.kpi_widgets["Margem Média"]
        margin_widget.configure(text=margem_formatted)
        if avg_margin < 15:
            margin_widget.configure(text_color="#ef4444")  # Alert Red
        else:
            margin_widget.configure(text_color="#2563EB")  # Standard Premium Blue
            
        self.kpi_widgets["Unidades Vendidas"].configure(text=vendas_formatted)
        
        # Update Categories Filter items dynamically
        categories = ["Todos"] + sorted(self.sales_df['category'].unique().tolist())
        self.cat_filter_menu.configure(values=categories)
        
    def get_filtered_dataframe(self) -> pd.DataFrame:
        """Apply active sidebar/entry filters to in-memory DataFrame."""
        df = self.sales_df.copy()
        
        # 1. Category Filter
        selected_cat = self.cat_filter_var.get()
        if selected_cat != "Todos":
            df = df[df['category'] == selected_cat]
            
        # 2. Text search query
        query = self.search_entry.get().strip()
        if query:
            df = df[
                df['product'].str.contains(query, case=False) | 
                df['category'].str.contains(query, case=False)
            ]
            
        return df
        
    def on_search_keyrelease(self, event):
        if getattr(self, '_search_timer', None) is not None:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(500, self.apply_dashboard_filters)
        
    def apply_dashboard_filters(self, *args):
        self.update_dashboard_kpis()
        self.populate_dashboard_table()
        self.draw_dashboard_charts()
        
    def populate_dashboard_table(self):
        """Load rows into Treeview."""
        # Empty old rows
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        df = self.get_filtered_dataframe()
        if df.empty:
            return
            
        # Sort by date desc
        df = df.sort_values(by="date", ascending=False)
        
        # Insert rows
        for idx, row in df.iterrows():
            rev_fmt = f"R$ {row['revenue']:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
            margin_fmt = f"{row['margin']*100:.1f}%"
            self.tree.insert("", "end", values=(
                row['date'],
                row['product'],
                row['category'],
                rev_fmt,
                margin_fmt
            ))
            
    def draw_dashboard_charts(self):
        """Render modern, beautiful Matplotlib charts inside Tkinter canvas."""
        # Clean up old widgets inside frame first
        for widget in self.charts_frame.winfo_children():
            widget.destroy()
            
        df = self.get_filtered_dataframe()
        if df.empty:
            return
            
        # Setup Figure and Subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6, 3), dpi=100)
        
        # Dark Theme Styling for Plots
        bg_color = "#1E293B"      # Frame matching color
        accent_color = "#2563EB"  # Dark Blue
        profit_color = "#10B981"  # Emerald Green
        text_color = "#94A3B8"    # Gray text
        
        fig.patch.set_facecolor(bg_color)
        
        # Plot 1: Sales Evolution
        df_time = df.groupby('date').agg(
            faturamento=('revenue', 'sum'),
            lucro=('profit', 'sum')
        ).sort_index().reset_index()
        
        ax1.set_facecolor("#0F172A")
        ax1.plot(df_time['date'], df_time['faturamento'], color=accent_color, linewidth=2, label="Receita")
        ax1.fill_between(df_time['date'], df_time['faturamento'], color=accent_color, alpha=0.1)
        ax1.plot(df_time['date'], df_time['lucro'], color=profit_color, linewidth=1.5, linestyle="--", label="Lucro")
        
        ax1.set_title("Evolução Temporal", color="#F8FAFC", fontsize=9, fontweight="bold")
        ax1.tick_params(colors=text_color, labelsize=7)
        # Avoid x-axis label overlap
        if len(df_time) > 4:
            # Show fewer tick labels
            ticks_idx = [0, len(df_time)//2, len(df_time)-1]
            ax1.set_xticks([df_time['date'].iloc[i] for i in ticks_idx])
            ax1.set_xticklabels([df_time['date'].iloc[i] for i in ticks_idx], rotation=15)
        else:
            ax1.tick_params(axis='x', rotation=15)
            
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color("#334155")
        ax1.spines['bottom'].set_color("#334155")
        ax1.grid(color='#334155', linestyle='--', linewidth=0.5, alpha=0.5)
        ax1.legend(facecolor=bg_color, edgecolor="none", fontsize=7, labelcolor="#F8FAFC")
        
        # Plot 2: Category Faturamento
        df_cat = df.groupby('category')['revenue'].sum().nlargest(5).reset_index().sort_values(by="revenue")
        
        ax2.set_facecolor("#0F172A")
        bars = ax2.barh(df_cat['category'], df_cat['revenue'], color=accent_color, height=0.6)
        
        # Highlight top category bar in green if multiple exist
        if len(bars) > 0:
            bars[-1].set_color(profit_color)
            
        ax2.set_title("Faturamento por Categoria", color="#F8FAFC", fontsize=9, fontweight="bold")
        ax2.tick_params(colors=text_color, labelsize=7)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_color("#334155")
        ax2.spines['bottom'].set_color("#334155")
        ax2.grid(color='#334155', linestyle='--', linewidth=0.5, alpha=0.5)
        
        plt.tight_layout()
        
        # Draw on Tkinter canvas
        canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        plt.close(fig)

    # ----------------- TAB: IMPORTAR PLANILHAS -----------------
    def create_import_frame(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        
        # 1. Action Header Box
        actions_box = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
        actions_box.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        title = ctk.CTkLabel(actions_box, text="📤 IMPORTADOR DE PLANILHAS COMERCIAIS", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2563EB")
        title.pack(anchor="w", padx=20, pady=(15, 5))
        
        desc = ctk.CTkLabel(
            actions_box, 
            text="Carregue novos fechamentos de vendas nos formatos Excel (.xlsx) ou arquivos CSV. O SmartBI validará e normalizará os dados automaticamente.",
            text_color="#94A3B8",
            font=ctk.CTkFont(size=11)
        )
        desc.pack(anchor="w", padx=20, pady=(0, 15))
        
        btn_upload = ctk.CTkButton(
            actions_box, 
            text="📂 Selecionar Planilha Excel / CSV", 
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.upload_file_dialog,
            height=35
        )
        btn_upload.pack(anchor="w", padx=20, pady=(0, 20))
        
        # 2. Preview Panel (Hidden until file selected)
        self.preview_box = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
        self.preview_lbl = ctk.CTkLabel(self.preview_box, text="👀 PRÉ-VISUALIZAÇÃO DE LINHAS NORMALIZADAS:", font=ctk.CTkFont(size=11, weight="bold"))
        self.preview_lbl.pack(anchor="w", padx=15, pady=(10, 5))
        
        # Process preview treeview
        p_cols = ('product', 'category', 'price', 'quantity', 'revenue')
        self.preview_tree = ttk.Treeview(self.preview_box, columns=p_cols, show='headings', height=4)
        
        self.preview_tree.heading('product', text='Produto')
        self.preview_tree.heading('category', text='Categoria')
        self.preview_tree.heading('price', text='Preço Unitário')
        self.preview_tree.heading('quantity', text='Quantidade')
        self.preview_tree.heading('revenue', text='Faturamento')
        
        self.preview_tree.column('product', width=180)
        self.preview_tree.column('category', width=100, anchor='center')
        self.preview_tree.column('price', width=100, anchor='e')
        self.preview_tree.column('quantity', width=80, anchor='center')
        self.preview_tree.column('revenue', width=100, anchor='e')
        
        self.preview_tree.pack(fill="x", padx=15, pady=5)
        
        self.btn_save_import = ctk.CTkButton(
            self.preview_box,
            text="💾 Confirmar e Salvar no SQLite",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            command=self.confirm_and_save_import
        )
        self.btn_save_import.pack(anchor="e", padx=15, pady=10)
        
        # 3. History List Panel
        self.history_box = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
        self.history_box.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        self.history_box.grid_columnconfigure(0, weight=1)
        self.history_box.grid_rowconfigure(1, weight=1)
        
        h_lbl = ctk.CTkLabel(self.history_box, text="📜 HISTÓRICO DE LOTES IMPORTADOS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#64748B")
        h_lbl.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        # Scrollable container for history list
        self.history_scroll = ctk.CTkScrollableFrame(self.history_box, fg_color="transparent")
        self.history_scroll.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        
        return frame
        
    def upload_file_dialog(self):
        """Open Windows file chooser, process spreadsheet and display preview."""
        file_path = filedialog.askopenfilename(
            title="Selecionar Planilha de Vendas",
            filetypes=[("Arquivos suportados", "*.xlsx *.xls *.csv"), ("Planilhas Excel", "*.xlsx *.xls"), ("Textos CSV", "*.csv")]
        )
        if not file_path:
            return
            
        try:
            # ETL pipeline
            self.temp_df = process_uploaded_file(file_path)
            self.temp_filename = os.path.basename(file_path)
            
            # Show preview panel
            self.preview_box.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
            
            # Populate preview table
            for item in self.preview_tree.get_children():
                self.preview_tree.delete(item)
                
            for idx, row in self.temp_df.head(4).iterrows():
                pr_fmt = f"R$ {row['price']:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
                rev_fmt = f"R$ {row['revenue']:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
                self.preview_tree.insert("", "end", values=(
                    row['product'],
                    row['category'],
                    pr_fmt,
                    int(row['quantity']),
                    rev_fmt
                ))
                
        except Exception as e:
            messagebox.showerror("Erro de Importação", f"Não foi possível processar este arquivo:\n\n{str(e)}")
            self.preview_box.grid_forget()
            
    def confirm_and_save_import(self):
        """Persist data inside database."""
        if not hasattr(self, 'temp_df') or self.temp_df.empty:
            return
            
        try:
            import_id = f"imp_{uuid.uuid4().hex[:8]}"
            save_import(self.temp_filename, import_id, self.temp_df)
            messagebox.showinfo("Sucesso!", f"Lote de vendas gravado com sucesso! {len(self.temp_df)} linhas inseridas.")
            
            # Cleanup state variables
            self.preview_box.grid_forget()
            delattr(self, 'temp_df')
            self.insights_cache = None
            
            # Sync
            self.refresh_data()
            self.draw_history_list()
        except Exception as e:
            messagebox.showerror("Erro de Gravação", f"Houve uma falha ao persistir no SQLite:\n\n{str(e)}")
            
    def draw_history_list(self):
        """Render history listing in scrollable container dynamically."""
        # Empty past items
        for widget in self.history_scroll.winfo_children():
            widget.destroy()
            
        history = get_import_history()
        if history.empty:
            empty_lbl = ctk.CTkLabel(self.history_scroll, text="Nenhum lote foi importado ainda.", text_color="#64748B", font=ctk.CTkFont(slant="italic"))
            empty_lbl.pack(pady=20)
            return
            
        for idx, row in history.iterrows():
            item_frame = ctk.CTkFrame(self.history_scroll, fg_color="#0F172A", corner_radius=8)
            item_frame.pack(fill="x", pady=4, padx=5)
            
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=8)
            
            file_lbl = ctk.CTkLabel(info_frame, text=f"📄 {row['filename']}", font=ctk.CTkFont(size=12, weight="bold"))
            file_lbl.pack(anchor="w")
            
            meta_lbl = ctk.CTkLabel(
                info_frame, 
                text=f"Código: {row['import_id']}  |  Data: {row['import_date']}  |  Registros: {row['records_count']} vendas",
                text_color="#64748B",
                font=ctk.CTkFont(size=10)
            )
            meta_lbl.pack(anchor="w")
            
            del_btn = ctk.CTkButton(
                item_frame,
                text="🗑️ Excluir",
                width=80,
                height=28,
                fg_color="#EF4444",
                hover_color="#DC2626",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda id=row['import_id']: self.delete_history_batch(id)
            )
            del_btn.pack(side="right", padx=15, pady=8)
            
    def delete_history_batch(self, import_id: str):
        """Remove a lote import."""
        if messagebox.askyesno("Confirmar Exclusão", f"Deseja realmente remover o lote '{import_id}'?\nEsta ação apagará em cascata todas as vendas desse arquivo no SQLite."):
            if delete_import(import_id):
                messagebox.showinfo("Removido", f"O lote '{import_id}' foi removido com sucesso!")
                self.insights_cache = None
                self.refresh_data()
                self.draw_history_list()
            else:
                messagebox.showerror("Erro", "Não foi possível excluir o lote do banco de dados.")

    # ----------------- TAB: IA INSIGHTS -----------------
    def create_ai_frame(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # 1. Action header
        header = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
        header.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        title = ctk.CTkLabel(header, text="🧠 ANÁLISE ESTRATÉGICA DE NEGÓCIOS (IA)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2563EB")
        title.pack(anchor="w", padx=20, pady=(15, 5))
        
        self.ai_status_lbl = ctk.CTkLabel(
            header,
            text=f"Motor de IA: {self.ai_config['api_provider'].upper()}  |  Modelo: {self.ai_config['model']}",
            text_color="#94A3B8",
            font=ctk.CTkFont(size=11)
        )
        self.ai_status_lbl.pack(anchor="w", padx=20, pady=(0, 15))
        
        self.btn_run_ai = ctk.CTkButton(
            header,
            text="🧠 Iniciar Consultoria Comercial Dinâmica",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.run_ai_analysis_thread,
            height=35
        )
        self.btn_run_ai.pack(anchor="w", padx=20, pady=(0, 20))
        
        # 2. Text Box Output
        self.textbox_frame = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
        self.textbox_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Custom CTkTextbox scrollable
        self.ai_textbox = ctk.CTkTextbox(
            self.textbox_frame,
            font=ctk.CTkFont(family="Consolas" if os.name == 'nt' else "Courier", size=12),
            fg_color="#0F172A",
            text_color="#F8FAFC",
            border_width=0,
            corner_radius=8
        )
        self.ai_textbox.pack(fill="both", expand=True, padx=15, pady=15)
        
        return frame
        
    def run_ai_analysis_thread(self):
        """Trigger AI API inside background thread to keep Tkinter GUI active."""
        if not self.has_data:
            messagebox.showwarning("Sem dados", "Importe dados antes de executar a análise de IA.")
            return
            
        self.btn_run_ai.configure(state="disabled", text="⏳ Analisando Indicadores Financeiros...")
        self.ai_textbox.delete("1.0", tk.END)
        self.ai_textbox.insert(tk.END, "🤖 SmartBI AI está consolidando os dados das tabelas SQLite...\n")
        self.ai_textbox.insert(tk.END, "🔗 Enviando KPIs para o motor estratégico de IA...\n\n")
        self.ai_textbox.insert(tk.END, "Aguarde, gerando relatório executivo de negócios em segundo plano...")
        
        # Background worker
        t = threading.Thread(target=self.worker_ai_insights)
        t.daemon = True
        t.start()
        
    def worker_ai_insights(self):
        """Worker thread logic."""
        try:
            insights = generate_ai_insights(self.sales_df, self.ai_config)
            self.insights_cache = insights
            self.after(0, self.success_ai_insights, insights)
        except Exception as e:
            self.after(0, self.error_ai_insights, str(e))
            
    def success_ai_insights(self, insights: str):
        """Main thread callback for successful API return."""
        self.btn_run_ai.configure(state="normal", text="🧠 Iniciar Consultoria Comercial Dinâmica")
        self.ai_textbox.delete("1.0", tk.END)
        self.ai_textbox.insert(tk.END, insights)
        messagebox.showinfo("Sucesso", "Métricas consolidadas e insights gerados pela IA!")
        
    def error_ai_insights(self, err_msg: str):
        """Main thread callback for failures."""
        self.btn_run_ai.configure(state="normal", text="🧠 Iniciar Consultoria Comercial Dinâmica")
        self.ai_textbox.delete("1.0", tk.END)
        self.ai_textbox.insert(tk.END, f"❌ Houve uma falha ao conectar com o provedor de IA.\n\nDetalhes do erro:\n{err_msg}")
        messagebox.showerror("Erro de IA", "Não foi possível completar a chamada de API.")
        
    # ----------------- TAB: REPORTS -----------------
    def create_reports_frame(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        
        card = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
        card.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        title = ctk.CTkLabel(card, text="📝 CENTRAL DE RELATÓRIOS EXECUTIVOS", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2563EB")
        title.pack(anchor="w", padx=20, pady=(15, 5))
        
        desc = ctk.CTkLabel(
            card,
            text="Gere versões formais do relatório comercial consolidadas com o parecer e análise estratégica da IA para apresentar a investidores ou diretores.",
            text_color="#94A3B8",
            font=ctk.CTkFont(size=11)
        )
        desc.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Grid of report downloads
        grids = ctk.CTkFrame(card, fg_color="transparent")
        grids.pack(fill="x", padx=20, pady=(0, 20))
        grids.grid_columnconfigure((0, 1), weight=1)
        
        # PDF Card
        pdf_box = ctk.CTkFrame(grids, fg_color="#0F172A", corner_radius=8, border_width=0.5, border_color="#334155")
        pdf_box.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        pdf_lbl = ctk.CTkLabel(pdf_box, text="📄 Relatório em PDF Corporativo", font=ctk.CTkFont(size=12, weight="bold"))
        pdf_lbl.pack(pady=(15, 5))
        pdf_desc = ctk.CTkLabel(pdf_box, text="Design elegante com tabelas de KPIs e grid de recordistas.", text_color="#64748B", font=ctk.CTkFont(size=10))
        pdf_desc.pack(pady=2)
        
        btn_pdf = ctk.CTkButton(
            pdf_box,
            text="📥 Salvar Relatório PDF",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.export_pdf_report_dialog
        )
        btn_pdf.pack(pady=(15, 15))
        
        # TXT Card
        txt_box = ctk.CTkFrame(grids, fg_color="#0F172A", corner_radius=8, border_width=0.5, border_color="#334155")
        txt_box.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        txt_lbl = ctk.CTkLabel(txt_box, text="📝 Relatório de Backup em TXT", font=ctk.CTkFont(size=12, weight="bold"))
        txt_lbl.pack(pady=(15, 5))
        txt_desc = ctk.CTkLabel(txt_box, text="Texto formatado limpo para arquivamento ou sistemas legados.", text_color="#64748B", font=ctk.CTkFont(size=10))
        txt_desc.pack(pady=2)
        
        btn_txt = ctk.CTkButton(
            txt_box,
            text="📥 Salvar Relatório TXT",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#64748B",
            hover_color="#475569",
            command=self.export_txt_report_dialog
        )
        btn_txt.pack(pady=(15, 15))
        
        return frame
        
    def ensure_insights_available(self) -> bool:
        """Helper to ensure we have the cached strategic insights before printing."""
        if self.insights_cache:
            return True
            
        if messagebox.askyesno("Gerar Análise", "O parecer estratégica de IA ainda não foi calculado para os dados atuais.\nDeseja efetuar uma compilação rápida de IA agora para incluí-la no relatório?"):
            # Run quick block or local statistics fallback
            try:
                self.insights_cache = generate_ai_insights(self.sales_df, self.ai_config)
                return True
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível consolidar insights rápidos:\n{str(e)}")
        return False
        
    def export_pdf_report_dialog(self):
        if not self.has_data:
            return
            
        if not self.ensure_insights_available():
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Salvar Relatório PDF Executivo",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            initialfile=f"SmartBI_Relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        if not file_path:
            return
            
        try:
            filename = os.path.basename(file_path)
            # Override target directory temporarily by running inside absolute path
            generated_path = generate_pdf_report(self.sales_df, self.insights_cache, filename=filename)
            # Copy file to user chosen path
            import shutil
            shutil.move(generated_path, file_path)
            messagebox.showinfo("Exportado!", "Relatório PDF de alta qualidade exportado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro ao exportar", f"Falha na compilação do ReportLab:\n\n{str(e)}")
            
    def export_txt_report_dialog(self):
        if not self.has_data:
            return
            
        if not self.ensure_insights_available():
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Salvar Relatório TXT",
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt")],
            initialfile=f"SmartBI_Relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not file_path:
            return
            
        try:
            filename = os.path.basename(file_path)
            generated_path = generate_txt_report(self.sales_df, self.insights_cache, filename=filename)
            import shutil
            shutil.move(generated_path, file_path)
            messagebox.showinfo("Exportado!", "Relatório de texto formatado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro ao exportar", f"Falha ao gerar arquivo:\n\n{str(e)}")

    # ----------------- TAB: SETTINGS -----------------
    def create_settings_frame(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        
        # 1. Credentials Card
        cred_card = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
        cred_card.pack(fill="x", padx=5, pady=5)
        
        title = ctk.CTkLabel(cred_card, text="⚙️ CONFIGURAÇÕES DE CREDENCIAIS DE IA", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2563EB")
        title.pack(anchor="w", padx=20, pady=(15, 5))
        
        # Provider Option
        p_lbl = ctk.CTkLabel(cred_card, text="Provedor de IA (AI Provider):", font=ctk.CTkFont(size=11, weight="bold"))
        p_lbl.pack(anchor="w", padx=20, pady=(10, 2))
        
        self.p_option = ctk.CTkOptionMenu(
            cred_card, 
            values=["openai", "ollama", "groq", "gemini", "opencode"],
            width=200
        )
        self.p_option.set(self.ai_config["api_provider"])
        self.p_option.pack(anchor="w", padx=20, pady=(0, 10))
        
        # API Key Password
        key_lbl = ctk.CTkLabel(cred_card, text="Chave API (API Key) ou Token:", font=ctk.CTkFont(size=11, weight="bold"))
        key_lbl.pack(anchor="w", padx=20, pady=(5, 2))
        
        self.key_entry = ctk.CTkEntry(cred_card, show="*", placeholder_text="Digite sua chave privada...", width=400)
        self.key_entry.insert(0, self.ai_config["api_key"])
        self.key_entry.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Model Name
        m_lbl = ctk.CTkLabel(cred_card, text="Nome do Modelo (Model Name):", font=ctk.CTkFont(size=11, weight="bold"))
        m_lbl.pack(anchor="w", padx=20, pady=(5, 2))
        
        self.m_entry = ctk.CTkEntry(cred_card, placeholder_text="gpt-4o-mini, llama3, gemini-1.5-flash...", width=300)
        self.m_entry.insert(0, self.ai_config["model"])
        self.m_entry.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Endpoint Custom URL
        url_lbl = ctk.CTkLabel(cred_card, text="Base URL Endpoint Personalizada (Opcional):", font=ctk.CTkFont(size=11, weight="bold"))
        url_lbl.pack(anchor="w", padx=20, pady=(5, 2))
        
        self.url_entry = ctk.CTkEntry(cred_card, placeholder_text="Ex: http://localhost:11434/v1 ou deixe vazio", width=400)
        self.url_entry.insert(0, self.ai_config["api_url"])
        self.url_entry.pack(anchor="w", padx=20, pady=(0, 15))
        
        btn_save = ctk.CTkButton(
            cred_card,
            text="💾 Salvar Configurações de IA",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.save_settings_in_state,
            height=32
        )
        btn_save.pack(anchor="w", padx=20, pady=(0, 20))
        
        # 2. Database Maintenance Card
        db_card = ctk.CTkFrame(frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
        db_card.pack(fill="x", padx=5, pady=10)
        
        db_title = ctk.CTkLabel(db_card, text="🚨 ADMINISTRAÇÃO DO BANCO SQLite LOCAL", font=ctk.CTkFont(size=12, weight="bold"), text_color="#EF4444")
        db_title.pack(anchor="w", padx=20, pady=(15, 5))
        
        db_btn = ctk.CTkButton(
            db_card,
            text="🚨 Apagar Todas as Tabelas (Zerar Banco de Dados)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            command=self.clear_all_sqlite_data,
            height=32
        )
        db_btn.pack(anchor="w", padx=20, pady=(5, 20))
        
        return frame
        
    def save_settings_in_state(self):
        """Persist settings inside RAM and session widgets."""
        self.ai_config = {
            "api_provider": self.p_option.get().lower(),
            "api_key": self.key_entry.get().strip(),
            "model": self.m_entry.get().strip(),
            "api_url": self.url_entry.get().strip()
        }
        self.insights_cache = None
        self.ai_status_lbl.configure(text=f"Motor de IA: {self.ai_config['api_provider'].upper()}  |  Modelo: {self.ai_config['model']}")
        messagebox.showinfo("Atualizado", "As credenciais de IA foram salvas localmente para a sessão ativa!")
        
    def clear_all_sqlite_data(self):
        """Wipe databases clean."""
        if messagebox.askyesno("Destrutivo - Atenção!", "Esta ação removerá de forma definitiva e irrecuperável todas as tabelas, históricos e registros financeiros salvos no SQLite.\n\nDeseja prosseguir?"):
            if clear_all_data():
                messagebox.showinfo("Banco Zerado", "Tabelas limpas com sucesso!")
                self.insights_cache = None
                self.refresh_data()
                self.draw_history_list()

if __name__ == "__main__":
    app = SmartBIApp()
    # Initial drawing of batch files lists
    app.draw_history_list()
    app.mainloop()
