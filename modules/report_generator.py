import os
import re
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Define base folder relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "data", "reports")

def ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)

def parse_inline_markdown(text: str) -> str:
    """Convert bold, italic, and key symbols from Markdown to HTML tags for ReportLab."""
    # Escape standard XML characters
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # Restore HTML-like markup we want to inject
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'`(.*?)`', r'<font face="Courier"><b>\1</b></font>', text)
    # Fix back the XML tags we replaced if they are ReportLab markup
    text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
    text = text.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
    text = text.replace('&lt;font', '<font').replace('&lt;/font&gt;', '</font>')
    return text

def markdown_to_reportlab_paragraphs(md_text: str, styles) -> list:
    """Convert standard markdown structures to ReportLab Flowables.
    Handles headers, bullet points, alerts, and bold text.
    """
    flowables = []
    
    h2_style = ParagraphStyle(
        'MD_H2',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'), # Slate 900
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h3_style = ParagraphStyle(
        'MD_H3',
        parent=styles['Heading3'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E293B'), # Slate 800
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'MD_Body',
        parent=styles['BodyText'],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155'), # Slate 700
        spaceAfter=5
    )
    
    bullet_style = ParagraphStyle(
        'MD_Bullet',
        parent=styles['BodyText'],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    
    alert_style = ParagraphStyle(
        'MD_Alert',
        parent=styles['BodyText'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1E293B'),
        backColor=colors.HexColor('#F8FAFC'),
        borderColor=colors.HexColor('#E2E8F0'),
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=8
    )
    
    lines = md_text.split('\n')
    in_alert = False
    alert_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Parse alerts (like blockquotes or custom alert tags)
        if line.startswith('>') or line.startswith('[!'):
            in_alert = True
            clean_line = line.replace('>', '').replace('[!NOTE]', '').replace('[!WARNING]', '').replace('[!IMPORTANT]', '').strip()
            alert_lines.append(clean_line)
            continue
        elif in_alert and not line.startswith('>') and not line.startswith('[!'):
            # Close alert flowable
            alert_text = " ".join(alert_lines)
            alert_text = parse_inline_markdown(alert_text)
            flowables.append(Paragraph(f"<b>Aviso:</b> {alert_text}", alert_style))
            flowables.append(Spacer(1, 4))
            in_alert = False
            alert_lines = []
            
        # Convert headers
        if line.startswith('## '):
            title = line[3:].strip()
            flowables.append(Paragraph(title, h2_style))
        elif line.startswith('### '):
            title = line[4:].strip()
            flowables.append(Paragraph(title, h3_style))
        # Convert bullets
        elif line.startswith('* ') or line.startswith('- '):
            bullet_content = line[2:].strip()
            bullet_content = parse_inline_markdown(bullet_content)
            flowables.append(Paragraph(f"&bull; {bullet_content}", bullet_style))
        elif re.match(r'^\d+\.\s', line):
            match = re.match(r'^(\d+\.)\s(.*)', line)
            num = match.group(1)
            content = match.group(2)
            content = parse_inline_markdown(content)
            flowables.append(Paragraph(f"<b>{num}</b> {content}", bullet_style))
        else:
            text = parse_inline_markdown(line)
            flowables.append(Paragraph(text, body_style))
            
    # Handle end of file alert check
    if in_alert and alert_lines:
        alert_text = " ".join(alert_lines)
        alert_text = parse_inline_markdown(alert_text)
        flowables.append(Paragraph(f"<b>Destaque:</b> {alert_text}", alert_style))
        
    return flowables

def generate_pdf_report(df: pd.DataFrame, insights: str, filename: str = None) -> str:
    """Create a gorgeous executive PDF report with metrics table and AI insights."""
    ensure_reports_dir()
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"SmartBI_Relatorio_{timestamp}.pdf"
        
    file_path = os.path.join(REPORTS_DIR, filename)
    
    # Standard margins (36 pt = 0.5 in)
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        leftMargin=36, rightMargin=36,
        topMargin=36, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    # Colors
    primary_color = colors.HexColor('#0F172A')   # Slate 900
    secondary_color = colors.HexColor('#2563EB') # Indigo Blue
    text_dark = colors.HexColor('#1E293B')       # Slate 800
    bg_light = colors.HexColor('#F8FAFC')        # Slate 50
    border_color = colors.HexColor('#E2E8F0')    # Slate 200
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=2,
        keepWithNext=True
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=12,
        keepWithNext=True
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=15,
        textColor=secondary_color,
        spaceBefore=14,
        spaceAfter=6,
        borderColor=secondary_color,
        borderWidth=0.5,
        borderPadding=2,
        keepWithNext=True
    )
    
    cell_style = ParagraphStyle(
        'GridCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=text_dark
    )
    
    cell_header_style = ParagraphStyle(
        'GridHeaderCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )
    
    # Cover / Header
    story.append(Paragraph("SmartBI • AI Business Intelligence Assistant", title_style))
    date_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
    story.append(Paragraph(f"RELATÓRIO DE PERFORMANCE EXECUTIVA — Gerado em {date_str}", subtitle_style))
    story.append(Spacer(1, 6))
    
    # KPI Grid
    total_rev = df['revenue'].sum()
    total_prof = df['profit'].sum()
    total_cost = (df['cost'] * df['quantity']).sum()
    avg_margin = df['margin'].mean() * 100
    
    kpi_data = [
        [
            Paragraph("<b>Faturamento Total</b>", cell_style),
            Paragraph("<b>Custo de Vendas</b>", cell_style),
            Paragraph("<b>Lucro Estimado</b>", cell_style),
            Paragraph("<b>Margem Média</b>", cell_style)
        ],
        [
            f"R$ {total_rev:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'),
            f"R$ {total_cost:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'),
            f"R$ {total_prof:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'),
            f"{avg_margin:.1f}%"
        ]
    ]
    
    kpi_table = Table(kpi_data, colWidths=[135]*4)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), bg_light),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,1), (-1,1), 11),
        ('TEXTCOLOR', (0,1), (0,1), secondary_color),
        ('TEXTCOLOR', (2,1), (2,1), colors.HexColor('#16A34A')),
    ]))
    
    story.append(kpi_table)
    story.append(Spacer(1, 10))
    
    # Top Products Table
    story.append(Paragraph("PRODUTOS LÍDERES EM FATURAMENTO", section_title_style))
    
    top_products = df.groupby('product').agg(
        total_revenue=('revenue', 'sum'),
        total_qty=('quantity', 'sum'),
        avg_margin=('margin', 'mean')
    ).nlargest(5, 'total_revenue').reset_index()
    
    product_headers = [
        Paragraph("Produto", cell_header_style),
        Paragraph("Qtd. Vendida", cell_header_style),
        Paragraph("Margem Média", cell_header_style),
        Paragraph("Faturamento Total", cell_header_style)
    ]
    
    table_rows = [product_headers]
    for idx, row in top_products.iterrows():
        table_rows.append([
            Paragraph(str(row['product']), cell_style),
            Paragraph(f"{int(row['total_qty']):,}", cell_style),
            Paragraph(f"{row['avg_margin']*100:.1f}%", cell_style),
            Paragraph(f"R$ {row['total_revenue']:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'), cell_style)
        ])
        
    prod_table = Table(table_rows, colWidths=[200, 100, 100, 140])
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
    ]))
    
    story.append(prod_table)
    story.append(Spacer(1, 10))
    
    # AI Insights
    story.append(Paragraph("ANÁLISE E DIRETRIZES DA INTELIGÊNCIA ARTIFICIAL", section_title_style))
    
    insight_flowables = markdown_to_reportlab_paragraphs(insights, styles)
    story.extend(insight_flowables)
    
    # Canvas decorations for Page numbers
    def add_page_decorations(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748B'))
        
        # Header running line
        canvas.setStrokeColor(border_color)
        canvas.setLineWidth(0.5)
        canvas.line(36, doc.pagesize[1] - 30, doc.pagesize[0] - 36, doc.pagesize[1] - 30)
        canvas.drawString(36, doc.pagesize[1] - 25, "SmartBI Python AI Assistant — Relatório de BI")
        
        # Footer
        canvas.line(36, 40, doc.pagesize[0] - 36, 40)
        canvas.drawString(36, 25, "Relatório Corporativo — Confidencial")
        canvas.drawRightString(doc.pagesize[0] - 36, 25, f"Página {doc.page}")
        canvas.restoreState()
        
    doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
    return file_path

def generate_txt_report(df: pd.DataFrame, insights: str, filename: str = None) -> str:
    """Create a clean, beautifully formatted Text report as a robust fallback."""
    ensure_reports_dir()
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"SmartBI_Relatorio_{timestamp}.txt"
        
    file_path = os.path.join(REPORTS_DIR, filename)
    
    # KPIs
    total_rev = df['revenue'].sum()
    total_prof = df['profit'].sum()
    total_cost = (df['cost'] * df['quantity']).sum()
    avg_margin = df['margin'].mean() * 100
    
    top_products = df.groupby('product').agg(
        total_revenue=('revenue', 'sum'),
        total_qty=('quantity', 'sum'),
        avg_margin=('margin', 'mean')
    ).nlargest(5, 'total_revenue').reset_index()
    
    txt_content = []
    txt_content.append("="*80)
    txt_content.append(" " * 20 + "SMARTBI - RELATÓRIO EXECUTIVO DE NEGÓCIOS")
    txt_content.append("="*80)
    txt_content.append(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
    txt_content.append("-"*80)
    txt_content.append("\n[1] MÉTRICAS FINANCEIRAS GERAIS")
    txt_content.append(f"  * Faturamento Total: R$ {total_rev:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'))
    txt_content.append(f"  * Custo de Vendas:   R$ {total_cost:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'))
    txt_content.append(f"  * Lucro Estimado:    R$ {total_prof:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'))
    txt_content.append(f"  * Margem Média:      {avg_margin:.1f}%")
    txt_content.append("\n" + "-"*80)
    txt_content.append("\n[2] TOP 5 PRODUTOS EM FATURAMENTO")
    txt_content.append(f"  {'Produto':<30} | {'Qtd Vendida':<12} | {'Margem Média':<12} | {'Faturamento Total':<18}")
    txt_content.append("  " + "-"*75)
    for idx, row in top_products.iterrows():
        p_name = row['product'][:30]
        p_revenue = f"R$ {row['total_revenue']:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
        txt_content.append(f"  {p_name:<30} | {int(row['total_qty']):<12,} | {row['avg_margin']*100:>10.1f}% | {p_revenue:>18}")
        
    txt_content.append("\n" + "-"*80)
    # Remove markdown tags from text report for neatness
    clean_insights = re.sub(r'#+\s*', '', insights)
    clean_insights = re.sub(r'\*+\s*', '* ', clean_insights)
    clean_insights = re.sub(r'>\s*', '', clean_insights)
    
    txt_content.append("\n[3] ANÁLISE DE NEGÓCIOS E RECOMENDAÇÕES DA IA")
    txt_content.append("\n" + clean_insights)
    txt_content.append("\n" + "="*80)
    txt_content.append(" " * 28 + "CONFIDENCIAL — SMARTBI CO.")
    txt_content.append("="*80)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(txt_content))
        
    return file_path
