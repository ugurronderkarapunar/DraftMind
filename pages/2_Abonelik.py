import streamlit as st
from auth_service import require_auth, AuthService
from db_utils import generate_personal_key

@require_auth
def main():
    st.title("Pro Üyelik")
    user = st.session_state.user
    if user['is_pro']:
        st.success("Zaten Pro üyesisiniz. Sınırsız analiz kullanabilirsiniz.")
    else:
        tab1, tab2 = st.tabs(["Aktivasyon Kodu", "Kişisel Anahtar Üret"])
        with tab1:
            code = st.text_input("Pro Kodu", type="password")
            if st.button("Yükselt"):
                if code == "PRO2026" or code == generate_personal_key(user['username']):
                    AuthService.set_pro(user['username'])
                    st.session_state.user['is_pro'] = 1
                    st.success("Tebrikler, Pro üye oldunuz!")
                    st.rerun()
                else:
                    st.error("Geçersiz kod.")
        with tab2:
            st.write("Admin şifresiyle kişisel anahtar oluşturun.")
            admin_pass = st.text_input("Admin Şifresi", type="password")
            if st.button("Anahtar Üret"):
                if admin_pass == "admin123":
                    key = generate_personal_key(user['username'])
                    st.success(f"Anahtarınız: **{key}**")
                else:
                    st.error("Yetkisiz erişim.")

if __name__ == "__main__":
    main()
