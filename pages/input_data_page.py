import streamlit as st
import pandas as pd
import datetime
import time 

# Mengimpor fungsi pendukung dari file utils.py
from utils import load_data, save_data 

# --- DEFINISI KONSTANTA GLOBAL ---
MESIN_OPTIONS = ["Mesin A1", "Mesin A2", "Mesin A3", "Mesin A4", "Mesin A5", "Mesin A6", "Mesin A7", "Mesin A8", "Mesin A9", "Mesin B0", "Mesin B1", "Mesin B2", "Mesin B3", "Mesin B4", "Mesin B5"]
VARIAN_OPTIONS = ["Wow Sapagethi Carbonara", "Wow Spagethi Bolognese", "Wow Spagethi Aglio Olio", "Wow Pasta Carbonara", "Wow Pasta Bolognese", "Wow Pasta Aglio Olio"]
JENIS_REJECT_OPTIONS = ["Kodefikasi", "Ganti Cello", "Kemasan Nginjek Mie", "Kemasan Nginjek Bumbu", "Setting Kemasan", "Kemasan Jebol", "Kemasan Over/Under", "Kemasan Melipat/Ngiris"]
SHIFT_OPTIONS = ["Shift 1", "Shift 2", "Shift 3"]

STT_DUMMY_MESIN = "STT_DUMMY_OUTPUT" 
BERAT_PER_PCS_KG = 0.075 
HOURLY_REJECT_COLS = [f"Jam {i}" for i in range(1, 9)]

COL_ORDER = [
    "Tanggal","Shift","Mesin","Varian","Jenis Reject",
    "Jam 1","Jam 2","Jam 3","Jam 4","Jam 5","Jam 6","Jam 7","Jam 8",
    "Koreksi","Total Reject","STT Waste (Kg)","Output (pcs)"
]

# --- FUNGSI UTAMA DATA ---

@st.cache_data(ttl=60) # Cache diperpendek agar data cepat update
def get_reject_data():
    df = load_data()
    if df is None or df.empty:
        return pd.DataFrame(columns=COL_ORDER)

    # Konversi Tanggal
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce").dt.date
    df.dropna(subset=['Tanggal'], inplace=True) 

    # Bersihkan String
    for col in ["Shift", "Mesin", "Varian", "Jenis Reject"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip() 

    # Konversi Numerik
    numeric_cols = ["Total Reject", "STT Waste (Kg)", "Output (pcs)", "Koreksi"] + HOURLY_REJECT_COLS
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # Hapus baris cacat
    filter_invalid_dummy = (
        (df["Jenis Reject"] == STT_DUMMY_MESIN) & 
        (df["Varian"] == STT_DUMMY_MESIN) &
        (df["Mesin"] == STT_DUMMY_MESIN)
    )
    df = df[~filter_invalid_dummy].copy()
    return df.sort_values(by=["Tanggal", "Shift"], ascending=False).reset_index(drop=True)

def initialize_session_state():
    if "input_shift" not in st.session_state:
        st.session_state.input_shift = SHIFT_OPTIONS[0]
    if "input_tanggal" not in st.session_state:
        st.session_state.input_tanggal = datetime.date.today()

def input_data_page():
    initialize_session_state()
    df_reject = get_reject_data()

    st.title("📝 Input Data Produksi & Reject")
    
    # ----------------------------------------------------------
    # 1. INPUT DATA REJECT DETAIL
    # ----------------------------------------------------------
    st.header("📦 Reject Detail per Mesin")
    
    with st.form("form_reject_detail"):
        col_info1, col_info2, col_info3 = st.columns(3)
        
        # REVISI: min_value DIHAPUS agar bisa input tanggal kapanpun (bulan/tahun lalu)
        tanggal = col_info1.date_input("Pilih Tanggal", 
                                       value=st.session_state.input_tanggal, 
                                       key="input_tanggal_form_reject",
                                       max_value=datetime.date.today())
        
        shift = col_info2.selectbox("Pilih Shift", SHIFT_OPTIONS, 
                                    index=SHIFT_OPTIONS.index(st.session_state.input_shift))
        
        mesin = col_info3.selectbox("Pilih Mesin", MESIN_OPTIONS)
        varian = st.selectbox("Pilih Varian Produk", VARIAN_OPTIONS) 

        st.subheader("Input Berat Reject (Kg)")
        data_input = []
        
        # Filter untuk pre-fill data lama
        filter_base = (df_reject["Tanggal"] == tanggal) & (df_reject["Shift"] == shift) & \
                      (df_reject["Mesin"] == mesin) & (df_reject["Varian"] == varian)

        for jr in JENIS_REJECT_OPTIONS:
            df_prefill = df_reject[filter_base & (df_reject["Jenis Reject"] == jr)]
            is_expanded = not df_prefill.empty and (df_prefill['Total Reject'].iloc[0] > 0)
            
            with st.expander(f"🔹 {jr}", expanded=is_expanded):
                cols = st.columns(4) # Dipersempit agar rapi di mobile
                nilai_jam = []
                for i in range(8):
                    jam_col = f"Jam {i+1}"
                    default_val = float(df_prefill[jam_col].iloc[0]) if not df_prefill.empty else 0.0
                    val = cols[i % 4].number_input(f"Jam {i+1}", min_value=0.0, step=0.01, value=default_val, key=f"r-{mesin}-{jr}-{i}")
                    nilai_jam.append(val)
                
                koreksi = st.number_input(f"Koreksi {jr} (±)", value=float(df_prefill['Koreksi'].iloc[0]) if not df_prefill.empty else 0.0, key=f"k-{mesin}-{jr}")
                total = sum(nilai_jam) + koreksi
                st.caption(f"Total: {total:.2f} Kg")
                data_input.append({"jr": jr, "jam": nilai_jam, "kor": koreksi, "tot": total})

        submitted_reject = st.form_submit_button("💾 SIMPAN DATA REJECT")

    if submitted_reject:
        df_full = load_data()
        str_tgl = str(tanggal)
        # Filter hapus data lama
        filter_old = (df_full["Tanggal"].astype(str) == str_tgl) & (df_full["Shift"] == shift) & \
                     (df_full["Mesin"] == mesin) & (df_full["Varian"] == varian) & \
                     (df_full["Jenis Reject"].isin(JENIS_REJECT_OPTIONS))
        
        df_updated = df_full[~filter_old].copy()
        new_rows = []
        for item in data_input:
            if item["tot"] != 0:
                row = {"Tanggal": str_tgl, "Shift": shift, "Mesin": mesin, "Varian": varian, "Jenis Reject": item["jr"],
                       "Koreksi": item["kor"], "Total Reject": item["tot"], "STT Waste (Kg)": 0, "Output (pcs)": 0}
                for i in range(8): row[f"Jam {i+1}"] = item["jam"][i]
                new_rows.append(row)
        
        df_final = pd.concat([df_updated, pd.DataFrame(new_rows)], ignore_index=True)[COL_ORDER]
        if save_data(df_final, "Data Berhasil Disimpan"):
            st.cache_data.clear()
            st.success("✅ Data Reject Berhasil Diperbarui!")
            time.sleep(1)
            st.rerun()

    st.divider()

    # ----------------------------------------------------------
    # 2. INPUT STT WASTE & OUTPUT
    # ----------------------------------------------------------
    st.header("♻️ STT Waste & Total Output")
    with st.form("form_stt"):
        c1, c2 = st.columns(2)
        tgl_w = c1.date_input("Tanggal", value=tanggal, max_value=datetime.date.today(), key="tgl_w")
        shf_w = c2.selectbox("Shift", SHIFT_OPTIONS, index=SHIFT_OPTIONS.index(shift), key="shf_w")
        var_w = st.selectbox("Varian", VARIAN_OPTIONS, key="var_w")
        
        df_stt_old = df_reject[(df_reject["Tanggal"] == tgl_w) & (df_reject["Shift"] == shf_w) & 
                               (df_reject["Varian"] == var_w) & (df_reject["Jenis Reject"] == STT_DUMMY_MESIN)]
        
        def_stt = float(df_stt_old["STT Waste (Kg)"].iloc[0]) if not df_stt_old.empty else 0.0
        def_out = int(df_stt_old["Output (pcs)"].iloc[0]) if not df_stt_old.empty else 0
        
        col_in1, col_in2 = st.columns(2)
        stt_val = col_in1.number_input("STT Waste (Kg)", min_value=0.0, value=def_stt)
        out_val = col_in2.number_input("Output (Pcs)", min_value=0, value=def_out)
        
        submitted_stt = st.form_submit_button("💾 SIMPAN STT & OUTPUT")

    if submitted_stt:
        df_full = load_data()
        filter_stt = (df_full["Tanggal"].astype(str) == str(tgl_w)) & (df_full["Shift"] == shf_w) & \
                     (df_full["Varian"] == var_w) & (df_full["Jenis Reject"] == STT_DUMMY_MESIN)
        
        df_updated = df_full[~filter_stt].copy()
        if stt_val > 0 or out_val > 0:
            new_stt = {"Tanggal": str(tgl_w), "Shift": shf_w, "Mesin": var_w, "Varian": var_w, "Jenis Reject": STT_DUMMY_MESIN,
                       "STT Waste (Kg)": stt_val, "Output (pcs)": out_val, "Total Reject": 0, "Koreksi": 0}
            for i in range(8): new_stt[f"Jam {i+1}"] = 0
            df_updated = pd.concat([df_updated, pd.DataFrame([new_stt])], ignore_index=True)
        
        if save_data(df_updated[COL_ORDER], "Data STT Disimpan"):
            st.cache_data.clear()
            st.success("✅ Data STT & Output Berhasil Disimpan!")
            time.sleep(1)
            st.rerun()

    # ----------------------------------------------------------
    # 3. PREVIEW
    # ----------------------------------------------------------
    st.divider()
    st.header("📋 Preview Data")
    c_p1, c_p2 = st.columns(2)
    p_tgl = c_p1.date_input("Filter Tanggal", value=tanggal)
    p_shf = c_p2.selectbox("Filter Shift", SHIFT_OPTIONS, index=SHIFT_OPTIONS.index(shift))
    
    df_view = df_reject[(df_reject["Tanggal"] == p_tgl) & (df_reject["Shift"] == p_shf)]
    if not df_view.empty:
        st.dataframe(df_view, use_container_width=True)
    else:
        st.info("Tidak ada data untuk filter ini.")

if __name__ == "__main__":
    input_data_page()