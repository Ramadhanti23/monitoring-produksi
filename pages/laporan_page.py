import streamlit as st
import pandas as pd
import io
import datetime
import plotly.express as px
from streamlit_extras.switch_page_button import switch_page 

# --- KONSTANTA GLOBAL ---
STT_DUMMY_MESIN = "STT_DUMMY_OUTPUT"
BERAT_PER_PCS_KG = 0.075

def get_data_laporan():
    """Fungsi mandiri untuk mengambil data dengan pembersihan tipe data"""
    try:
        from utils import load_data
        df = load_data()
        if df is not None and not df.empty:
            # Pastikan Tanggal dalam format date
            df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce").dt.date
            df = df.dropna(subset=['Tanggal'])
            
            # Konversi kolom numerik yang kritikal
            cols_to_fix = ["Total Reject", "STT Waste (Kg)", "Output (pcs)", "Koreksi"]
            for col in cols_to_fix:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
    return pd.DataFrame()

def run_laporan():
    # --- 1. PROTEKSI HALAMAN ---
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        switch_page("app")
        st.stop()

    # --- 2. SIDEBAR CUSTOM ---
    with st.sidebar:
        st.header("⚙️ Menu Laporan")
        st.write(f"👤 User: **{st.session_state.get('username', 'Admin')}**")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            switch_page("app")
        st.divider()

    # --- 3. HEADER HALAMAN ---
    st.title("📄 Laporan Produksi & Waste Harian")
    st.info("Gunakan halaman ini untuk melihat performa antar shift dan mendownload data untuk audit.")

    df_full = get_data_laporan()
    if df_full.empty:
        st.warning("Belum ada data yang tersimpan di sistem.")
        return

    # --- 4. FILTER PANEL ---
    with st.container(border=True):
        st.subheader("🔍 Filter Data")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            start_date = st.date_input("Mulai Tanggal", value=df_full["Tanggal"].min())
        with col_b:
            # Default ke hari ini agar data terbaru langsung muncul
            end_date = st.date_input("Sampai Tanggal", value=datetime.date.today())
        with col_c:
            list_shift = ["Semua Shift"] + sorted(df_full["Shift"].unique().tolist())
            sel_shift = st.selectbox("Pilih Shift", list_shift)

    # Eksekusi Filter
    mask = (df_full["Tanggal"] >= start_date) & (df_full["Tanggal"] <= end_date)
    if sel_shift != "Semua Shift":
        mask = mask & (df_full["Shift"] == sel_shift)
    
    df_filtered = df_full[mask].copy()

    if df_filtered.empty:
        st.error("Data tidak ditemukan untuk periode/shift tersebut.")
        return

    # --- 5. PENGOLAHAN DATA (LOGIKA AGREGASI) ---
    # Pisahkan baris Dummy (STT/Output) dan baris Reject Detail
    df_out = df_filtered[df_filtered["Jenis Reject"] == STT_DUMMY_MESIN]
    df_rej_detail = df_filtered[df_filtered["Jenis Reject"] != STT_DUMMY_MESIN]

    # Agregasi data Output & STT
    summary = df_out.groupby(["Tanggal", "Shift"]).agg({
        "Output (pcs)": "sum",
        "STT Waste (Kg)": "sum"
    }).reset_index()

    # Agregasi data Reject Detail (untuk cross-check/sinkronisasi)
    rej_val = df_rej_detail.groupby(["Tanggal", "Shift"])["Total Reject"].sum().reset_index()
    
    # Gabungkan menjadi satu Laporan Final
    report_final = pd.merge(summary, rej_val, on=["Tanggal", "Shift"], how="left").fillna(0)
    
    # Hitung Kalkulasi Tambahan
    report_final["Selisih (Kg)"] = report_final["STT Waste (Kg)"] - report_final["Total Reject"]
    # Rumus Waste Rate: (Total Waste / (Total Output Kg + Total Waste)) * 100
    report_final["Waste (%)"] = (report_final["STT Waste (Kg)"] / 
                                ((report_final["Output (pcs)"] * BERAT_PER_PCS_KG) + report_final["STT Waste (Kg)"]) * 100).fillna(0)

    # --- 6. VISUALISASI PERFORMA ---
    st.divider()
    st.subheader("📊 Analisis Komparasi Antar Shift")
    
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        # Grafik Output
        fig_out = px.bar(report_final, x="Shift", y="Output (pcs)", color="Shift",
                         title="Total Output (Pcs) per Shift",
                         text_auto=',.0f', # Format angka ribuan
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_out.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(fig_out, use_container_width=True)
        
        best_shift = report_final.loc[report_final['Output (pcs)'].idxmax(), 'Shift']
        st.success(f"🏆 **Shift Terbaik:** {best_shift}")

    with col_g2:
        # Grafik Waste Rate
        fig_waste = px.bar(report_final, x="Shift", y="Waste (%)", color="Shift",
                           title="Waste Rate (%) per Shift",
                           text_auto='.2f',
                           color_discrete_sequence=px.colors.qualitative.Set2)
        
        # Tambahkan Garis Target 2%
        fig_waste.add_hline(y=2.0, line_dash="dash", line_color="red", 
                            annotation_text="Target Maks 2%", annotation_position="top left")
        
        fig_waste.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(fig_waste, use_container_width=True)

        avg_waste = report_final['Waste (%)'].mean()
        if avg_waste > 2:
            st.warning(f"⚠️ **Rata-rata Waste:** {avg_waste:.2f}% (Melebihi target 2%)")
        else:
            st.success(f"✅ **Rata-rata Waste:** {avg_waste:.2f}% (Sesuai target)")

    # --- 7. TABEL RINGKASAN & EXPORT ---
    st.divider()
    st.subheader("📋 Data Tabel Ringkasan")
    
    # Styling Tabel agar user mudah membaca data
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

    # Tombol Download Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        report_final.to_excel(writer, sheet_name='Ringkasan_Shift', index=False)
        df_rej_detail.to_excel(writer, sheet_name='Detail_Reject_Mesin', index=False)
    
    st.download_button(
        label="📥 Download Laporan Lengkap (.xlsx)",
        data=buffer.getvalue(),
        file_name=f"Laporan_Produksi_{start_date}_ke_{end_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

if __name__ == "__main__":
    run_laporan()