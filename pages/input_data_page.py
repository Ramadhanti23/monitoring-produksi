import streamlit as st
import pandas as pd
import datetime
import time 

# Asumsi: 'utils' (load_data, save_data) tersedia di lingkungan Anda
# Pastikan fungsi load_data() mengembalikan DataFrame mentah (raw data)
from utils import load_data, save_data 

# --- DEFINISI KONSTANTA GLOBAL ---
MESIN_OPTIONS = ["Mesin A1", "Mesin A2", "Mesin A3", "Mesin A4", "Mesin A5", "Mesin A6", "Mesin A7", "Mesin A8", "Mesin A9", "Mesin B0", "Mesin B1", "Mesin B2", "Mesin B3", "Mesin B4", "Mesin B5"]
VARIAN_OPTIONS = ["Wow Sapagethi Carbonara", "Wow Spagethi Bolognese", "Wow Spagethi Aglio Olio", "Wow Pasta Carbonara", "Wow Pasta Bolognese", "Wow Pasta Aglio Olio"]
JENIS_REJECT_OPTIONS = ["Kodefikasi", "Ganti Cello", "Kemasan Nginjek Mie", "Kemasan Nginjek Bumbu", "Setting Kemasan", "Kemasan Jebol", "Kemasan Over/Under", "Kemasan Melipat/Ngiris"]
SHIFT_OPTIONS = ["Shift 1", "Shift 2", "Shift 3"]

# Baris placeholder untuk menyimpan Output dan STT Waste 
STT_DUMMY_MESIN = "STT_DUMMY_OUTPUT" 

# Berat per pcs dalam Kg (Asumsi: konstanta untuk semua varian)
BERAT_PER_PCS_KG = 0.075 

# Kolom Reject per jam
HOURLY_REJECT_COLS = [f"Jam {i}" for i in range(1, 9)]

# Kolom yang harus dipastikan ada
REQUIRED_COLS = [
    "Tanggal","Shift","Mesin","Varian","Jenis Reject",
    "Koreksi","Total Reject","STT Waste (Kg)","Output (pcs)"
] + HOURLY_REJECT_COLS
# Tentukan urutan kolom yang benar
COL_ORDER = [
    "Tanggal","Shift","Mesin","Varian","Jenis Reject",
    "Jam 1","Jam 2","Jam 3","Jam 4","Jam 5","Jam 6","Jam 7","Jam 8",
    "Koreksi","Total Reject","STT Waste (Kg)","Output (pcs)"
]

# --- FUNGSI UTAMA DATA ---

@st.cache_data
def get_reject_data():
    """
    Memuat data mentah dari sumber, memastikan konversi tipe data, 
    dan membersihkan baris placeholder STT_DUMMY yang tidak valid/cacat.
    """
    df = load_data()

    # 1. Pastikan semua kolom yang diperlukan ada, terutama untuk DataFrame kosong
    for col in REQUIRED_COLS:
        if col not in df.columns:
            if col in ["Tanggal", "Shift", "Mesin", "Varian", "Jenis Reject"]:
                df[col] = ''
            else:
                df[col] = 0.0

    # 2. Konversi dan pembersihan
    # Pastikan kolom Tanggal dikonversi ke datetime.date
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce").dt.date
    df.dropna(subset=['Tanggal'], inplace=True) 

    # Bersihkan (strip) kolom string untuk konsistensi
    string_cols_to_clean = ["Shift", "Mesin", "Varian", "Jenis Reject"]
    for col in string_cols_to_clean:
        if col in df.columns:
            # Menggunakan .astype(str) sebelum .str.strip() untuk menghindari masalah tipe
            df[col] = df[col].astype(str).str.strip() 

    # Konversi kolom numerik
    numeric_cols = ["Total Reject", "STT Waste (Kg)", "Output (pcs)", "Koreksi"] + HOURLY_REJECT_COLS
    
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # 3. PEMBESIHAN DATA UTAMA SAAT LOADING (Menghapus baris cacat penuh)
    # Baris STT yang cacat adalah: Jenis Reject = DUMMY AND Varian = DUMMY AND Mesin = DUMMY
    filter_invalid_dummy = (
        (df["Jenis Reject"] == STT_DUMMY_MESIN) & 
        (df["Varian"] == STT_DUMMY_MESIN) &
        (df["Mesin"] == STT_DUMMY_MESIN)
    )
    
    # Hanya simpan baris yang TIDAK memenuhi kriteria filter_invalid_dummy
    df = df[~filter_invalid_dummy].copy()
    
    # Urutkan berdasarkan Tanggal dan Shift untuk tampilan
    df = df.sort_values(by=["Tanggal", "Shift"]).reset_index(drop=True)

    return df

# --- FUNGSI INISIALISASI SESSION STATE ---
def initialize_session_state():
    """Menginisialisasi semua variabel session state yang diperlukan."""
    today = datetime.date.today()
    # Inisialisasi untuk form input
    if "input_shift" not in st.session_state:
        st.session_state.input_shift = SHIFT_OPTIONS[0]
    if "input_tanggal" not in st.session_state:
        st.session_state.input_tanggal = today

def input_data_page():
    # Panggil inisialisasi di awal fungsi
    initialize_session_state()
    
    # Muat data dari sumber (hanya dipanggil sekali, hasilnya di-cache)
    df_reject = get_reject_data()

    st.title("📝 Aplikasi Input Data Reject & STT Waste")
    st.markdown("Halaman ini dibagi menjadi dua bagian: **Detail Reject Per Mesin** dan **STT Waste & Output Per Varian**.")
    
    # ----------------------------------------------------------
    # 1. INPUT DATA REJECT DETAIL (Per Mesin)
    # ----------------------------------------------------------
    st.header("📦 Input Data Reject Detail (Per Mesin)")
    
    # Cek apakah data kosong untuk menentukan tanggal awal
    try:
        min_date = df_reject["Tanggal"].min()
        if pd.isna(min_date):
            min_date = datetime.date.today()
    except:
        min_date = datetime.date.today()


    with st.form("form_reject_detail"):
        
        st.subheader("Informasi Utama Mesin")
        
        # Penentuan index default
        try:
            default_shift_index = SHIFT_OPTIONS.index(st.session_state.input_shift)
        except ValueError:
            default_shift_index = 0

        col_info1, col_info2, col_info3 = st.columns(3)

        # Menggunakan session state sebagai key, memungkinkan nilai default persist
        tanggal = col_info1.date_input("Tanggal", 
                                       value=st.session_state.input_tanggal, 
                                       key="input_tanggal_form_reject",
                                       min_value=min_date, max_value=datetime.date.today())
        
        shift = col_info2.selectbox("Shift", 
                                    SHIFT_OPTIONS, 
                                    key="input_shift_form_reject", 
                                    index=default_shift_index)
        
        mesin = col_info3.selectbox("Nama Mesin", 
                                    MESIN_OPTIONS, 
                                    key="input_mesin")
        
        varian = st.selectbox("Varian", 
                                VARIAN_OPTIONS, 
                                key="input_varian_reject") 

        st.subheader("Input Reject per Jenis (Kg)")

        data_input = []

        # Memfilter data lama untuk pre-fill di luar loop agar lebih efisien
        filter_base = (
            (df_reject["Tanggal"] == tanggal) & 
            (df_reject["Shift"] == shift) & 
            (df_reject["Mesin"] == mesin) & 
            (df_reject["Varian"] == varian)
        )
        
        for jr in JENIS_REJECT_OPTIONS:
            
            # Cek data pre-fill untuk Jenis Reject ini
            filter_prefill = filter_base & (df_reject["Jenis Reject"] == jr)
            df_prefill = df_reject[filter_prefill]
            
            # Tentukan apakah expander harus diperluas
            # Diperluas jika sudah ada data dengan Total Reject > 0 atau Koreksi != 0
            is_expanded = (not df_prefill.empty and 
                           (df_prefill['Total Reject'].iloc[0] > 0 or df_prefill['Koreksi'].iloc[0] != 0))
            
            with st.expander(f"🔹 {jr}", expanded=is_expanded):
                
                cols = st.columns(8)
                nilai_jam = []
                total_reject_jam = 0.0

                # Pre-fill data Jam 1 sampai Jam 8
                for i in range(8):
                    jam_col = f"Jam {i+1}"
                    
                    default_val = 0.0
                    if not df_prefill.empty and jam_col in df_prefill.columns:
                        try:
                            # Ambil nilai default dari data lama
                            default_val = float(df_prefill[jam_col].iloc[0])
                        except:
                            default_val = 0.0 # Safety fallback
                    
                    val = cols[i].number_input(
                        f"Jam {i+1}",
                        min_value=0.0, step=0.01, format="%.2f",
                        value=default_val,
                        key=f"reject-{mesin}-{varian}-{jr}-j{i+1}" 
                    )
                    nilai_jam.append(val)
                    total_reject_jam += val

                # Input Koreksi
                default_koreksi = 0.0
                if not df_prefill.empty and "Koreksi" in df_prefill.columns:
                    try:
                        default_koreksi = float(df_prefill["Koreksi"].iloc[0])
                    except:
                        default_koreksi = 0.0 # Safety fallback
                
                koreksi = st.number_input(
                    f"Koreksi {jr} (±)",
                    value=default_koreksi, step=0.01, format="%.2f",
                    key=f"reject-{mesin}-{varian}-{jr}-koreksi" 
                )

                total = total_reject_jam + koreksi
                st.caption(f"Total Reject {jr} (Jam + Koreksi): **{total:.2f} Kg**")

                data_input.append({
                    "Tanggal": tanggal, "Shift": shift, "Mesin": mesin, 
                    "Varian": varian, "Jenis Reject": jr,
                    "Jam Values": nilai_jam, "Koreksi": koreksi, "Total": total
                })

        submitted_reject = st.form_submit_button("💾 Simpan Data Reject Detail (Timpa Data Mesin Lama)")

    # -----------------------------
    # LOGIKA SIMPAN REJECT DETAIL
    # -----------------------------
    if submitted_reject:
        
        # Simpan nilai tanggal dan shift terakhir yang diinput ke session state
        st.session_state.input_shift = shift 
        st.session_state.input_tanggal = tanggal
        
        # 1. Muat ulang data mentah (raw data) dari CSV 
        df_full = load_data() 
        
        # Konversi tanggal ke string untuk perbandingan dengan data mentah (raw CSV)
        str_tanggal = str(tanggal)
        
        # 2. KRUSIAL: Hapus baris detail reject lama (BUKAN STT_DUMMY) untuk 4 kunci utama ini
        filter_old_reject = (
            (df_full["Tanggal"].astype(str).str.strip() == str_tanggal) &
            (df_full["Shift"].astype(str).str.strip() == shift) &
            (df_full["Mesin"].astype(str).str.strip() == mesin) & 
            (df_full["Varian"].astype(str).str.strip() == varian) &
            # Hanya filter jenis reject yang ada di JENIS_REJECT_OPTIONS
            (df_full["Jenis Reject"].astype(str).str.strip().isin(JENIS_REJECT_OPTIONS)) 
        )
        # df_updated sekarang berisi semua data, kecuali baris Detail Reject lama
        df_updated = df_full[~filter_old_reject].copy()
        
        new_data_list = []

        # 3. Kumpulkan data baru Reject Detail yang bernilai > 0 atau Koreksi != 0
        for item in data_input:
            # Simpan jika Total Reject > 0 ATAU ada Koreksi yang tidak nol
            if item["Total"] > 0.0 or item["Koreksi"] != 0.0: 
                new_row = {
                    "Tanggal": str(item["Tanggal"]), # Simpan sebagai string
                    "Shift": item["Shift"],
                    "Mesin": item["Mesin"],
                    "Varian": item["Varian"],
                    "Jenis Reject": item["Jenis Reject"],
                    **{f"Jam {i+1}": item["Jam Values"][i] for i in range(8)},
                    "Koreksi": item["Koreksi"],
                    "Total Reject": item["Total"],
                    "STT Waste (Kg)": 0.0, 
                    "Output (pcs)": 0.0 
                }
                new_data_list.append(new_row)
        
        # 4. Gabungkan data Reject Detail baru dengan data lama yang tidak terhapus
        if new_data_list:
            new_data_df = pd.DataFrame(new_data_list)
            
            # Gabungkan DataFrame baru dengan DataFrame yang sudah dihapus baris lamanya
            df_final = pd.concat([df_updated, new_data_df], ignore_index=True)
            
            # Hapus duplikasi baris Reject Detail (pertahankan yang baru diinput)
            df_final.drop_duplicates(
                subset=['Tanggal', 'Shift', 'Mesin', 'Varian', 'Jenis Reject'], 
                keep='last', # Pertahankan data yang baru diinput
                inplace=True
            )

            # Pastikan semua kolom yang diperlukan ada dan diurutkan
            for col in COL_ORDER:
                if col not in df_final.columns:
                    df_final[col] = 0.0 
            df_final = df_final[COL_ORDER]

            # 5. Tulis ke file
            if save_data(df_final, "Data Reject Detail berhasil disimpan"):
                get_reject_data.clear() 
                st.session_state.input_shift = shift 
                st.session_state.input_tanggal = tanggal
                st.success(f"✅ Data Reject Detail Mesin **{mesin}** Varian **{varian}** pada {tanggal.strftime('%d %B %Y')}/{shift} berhasil disimpan/diperbarui! ({len(new_data_list)} baris reject detail disimpan)")
        else:
            # Jika tidak ada input baru yang bernilai > 0, tapi ada baris lama yang dihapus/dimodifikasi
            if filter_old_reject.any(): # Cek apakah ada baris yang dihapus
                if save_data(df_updated, "Data Reject Detail berhasil dihapus"):
                    get_reject_data.clear()
                    st.session_state.input_shift = shift 
                    st.session_state.input_tanggal = tanggal
                    st.info(f"Semua data reject detail Mesin **{mesin}** Varian **{varian}** berhasil direset (nilai diinput nol).")
            else:
                st.info("Tidak ada reject detail yang dimasukkan dan tidak ada data lama yang perlu direset.")


    st.divider()


    # ----------------------------------------------------------
    # 2. INPUT STT WASTE & OUTPUT Per Varian (Form Terpisah)
    # ----------------------------------------------------------
    st.header("♻️ Input STT Waste & Output Per Varian")
    st.markdown("Isi data **STT Waste & Output** per **Varian, Tanggal, dan Shift** yang dipilih.")
    
    # Ambil nilai yang terakhir di input form 1 untuk default form 2
    try:
        default_shift_index_w = SHIFT_OPTIONS.index(st.session_state.input_shift)
    except ValueError:
        default_shift_index_w = 0
        
    default_tanggal_w = st.session_state.input_tanggal

    with st.form("form_stt_output"):

        st.subheader("Informasi Utama STT/Output")
        col_w1, col_w2 = st.columns(2)
        tanggal_w = col_w1.date_input("Tanggal Waste", key="tw", value=default_tanggal_w)
        shift_w = col_w2.selectbox("Shift Waste", SHIFT_OPTIONS, key="sw", index=default_shift_index_w)
        
        varian_w = st.selectbox("Varian STT/Output", VARIAN_OPTIONS, key="vw")
        
        # Ambil data STT/Output yang sudah ada (Jenis Reject = STT_DUMMY) untuk PRE-FILL
        filter_stt_check = (
            (df_reject["Tanggal"] == tanggal_w) & 
            (df_reject["Shift"] == shift_w) &
            (df_reject["Varian"] == varian_w) & 
            (df_reject["Mesin"] == varian_w) & # Perkuatan filter: Mesin juga harus sama dengan Varian
            (df_reject["Jenis Reject"] == STT_DUMMY_MESIN) 
        )
        
        df_stt_old = df_reject[filter_stt_check]
        
        # Cari nilai default
        default_stt_waste = float(df_stt_old["STT Waste (Kg)"].iloc[0]) if not df_stt_old.empty else 0.0
        default_output_pcs = int(df_stt_old["Output (pcs)"].iloc[0]) if not df_stt_old.empty else 0
        
        st.subheader(f"Input Data Varian {varian_w}")

        col_input1, col_input2 = st.columns(2)

        stt_waste_value = col_input1.number_input(
            "Total STT Waste (Kg)",
            min_value=0.0, step=0.01, format="%.2f",
            value=default_stt_waste,
            key="stt_waste_value" 
        )
        
        output_value = col_input2.number_input(
            "Total Output (pcs)",
            min_value=0, step=1, format="%d", # Menggunakan %d untuk integer
            value=default_output_pcs,
            key="output_value"
        )
        
        submitted_stt = st.form_submit_button("💾 Simpan Data STT Waste & Output")

    # -----------------------------
    # LOGIKA SIMPAN STT WASTE & OUTPUT
    # -----------------------------
    if submitted_stt:
        
        # Update session state
        st.session_state.input_shift = shift_w 
        st.session_state.input_tanggal = tanggal_w
        
        # 1. Muat ulang data mentah (raw data) dari CSV 
        df_full = load_data() 

        # 2. Hapus baris STT_DUMMY lama yang relevan 
        str_tanggal_w = str(tanggal_w)
        filter_old_stt = (
            (df_full["Tanggal"].astype(str).str.strip() == str_tanggal_w) &
            (df_full["Shift"].astype(str).str.strip() == shift_w) &
            (df_full["Varian"].astype(str).str.strip() == varian_w) &
            (df_full["Mesin"].astype(str).str.strip() == varian_w) & # Perkuatan filter
            (df_full["Jenis Reject"].astype(str).str.strip() == STT_DUMMY_MESIN)
        )
        # Hapus baris STT_DUMMY yang lama dan relevan
        df_updated = df_full[~filter_old_stt].copy()
        
        # 3. Buat baris data STT_DUMMY baru (hanya menyimpan jika ada nilai > 0)
        if stt_waste_value > 0.0 or output_value > 0:
            new_stt_row = {
                "Tanggal": str_tanggal_w, 
                "Shift": shift_w,
                # Mesin diisi Varian agar unik (Tgl/Shift/Mesin/Varian/Jenis Reject)
                "Mesin": varian_w, 
                "Varian": varian_w, 
                "Jenis Reject": STT_DUMMY_MESIN, 
                **{f"Jam {i+1}": 0.0 for i in range(8)}, 
                "Koreksi": 0.0,
                "Total Reject": 0.0, 
                "STT Waste (Kg)": stt_waste_value, 
                "Output (pcs)": float(output_value) 
            }
            
            new_stt_df = pd.DataFrame([new_stt_row])
            
            df_final = pd.concat([df_updated, new_stt_df], ignore_index=True)

            # Pastikan semua kolom yang diperlukan ada dan diurutkan
            for col in COL_ORDER:
                if col not in df_final.columns:
                    df_final[col] = 0.0
            df_final = df_final[COL_ORDER]
            
            # Drop duplikasi (ini memastikan baris STT/Output yang baru menimpa yang lama)
            df_final.drop_duplicates(
                subset=['Tanggal', 'Shift', 'Mesin', 'Varian', 'Jenis Reject'], 
                keep='last', 
                inplace=True
            )

            # 4. Simpan data
            if save_data(df_final, "Data STT Waste berhasil disimpan"):
                get_reject_data.clear() 
                st.session_state.input_shift = shift_w 
                st.session_state.input_tanggal = tanggal_w
                st.success(f"✅ Data STT Waste & Output Varian **{varian_w}** untuk **{tanggal_w.strftime('%d %B %Y')}/{shift_w}** berhasil disimpan/diperbarui!")
        else:
            # Jika nilainya 0, dan ada data lama yang terhapus (berarti reset ke 0)
            if filter_old_stt.any():
                if save_data(df_updated, "Data STT Waste berhasil dihapus"):
                    get_reject_data.clear()
                    st.session_state.input_shift = shift_w 
                    st.session_state.input_tanggal = tanggal_w
                    st.success(f"✅ Data STT Waste & Output Varian **{varian_w}** untuk **{tanggal_w.strftime('%d %B %Y')}/{shift_w}** berhasil dihapus (nilai direset ke nol).")
            else:
                st.info("Tidak ada nilai yang dimasukkan dan tidak ada data lama untuk dihapus.")
            

    st.divider()


    # ----------------------------------------------------------
    # 3. PREVIEW DATA (Dilengkapi Persentase Waste per Varian)
    # ----------------------------------------------------------
    st.header("📋 Preview Data Shift")
    
    # Ambil nilai terakhir di input form 2 (atau form 1)
    tanggal_filter = st.date_input("Pilih Tanggal", key="pf", value=st.session_state.input_tanggal) 
    
    try:
        default_preview_shift_index = SHIFT_OPTIONS.index(st.session_state.input_shift)
    except ValueError:
        default_preview_shift_index = 0
        
    shift_filter = st.selectbox("Pilih Shift", 
                                SHIFT_OPTIONS, 
                                key="sf", 
                                index=default_preview_shift_index)

    df_filtered = df_reject[
        (df_reject["Tanggal"] == tanggal_filter) & 
        (df_reject["Shift"] == shift_filter)
    ].copy()

    if df_filtered.empty:
        st.info(f"Belum ada data (Reject Detail atau STT Waste) untuk tanggal **{tanggal_filter.strftime('%d %B %Y')}** dan **{shift_filter}**.")
    else:
        
        # --- Ringkasan Total Shift ---
        total_reject_detail = df_filtered[
            df_filtered["Jenis Reject"] != STT_DUMMY_MESIN
        ]["Total Reject"].sum()
        
        # Ambil data STT dari baris Jenis Reject = STT_DUMMY_OUTPUT
        df_stt_rows = df_filtered[df_filtered["Jenis Reject"] == STT_DUMMY_MESIN].copy()

        total_stt = df_stt_rows["STT Waste (Kg)"].sum()
        total_output_pcs = df_stt_rows["Output (pcs)"].sum()
        
        # Perhitungan Persentase Total (Absolut)
        total_output_kg = total_output_pcs * BERAT_PER_PCS_KG
        
        # Total Waste (Detail Reject + STT Waste)
        total_waste_kg = total_stt + total_reject_detail
        
        # Total Input = Total Output + Total Waste
        total_input_kg = total_output_kg + total_waste_kg
        
        persentase_waste_total = 0.0
        if total_input_kg > 0:
            persentase_waste_total = (total_waste_kg / total_input_kg) * 100

        st.subheader("Ringkasan Total Per Shift")
        
        # REVISI PENTING: Mengatur rasio kolom untuk memberi ruang ekstra (Solusi angka terpotong)
        col_summary1, col_summary2, col_summary3, col_summary4 = st.columns([1.5, 1.5, 1, 1])
        
        # REVISI JUDUL METRIK
        col_summary1.metric("Reject Detail (Kg)", f"{total_reject_detail:,.2f} Kg")
        col_summary2.metric("STT Waste (Kg)", f"{total_stt:,.2f} Kg")
        col_summary3.metric("Output (pcs)", f"{total_output_pcs:,.0f} pcs")
        col_summary4.metric("Waste Total (%)", f"{persentase_waste_total:,.2f} %")
        
        st.markdown("---")
        
        # --- Data Detail STT/Output Per Varian (Ringkasan) ---
        st.subheader("Data STT Waste & Output Per Varian (Ringkasan)")
        
        if not df_stt_rows.empty:
            df_stt_display = df_stt_rows[["Varian", "STT Waste (Kg)", "Output (pcs)"]].copy() 
            
            # Hitung Total Reject Detail Per Varian (dari baris non-dummy)
            df_reject_grouped = df_filtered[
                df_filtered["Jenis Reject"] != STT_DUMMY_MESIN
            ].groupby("Varian")["Total Reject"].sum().reset_index()
            df_reject_grouped.rename(columns={"Total Reject": "Total Reject Detail (Kg)"}, inplace=True)
            
            # Gabungkan dengan data STT/Output
            df_stt_display = df_stt_display.merge(df_reject_grouped, on="Varian", how="left").fillna(0)
            
            # Hitung Output dalam Kg dan Total Input
            df_stt_display['Output (Kg)'] = df_stt_display['Output (pcs)'] * BERAT_PER_PCS_KG
            df_stt_display['Total Waste (Kg)'] = df_stt_display['STT Waste (Kg)'] + df_stt_display['Total Reject Detail (Kg)']
            df_stt_display['Total Input (Kg)'] = df_stt_display['Output (Kg)'] + df_stt_display['Total Waste (Kg)']
            
            # Hitung Persentase Waste Absolut Per Varian
            # Menggunakan .replace(0, 1e-9) untuk menghindari ZeroDivisionError
            df_stt_display['Persentase Waste (%)'] = (
                (df_stt_display['Total Waste (Kg)'] / df_stt_display['Total Input (Kg)'].replace(0, 1e-9)) * 100
            ).fillna(0).round(2)
            
            # Pilih kolom untuk ditampilkan di preview
            df_stt_display_final = df_stt_display[
                ["Varian", "STT Waste (Kg)", "Total Reject Detail (Kg)", "Total Waste (Kg)", "Output (pcs)", "Output (Kg)", "Total Input (Kg)", "Persentase Waste (%)"]
            ].sort_values(by="Persentase Waste (%)", ascending=False).reset_index(drop=True)
            
            # Filter baris yang benar-benar kosong (semua nilai numerik 0)
            df_stt_display_final = df_stt_display_final[
                (df_stt_display_final["Total Waste (Kg)"] > 0) | 
                (df_stt_display_final["Output (pcs)"] > 0)
            ].reset_index(drop=True)

            st.dataframe(
                df_stt_display_final,
                use_container_width=True,
                height=300
            )
        else:
            st.info("Tidak ada data STT Waste/Output yang diinput pada filter ini.")
        
        st.markdown("---")
        
        # --- Data Detail Reject ---
        df_display_reject = df_filtered[
            df_filtered["Jenis Reject"].astype(str).str.strip().isin(JENIS_REJECT_OPTIONS)
        ].copy()
        
        st.subheader("Data Detail Reject Per Mesin/Varian (Kg)")
        
        if not df_display_reject.empty:
            
            # Kelompokkan data reject detail berdasarkan Mesin/Varian/Jenis Reject dan tampilkan Jam
            reject_cols = ["Mesin","Varian","Jenis Reject", "Koreksi", "Total Reject"] + HOURLY_REJECT_COLS
            
            df_display_reject_grouped = df_display_reject[reject_cols].reset_index(drop=True)
            
            # Rename kolom Total Reject menjadi Total (Kg) untuk kejelasan
            df_display_reject_grouped.rename(columns={"Total Reject": "Total (Kg)"}, inplace=True)

            st.dataframe(
                df_display_reject_grouped,
                use_container_width=True,
                height=350
            )
        else:
            st.info("Tidak ada data detail reject yang diinput pada filter ini.")

    st.divider()

    # ----------------------------------------------------------
    # 4. ALAT DIAGNOSTIK: Hapus Baris Cacat STT_DUMMY (PENTING!)
    # ----------------------------------------------------------
    st.header("⚙️ Alat Diagnostik Data")
    st.warning("Gunakan tombol ini HANYA jika baris 'STT_DUMMY_OUTPUT' yang cacat masih muncul. Baris cacat adalah jika **Jenis Reject, Varian, dan Mesin** semuanya terisi **'STT_DUMMY_OUTPUT'**.")
    
    if st.button("🔴 Hapus Baris Data Cacat Permanen"):
        
        # Muat data mentah terbaru tanpa pembersihan cache
        df_full_raw = load_data()

        # Buat filter untuk data yang TIDAK VALID (Jenis Reject = DUMMY AND Varian = DUMMY AND Mesin = DUMMY)
        filter_invalid_dummy = (
            (df_full_raw["Jenis Reject"].astype(str).str.strip() == STT_DUMMY_MESIN) & 
            (df_full_raw["Varian"].astype(str).str.strip() == STT_DUMMY_MESIN) &
            (df_full_raw["Mesin"].astype(str).str.strip() == STT_DUMMY_MESIN) 
        )
        
        rows_to_delete_count = filter_invalid_dummy.sum()
        
        if rows_to_delete_count > 0:
            # Buat DataFrame baru yang hanya berisi baris yang VALID
            df_cleaned = df_full_raw[~filter_invalid_dummy].copy()
            
            # Simpan data yang sudah bersih ke CSV
            if save_data(df_cleaned, "Data Cacat Berhasil Dihapus"):
                # Hapus cache data utama
                get_reject_data.clear() 
                st.success(f"✅ Berhasil menghapus **{rows_to_delete_count}** baris data cacat STT_DUMMY_OUTPUT. Mohon Muat Ulang Halaman (Ctrl+R) sekarang.")
                
                # Tambahkan tombol muat ulang untuk kenyamanan
                time.sleep(1) # Beri waktu notifikasi muncul
                st.button("Klik untuk Muat Ulang Halaman", on_click=st.rerun)

            else:
                st.error("Gagal menyimpan data yang sudah dibersihkan. Cek izin file.")
        else:
            st.info("Tidak ditemukan baris STT_DUMMY cacat yang perlu dihapus.")


if __name__ == "__main__":
    input_data_page()