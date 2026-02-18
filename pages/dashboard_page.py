import streamlit as st
import pandas as pd
import datetime 
import plotly.express as px
import plotly.graph_objects as go
import numpy as np 

# --- KONSTANTA GLOBAL ---
STT_DUMMY_MESIN = "STT_DUMMY_OUTPUT" 
BERAT_PER_PCS_KG = 0.075 
ALL_AVAILABLE_SHIFTS = ['Semua Shift', 'Shift 1', 'Shift 2', 'Shift 3', 'Shift Tidak Tercatat'] 
TARGET_SHIFT_TOTAL = 6746 

# ====================================================================
# --- FUNGSI PENDUKUNG ---
# ====================================================================

def create_pareto_chart(df, weight_col, category_col, title):
    if df.empty: return None
    df_agg = df.groupby(category_col)[weight_col].sum().reset_index()
    df_agg = df_agg.sort_values(by=weight_col, ascending=False).reset_index(drop=True)
    total_sum = df_agg[weight_col].sum()
    if total_sum == 0: return None
    
    df_agg['Cumulative_Percent'] = (df_agg[weight_col].cumsum() / total_sum) * 100
    fig = px.bar(df_agg, x=category_col, y=weight_col, title=title, 
                  text_auto=".2f", color_discrete_sequence=['#3366CC']) 
    fig.add_scatter(x=df_agg[category_col], y=df_agg['Cumulative_Percent'], 
                    mode='lines+markers', name='Kumulatif (%)', yaxis='y2', 
                    line=dict(color='#DC3912', width=3))
    fig.update_layout(yaxis2=dict(title='Kumulatif (%)', side='right', overlaying='y', range=[0, 105]),
                      hovermode="x unified", showlegend=False, margin=dict(l=20, r=20, t=50, b=20))
    return fig

@st.cache_data(ttl=300)
def get_processed_data():
    try:
        from utils import load_data
        df = load_data()
    except:
        return pd.DataFrame()
    if df is None or df.empty: return pd.DataFrame()
    if "Tanggal" in df.columns:
        df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce").dt.date
        df = df.dropna(subset=['Tanggal'])
    for col in ["Shift", "Mesin", "Varian", "Jenis Reject"]:
        if col in df.columns:
            df[col] = df[col].fillna('N/A').astype(str).str.strip()
    for col in ["Total Reject", "STT Waste (Kg)", "Output (pcs)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df

# ====================================================================
# --- DASHBOARD UTAMA ---
# ====================================================================

def run_dashboard():
    st.set_page_config(page_title="Dashboard Produksi Terpadu", layout="wide")
    
    st.markdown("""
        <style>
        div[data-testid="metric-container"] {
            background-color: #161b22; border: 1px solid #30363d;
            padding: 15px; border-radius: 10px;
        }
        [data-testid="stMetricValue"] { font-size: 24px !important; color: #58a6ff !important; }
        .stSubheader { color: #f0f6fc !important; font-weight: bold; margin-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("📑 Dashboard Monitoring Produksi")
    st.subheader("📌 Key Performance Indicators (KPI)")
    st.markdown("---")

    df_full = get_processed_data()
    if df_full.empty:
        st.warning("Data tidak tersedia.")
        return

    with st.sidebar:
        st.header("⚙️ Filter Panel")
        if st.button("🔄 Sinkronkan Data"):
            st.cache_data.clear()
            st.rerun()
        start_date = st.date_input("Mulai", value=df_full["Tanggal"].min())
        end_date = st.date_input("Sampai", value=df_full["Tanggal"].max())
        sel_shift = st.selectbox("Pilih Shift", options=ALL_AVAILABLE_SHIFTS)

    mask = (df_full["Tanggal"] >= start_date) & (df_full["Tanggal"] <= end_date)
    if sel_shift != 'Semua Shift':
        shift_keyword = sel_shift.split()[-1] if 'Shift' in sel_shift else sel_shift
        mask = mask & (df_full["Shift"].str.contains(shift_keyword, na=False))
    df_filtered = df_full[mask].copy()

    df_out = df_filtered[df_filtered["Jenis Reject"] == STT_DUMMY_MESIN]
    df_rej = df_filtered[df_filtered["Jenis Reject"] != STT_DUMMY_MESIN]

    t_out_pcs = df_out["Output (pcs)"].sum()
    t_stt_kg = df_out["STT Waste (Kg)"].sum()
    t_rej_op = df_rej["Total Reject"].sum()
    selisih = t_stt_kg - t_rej_op
    total_prod_kg = (t_out_pcs * BERAT_PER_PCS_KG) + t_stt_kg
    waste_pct = (t_stt_kg / total_prod_kg * 100) if total_prod_kg > 0 else 0

    kpi_cols = st.columns(5)
    kpi_cols[0].metric("Total Output", f"{t_out_pcs:,.0f} Pcs")
    kpi_cols[1].metric("Reject Lapangan", f"{t_rej_op:,.2f} Kg")
    kpi_cols[2].metric("STT Waste (Audit)", f"{t_stt_kg:,.2f} Kg")
    kpi_cols[3].metric("Selisih Waste", f"{selisih:,.2f} Kg", delta="⚠️ Cek" if abs(selisih) > 0.1 else "✅ OK", delta_color="inverse")
    kpi_cols[4].metric("Waste Rate (%)", f"{waste_pct:.2f}%")

    st.markdown("---")

    # --- BARIS 1 ---
    st.subheader("📦 Rincian Performa Produksi")
    col_v1, col_v2 = st.columns([2, 1])
    
    with col_v1:
        if not df_out.empty:
            df_out_var = df_out.groupby("Varian")["Output (pcs)"].sum().reset_index()
            ach_total_pct = (t_out_pcs / TARGET_SHIFT_TOTAL) * 100
            
            if ach_total_pct >= 92.5:
                res_color = '#238636'
                status_txt = "SANGAT BAIK"
            elif 87.5 <= ach_total_pct <= 91.9:
                res_color = '#3366CC'
                status_txt = "STANDAR"
            elif 10 <= ach_total_pct <= 86.9:
                res_color = '#FFD700'
                status_txt = "WARNING (UNDER TARGET)"
            else:
                res_color = '#808080'
                status_txt = "LOW OUTPUT"

            st.markdown(f"""
                <div style="background-color:{res_color}; padding:15px; border-radius:10px; text-align:center; margin-bottom:15px;">
                    <h1 style="color:white; margin:0; font-size:45px;">{ach_total_pct:.2f}%</h1>
                    <p style="color:white; margin:0; font-weight:bold; font-size:16px;">{status_txt}</p>
                </div>
            """, unsafe_allow_html=True)

            fig_out = px.bar(df_out_var, x="Output (pcs)", y="Varian", orientation='h',
                             text_auto=',.0f', color_discrete_sequence=[res_color])
            fig_out.update_traces(textposition='outside')
            fig_out.update_layout(showlegend=False, height=350, margin=dict(l=10, r=60, t=10, b=10),
                                  xaxis=dict(range=[0, max(t_out_pcs, TARGET_SHIFT_TOTAL) * 1.1]))
            st.plotly_chart(fig_out, use_container_width=True)

    with col_v2:
        # LOGIKA REJECT & SKALA DETAIL
        if waste_pct <= 2.0:
            gauge_bar_color = "#238636" # Hijau
        elif waste_pct > 3.5:
            gauge_bar_color = "#3366CC" # Biru
        else:
            gauge_bar_color = "white"   # Netral

        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = waste_pct,
            title = {'text': "Waste Rate Target (%)", 'font': {'size': 18}},
            gauge = {
                # DISINI PERBAIKAN SKALANYA (Tickvals)
                'axis': {
                    'range': [0, 10], 
                    'tickvals': [0, 2, 3.5, 5, 7.5, 10], # Menampilkan angka 2 dan 3.5 secara eksplisit
                    'ticktext': ["0", "2%", "3.5%", "5", "7.5", "10"],
                    'tickwidth': 2
                },
                'bar': {'color': gauge_bar_color},
                'steps': [
                    {'range': [0, 2], 'color': "#c6e5cf"},   # Area Hijau
                    {'range': [2, 3.5], 'color': "white"},   # Area Transisi
                    {'range': [3.5, 10], 'color': "#D0E1F9"} # Area Biru
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 3},
                    'thickness': 0.75,
                    'value': 3.5 # Garis merah di batas 3.5%
                }
            }))
        fig_gauge.update_layout(height=400, margin=dict(l=30, r=30, t=50, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # --- BARIS 2 & 3 ---
    st.markdown("---")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("📊 Reject per Varian (Kg)")
        if not df_rej.empty:
            df_rej_var = df_rej.groupby("Varian")["Total Reject"].sum().reset_index().sort_values("Total Reject")
            fig_rej_var = px.bar(df_rej_var, y="Varian", x="Total Reject", orientation='h', 
                                 text_auto='.2f', color_discrete_sequence=['#8A2BE2'])
            st.plotly_chart(fig_rej_var, use_container_width=True)
    
    with col_r2:
        st.subheader("🌍 Proporsi Berat Total (Kg)")
        fig_pie = px.pie(values=[t_out_pcs * BERAT_PER_PCS_KG, t_stt_kg], 
                         names=['Produk Jadi', 'Total Waste'],
                         hole=0.5, color_discrete_sequence=['#238636', '#da3633'])
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("📉 Pareto Masalah Reject")
        fig_p = create_pareto_chart(df_rej, "Total Reject", "Jenis Reject", "")
        if fig_p: st.plotly_chart(fig_p, use_container_width=True)
    with col_p2:
        st.subheader("🔧 Detail Reject per Mesin")
        if not df_rej.empty:
            df_mesin = df_rej.groupby(["Mesin", "Varian"]).agg({'Total Reject': 'sum'}).reset_index()
            st.dataframe(df_mesin.sort_values("Total Reject", ascending=False), use_container_width=True, height=350)

if __name__ == "__main__":
    run_dashboard()