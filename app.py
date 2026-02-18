import streamlit as st

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Monitoring Produksi",
    page_icon="📊",
    layout="wide"
)

# --- INISIALISASI SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

# --- DATA LOGIN SEDERHANA ---
CORRECT_USERNAME = "admin"
CORRECT_PASSWORD = "admin123"

def check_login(username, password):
    return username == CORRECT_USERNAME and password == CORRECT_PASSWORD

# --- JIKA SUDAH LOGIN, LANGSUNG KE DASHBOARD ---
if st.session_state.logged_in:
    st.switch_page("pages/dashboard_page.py")

# --- SIDEBAR LOGIN INFO ---
with st.sidebar:
    st.subheader("🔐 Akses Terbatas")
    st.warning("Anda harus login untuk mengakses data.")
    st.markdown("---")
    st.info("Username: `admin`")
    st.info("Password: `admin123`")

# --- TAMPILAN LOGIN ---
st.markdown(
    "<h1 style='text-align: center; color: #1f77b4;'>🔒 Sistem Monitoring Produksi</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; font-size: 1.1em; color: #555;'>Masukkan kredensial untuk mengakses Dashboard.</p>",
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    with st.container(border=True):
        st.subheader("Form Login")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Masuk", use_container_width=True)

        if submit_button:
            if check_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login berhasil! Mengarahkan ke Dashboard...")
                st.switch_page("pages/dashboard_page.py")
            else:
                st.error("Username atau password salah.")

st.markdown("---")
st.caption("Pastikan Anda memiliki hak akses Administrator.")
