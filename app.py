import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import os
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="DataCalc Andrello", page_icon="logo.png", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/15XPXTSPsNG0jNAA8Mc854E55wng03F8p6r7DamCwedk/edit?usp=sharing"

# --- SISTEMA DE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acesso Restrito - DataCalc")
        senha = st.text_input("Digite a senha de acesso", type="password")
        if st.button("Entrar"):
            if senha == "1234": # <--- SUA SENHA
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
        return False
    return True

if check_password():
    # --- CLASSE DO PDF ---
    class PDF(FPDF):
        def header(self):
            if os.path.exists("logo.png"):
                self.image("logo.png", 10, 4, 30) # Logo na esquerda
                
            self.set_font('Arial', 'B', 15)
            self.cell(80) 
            self.cell(30, 10, 'Relatório de Antecipação', 0, 0, 'C')
            self.ln(20)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    def gerar_pdf(nome_cliente, df_dados, t_bruto, t_juros, t_liq, taxa):
        pdf = PDF()
        pdf.add_page()
        
        # 1. Nome do Cliente com fundo azul claro
        pdf.set_fill_color(200, 220, 255) 
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f"CLIENTE: {nome_cliente.upper()}", ln=True, fill=True, align='C')
        pdf.ln(5)
        
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, txt=f"Data: {date.today().strftime('%d/%m/%Y')}", ln=True)
        pdf.cell(0, 10, txt=f"Taxa Mensal: {taxa}%", ln=True)
        pdf.ln(5)
        
        # 2. Cabeçalho da Tabela
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(40, 10, "Valor Original", 1, 0, 'C', True)
        pdf.cell(40, 10, "Vencimento", 1, 0, 'C', True)
        pdf.cell(20, 10, "Dias", 1, 0, 'C', True)
        pdf.cell(40, 10, "Desconto", 1, 0, 'C', True)
        pdf.cell(40, 10, "Liquido", 1, 1, 'C', True)
        
        # 3. Dados
        pdf.set_font("Arial", size=10)
        for _, row in df_dados.iterrows():
            pdf.cell(40, 10, f"R$ {row['Valor Original']:,.2f}", 1, 0, 'C')
            pdf.cell(40, 10, f"{row['Vencimento']}", 1, 0, 'C')
            pdf.cell(20, 10, f"{row['Dias']}", 1, 0, 'C')
            pdf.cell(40, 10, f"R$ {row['Juros']:,.2f}", 1, 0, 'C')
            pdf.cell(40, 10, f"R$ {row['Líquido']:,.2f}", 1, 1, 'C')
        
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        
        # 4. Totais Coloridos no PDF
        pdf.set_text_color(0, 0, 0) # Preto
        pdf.cell(0, 10, f"TOTAL BRUTO: R$ {t_bruto:,.2f}", ln=True)

        pdf.set_text_color(255, 0, 0) # Vermelho
        pdf.cell(0, 10, f"TOTAL DESCONTOS: R$ {t_juros:,.2f}", ln=True)

        pdf.set_text_color(0, 128, 0) # Verde
        pdf.cell(0, 10, f"VALOR LÍQUIDO A RECEBER: R$ {t_liq:,.2f}", ln=True)
        
        pdf.set_text_color(0, 0, 0) # Volta para preto
        return pdf.output(dest='S').encode('latin-1')

    # --- BARRA LATERAL ---
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", width=200)
    st.sidebar.divider()
    st.sidebar.info(f"📅 Hoje: {date.today().strftime('%d/%m/%Y')}")
    st.sidebar.button("Sair", on_click=lambda: st.session_state.clear())
    
    # --- ABAS ---
    aba1, aba2 = st.tabs(["📊 Nova Operação", "🔍 Histórico Permanente"])

    with aba1:
        st.title("Calculadora de Antecipação")
        col1, col2 = st.columns([2, 1])
        nome_cliente = col1.text_input("Nome do Cliente")
        taxa_mensal = col2.selectbox("Taxa Mensal (%)", [2.0, 2.5, 2.8, 3.0, 3.5, 4.0, 5.0], index=1)
        taxa_diaria = (taxa_mensal / 100) / 30

        if 'cheques' not in st.session_state: st.session_state['cheques'] = []

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            val = c1.number_input("Valor (R$)", min_value=0.0)
            venc = c2.date_input("Vencimento", date.today())
            if c3.button("➕ Adicionar"):
                dias = (venc - date.today()).days
                if dias >= 0 and val > 0:
                    juros = val * (taxa_diaria * dias)
                    st.session_state['cheques'].append({
                        "Valor Original": val, "Vencimento": venc.strftime("%d/%m/%Y"),
                        "Dias": dias, "Juros": juros, "Líquido": val - juros
                    })
                    st.rerun()

        if st.session_state['cheques']:
            df = pd.DataFrame(st.session_state['cheques'])
            st.table(df.style.format({"Valor Original": "R$ {:.2f}", "Juros": "R$ {:.2f}", "Líquido": "R$ {:.2f}"}))
            
            t_bruto, t_juros, t_liq = df["Valor Original"].sum(), df["Juros"].sum(), df["Líquido"].sum()
            
            # --- TOTAIS COLORIDOS NO APP ---
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Bruto", f"R$ {t_bruto:,.2f}")
            c2.metric("Total Juros", f"R$ {t_juros:,.2f}")
            c3.metric("Total Líquido", f"R$ {t_liq:,.2f}")

            st.markdown("""
                <style>
                div[data-testid="metric-container"]:nth-child(2) [data-testid="stMetricValue"] { color: red; }
                div[data-testid="metric-container"]:nth-child(3) [data-testid="stMetricValue"] { color: green; }
                </style>
            """, unsafe_allow_html=True)
            
            # Botões
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("💾 Salvar na Nuvem"):
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        existente = conn.read(spreadsheet=URL_PLANILHA)
                        novo = pd.DataFrame([{
                            "Data Operação": date.today().strftime("%d/%m/%Y"),
                            "Cliente": nome_cliente, "Total Bruto": t_bruto,
                            "Total Juros": t_juros, "Total Líquido": t_liq
                        }])
                        atualizado = pd.concat([existente, novo], ignore_index=True)
                        conn.update(spreadsheet=URL_PLANILHA, data=atualizado)
                        st.success("Salvo com sucesso!")
                        st.session_state['cheques'] = []
                    except Exception as e:
                        st.error(f"Erro: {e}")

            with col_b2:
                pdf_data = gerar_pdf(nome_cliente, df, t_bruto, t_juros, t_liq, taxa_mensal)
                st.download_button(
                    label="📄 Baixar PDF",
                    data=pdf_data,
                    file_name=f"Relatorio_{nome_cliente}.pdf",
                    mime="application/pdf"
                )

    with aba2:
        st.subheader("🔍 Histórico de Operações")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_historico = conn.read(spreadsheet=URL_PLANILHA, ttl="0s")
            
            if not df_historico.empty:
                f_cliente = st.text_input("Filtrar por Cliente")
                if f_cliente:
                    df_historico = df_historico[df_historico['Cliente'].str.contains(f_cliente, case=False)]
                
                st.dataframe(df_historico.style.format({
                    "Total Bruto": "R$ {:.2f}", "Total Juros": "R$ {:.2f}", "Total Líquido": "R$ {:.2f}"
                }), use_container_width=True)
            else:
                st.info("Planilha vazia.")
        except:
            st.error("Erro ao carregar dados.")