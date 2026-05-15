import streamlit as st
from db_utils import set_pro

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("Lütfen giriş yapın.")
    st.stop()

st.title("Pro Üyelik")

user = st.session_state.user
if user['is_pro']:
    st.success("Zaten Pro üyesisiniz. Sınırsız analiz kullanabilirsiniz.")
else:
    st.write("Pro üyelik ile günlük limitsiz analiz ve öncelikli özelliklere erişim sağlayın.")
    code = st.text_input("Pro Kodu", type="password")
    if st.button("Yükselt"):
        if code == "PRO2026":
            set_pro(user['username'])
            st.session_state.user['is_pro'] = 1
            st.success("Tebrikler, Pro üye oldunuz!")
            st.rerun()
        else:
            st.error("Geçersiz kod.")
