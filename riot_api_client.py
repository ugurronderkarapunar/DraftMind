import requests
import streamlit as st

@st.cache_data(ttl=86400)
def get_champion_square(champion_name):
    """Riot Data Dragon'dan şampiyon portresini döndürür."""
    name_formatted = champion_name.replace(" ", "").replace("'", "").lower()
    # Bazı özel durumlar
    special_names = {
        "kai'sa": "kaisa",
        "khazix": "khazix",
        "velkoz": "velkoz",
        "jarvaniv": "jarvaniv",
        "missfortune": "missfortune",
        "twistedfate": "twistedfate",
        "masteryi": "masteryi",
        "leesin": "leesin",
    }
    name_formatted = special_names.get(name_formatted, name_formatted)
    url = f"https://ddragon.leagueoflegends.com/cdn/13.18.1/img/champion/{name_formatted.capitalize()}.png"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return url
    except:
        pass
    return "https://ddragon.leagueoflegends.com/cdn/13.18.1/img/champion/Default.png"
