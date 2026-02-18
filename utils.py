import pandas as pd
import streamlit as st
import os
import numpy as np

FILE_PATH = "data_produksi.csv"
ESTIMASI_TOTAL_BARIS = 100000 

# --- KONSTANTA GLOBAL ---
BERAT_PER_PCS_KG = 0.075 
STT_DUMMY_MESIN = "STT_DUMMY_OUTPUT" 

def load_data():
    if not os.path.exists(FILE_PATH):
        st.warning(f"File '{FILE_PATH}' belum ada. Membuat template data baru...")
        df_dummy = pd.DataFrame(columns=[
            "Tanggal", "Shift", "Mesin", "Varian", "Jenis Reject", 
            "Jam 1", "Jam 2", "Jam 3", "Jam 4", "Jam 5", "Jam 6", "Jam 7", "Jam 8", 
            "Koreksi", "Total Reject", "STT Waste (Kg)", "Output (pcs)"
        ])
        return df_dummy

    chunks = []
    chunksize = 50000 
    progress = st.progress(0, text="Membaca Database...")
    total_read = 0

    try:
        # Gunakan low_memory=False agar tipe data lebih konsisten
        for chunk in pd.read_csv(FILE_PATH, chunksize=chunksize, engine='c', low_memory=False, encoding='utf-8'): 
            total_read += len(chunk)
            progress_value = min(total_read / ESTIMASI_TOTAL_BARIS, 1.0) 
            progress.progress(progress_value, text=f"Loading Data... {int(progress_value * 100)}%")
            
            # Bersihkan Tanggal dari spasi atau karakter non-visible
            if 'Tanggal' in chunk.columns:
                chunk['Tanggal'] = chunk['Tanggal'].astype(str).str.strip() 

            chunks.append(chunk)

        progress.empty() # Hapus progress bar setelah selesai
        
        if not chunks:
            return pd.DataFrame()

        df = pd.concat(chunks, ignore_index=True)
        
        # Bersihkan baris yang benar-benar kosong
        df.dropna(how='all', inplace=True)
        
        # Hapus duplikasi berdasarkan baris yang identik
        df = df.drop_duplicates()
        
        return df

    except Exception as e:
        st.error(f"Error saat memuat data: {e}")
        return pd.DataFrame()

def save_data(df, message="Data Berhasil Disimpan"):
    try:
        # Simpan dengan format yang bersih
        df.to_csv(FILE_PATH, index=False, encoding='utf-8')
        st.toast(message, icon='💾')
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data ke CSV: {e}")
        return False

def get_summary_data(df):
    """
    Menghitung metrik ringkasan harian (per Tanggal & Shift) untuk Laporan.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # Copy data agar tidak merusak dataframe asli
    df_valid = df.copy()
    
    # Pastikan kolom numerik benar-benar angka
    cols_to_fix = ["Output (pcs)", "STT Waste (Kg)", "Total Reject"]
    for col in cols_to_fix:
        if col in df_valid.columns:
            df_valid[col] = pd.to_numeric(df_valid[col], errors='coerce').fillna(0)

    # Pisahkan data Output (Dummy Mesin) dan Reject Detail (Input Operator)
    df_output = df_valid[df_valid["Jenis Reject"] == STT_DUMMY_MESIN].copy()
    df_reject_detail = df_valid[df_valid["Jenis Reject"] != STT_DUMMY_MESIN].copy()
    
    # Agregasi Output & Waste Audit
    output_agg = df_output.groupby(["Tanggal", "Shift"]).agg(
        Output_pcs=('Output (pcs)', 'sum'),
        STT_Waste_Audit=('STT Waste (Kg)', 'sum')
    ).reset_index()
    
    # Agregasi Reject Detail (dari operator)
    reject_agg = df_reject_detail.groupby(["Tanggal", "Shift"]).agg(
        Total_Reject_Detail=('Total Reject', 'sum')
    ).reset_index()
    
    # Gabungkan
    df_merged = pd.merge(
        output_agg, 
        reject_agg, 
        on=["Tanggal", "Shift"], 
        how="outer"
    ).fillna(0)
    
    if df_merged.empty:
        return pd.DataFrame()

    # Kalkulasi Metrik
    df_merged['Total_Output_Kg'] = df_merged['Output_pcs'] * BERAT_PER_PCS_KG
    df_merged['Total_Waste_Resmi'] = df_merged['STT_Waste_Audit']
    df_merged['Selisih Waste (Kg)'] = df_merged['Total_Waste_Resmi'] - df_merged['Total_Reject_Detail']
    
    # Hitung Persentase Waste
    total_input = df_merged['Total_Output_Kg'] + df_merged['Total_Waste_Resmi']
    df_merged['Persentase Waste (%)'] = np.where(
        total_input > 0,
        (df_merged['Total_Waste_Resmi'] / total_input * 100),
        0
    ).round(2)
    
    # Rename untuk tampilan laporan
    df_merged.rename(columns={
        'Output_pcs': 'Output (pcs)',
        'STT_Waste_Audit': 'STT Waste (Kg)',
        'Total_Reject_Detail': 'Total Reject Detail (Kg)',
    }, inplace=True)

    final_cols = [
        "Tanggal", "Shift", "Output (pcs)", "STT Waste (Kg)", 
        "Total Reject Detail (Kg)", "Selisih Waste (Kg)", "Persentase Waste (%)"
    ]
    
    return df_merged[final_cols].sort_values(by="Tanggal", ascending=False)