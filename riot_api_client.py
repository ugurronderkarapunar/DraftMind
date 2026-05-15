import requests
import streamlit as st

@st.cache_data(ttl=86400)
def get_champion_square(champion_name):
    """Riot Data Dragon'dan şampiyon portresini döndürür."""
    name_formatted = champion_name.replace(" ", "").replace("'", "").lower()
    url = f"https://ddragon.leagueoflegends.com/cdn/13.18.1/img/champion/{name_formatted.capitalize()}.png"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return url
    except:
        pass
    # Yedek görsel
    return "https://ddragon.leagueoflegends.com/cdn/13.18.1/img/champion/Default.png"
