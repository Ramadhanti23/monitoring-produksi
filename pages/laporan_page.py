import streamlit as st
import pandas as pd
import io
import datetime
import plotly.express as px
# Import switch_page untuk navigasi balik ke login
from streamlit_extras.switch_page_button import switch_page 

# --- KONSTANTA LOKAL ---
STT_DUMMY_MESIN = "STT_DUMMY_OUTPUT"
BERAT_PER_PCS_KG = 0.075

def get_data_laporan():
    """Fungsi mandiri untuk mengambil data tanpa error import"""
    try:
        from utils import load_data
        df = load_data()
        if df is not None and not df.empty:
            df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce").dt.date
            df = df.dropna(subset=['Tanggal'])
            for col in ["Total Reject", "STT Waste (Kg)", "Output (pcs)"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
    return pd.DataFrame()

def run_laporan():
    # --- 1. PROTEKSI HALAMAN & SIDEBAR LOGOUT ---
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        switch_page("app")
        st.stop()

    with st.sidebar:
        st.markdown("---")
        st.write(f"👤 Akun: **{st.session_state.get('username', 'Admin')}**")
        if st.button("🚪 Logout / Keluar", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.session_state.username = None
            switch_page("app") 
        st.markdown("---")

    # --- 2. KONFIGURASI HALAMAN ---
    st.title("📄 Laporan Harian Produksi & Waste")
    st.markdown("Halaman ini menyajikan ringkasan performa antar shift dan sinkronisasi data audit.")
    st.markdown("---")

    df_full = get_data_laporan()
    if df_full.empty:
        st.warning("Data tidak tersedia.")
        return

    # --- FILTER PANEL ---
    with st.expander("🔍 Filter Laporan (Periode & Shift)", expanded=True):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            start_date = st.date_input("Mulai", value=df_full["Tanggal"].min())
        with col_b:
            end_date = st.date_input("Sampai", value=df_full["Tanggal"].max())
        with col_c:
            list_shift = ["Semua Shift"] + sorted(df_full["Shift"].unique().tolist())
            sel_shift = st.selectbox("Pilih Shift", list_shift)

    mask = (df_full["Tanggal"] >= start_date) & (df_full["Tanggal"] <= end_date)
    if sel_shift != "Semua Shift":
        mask = mask & (df_full["Shift"] == sel_shift)
    
    df_filtered = df_full[mask].copy()

    if df_filtered.empty:
        st.info("Tidak ada data untuk filter yang dipilih.")
        return

    # --- PENGOLAHAN DATA ---
    df_out = df_filtered[df_filtered["Jenis Reject"] == STT_DUMMY_MESIN]
    df_rej = df_filtered[df_filtered["Jenis Reject"] != STT_DUMMY_MESIN]

    summary = df_out.groupby(["Tanggal", "Shift"]).agg({
        "Output (pcs)": "sum",
        "STT Waste (Kg)": "sum"
    }).reset_index()

    rej_val = df_rej.groupby(["Tanggal", "Shift"])["Total Reject"].sum().reset_index()
    report_final = pd.merge(summary, rej_val, on=["Tanggal", "Shift"], how="left").fillna(0)
    
    report_final["Selisih (Kg)"] = report_final["STT Waste (Kg)"] - report_final["Total Reject"]
    report_final["Waste (%)"] = (report_final["STT Waste (Kg)"] / 
                                ((report_final["Output (pcs)"] * BERAT_PER_PCS_KG) + report_final["STT Waste (Kg)"]) * 100).fillna(0)

    # --- BAGIAN GRAFIK KOMPARASI DENGAN DATA LABELS ---
    st.subheader("📊 Analisis Komparasi Antar Shift")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        # Menambahkan text_auto untuk menampilkan label angka langsung di atas batang
        fig_shift_out = px.bar(report_final, x="Shift", y="Output (pcs)", color="Shift",
                               title="Total Output (Pcs) per Shift",
                               text_auto=',.0f', # Label angka ribuan
                               color_discrete_sequence=px.colors.qualitative.Pastel)
        
        fig_shift_out.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
        st.plotly_chart(fig_shift_out, use_container_width=True)
        
        max_out_row = report_final.loc[report_final['Output (pcs)'].idxmax()]
        st.info(f"💡 **Insight Produksi:** Output tertinggi dicapai oleh **{max_out_row['Shift']}** sebesar **{max_out_row['Output (pcs)']:,.0f} pcs**.")

    with col_g2:
        # Menambahkan text_auto untuk menampilkan label persentase langsung di atas batang
        fig_shift_waste = px.bar(report_final, x="Shift", y="Waste (%)", color="Shift",
                                 title="Waste Rate (%) per Shift",
                                 text_auto='.2f', # Label persen 2 desimal
                                 color_discrete_sequence=px.colors.qualitative.Safe)
        
        # PERUBAHAN: Batas Maksimal diubah ke 2%
        fig_shift_waste.add_hline(y=2, line_dash="dash", line_color="red", 
                                  annotation_text="Batas Maks 2%", annotation_position="top left")
        
        fig_shift_waste.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
        st.plotly_chart(fig_shift_waste, use_container_width=True)
        
        avg_waste = report_final['Waste (%)'].mean()
        # Logika warna info box berdasarkan target 2%
        if avg_waste > 2:
            st.error(f"⚠️ **Insight Efisiensi:** Rata-rata Waste Rate adalah **{avg_waste:.2f}%** (Melebihi target 2%).")
        else:
            st.success(f"✅ **Insight Efisiensi:** Rata-rata Waste Rate adalah **{avg_waste:.2f}%** (Sesuai target).")

    st.markdown("---")

    # --- TABEL RINGKASAN & DOWNLOAD ---
    st.subheader("📋 Ringkasan Produksi & Sinkronisasi")
    st.dataframe(
        report_final.style.format({
            "Output (pcs)": "{:,.0f}",
            "STT Waste (Kg)": "{:.2f}",
            "Total Reject": "{:.2f}",
            "Selisih (Kg)": "{:.2f}",
            "Waste (%)": "{:.2f}%"
        }), 
        use_container_width=True
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        report_final.to_excel(writer, sheet_name='Ringkasan', index=False)
        df_rej.to_excel(writer, sheet_name='Detail_Reject', index=False)
    
    st.download_button(
        label="📥 Download Laporan Excel",
        data=buffer.getvalue(),
        file_name=f"Laporan_Produksi_{start_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    run_laporan()