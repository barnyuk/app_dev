"""Token-based authentication for the map service."""

import os

import requests
from dotenv import load_dotenv

from config.settings import root_path

TOKEN_URL = 'https://xn--80atti9b.xn--80ad2a0b1c.xn--90ais/elitegis/tokens/generateToken/'
REQUEST_TIMEOUT = 30
user_data = {
    'username':None,
    'password':None
}

def get_token(username=None, password=None) -> str:
    """Read credentials from the environment and request a token."""
    #load_dotenv(root_path / '.env')
    #username = os.getenv('login')
    #password = os.getenv('password')
    if not username or not password:
        username, password = user_data['username'], user_data['password']

    response = requests.post(
        TOKEN_URL,
        data={'username': username, 'password': password, 'f': 'json'},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get('token') if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise ValueError('Неверное имя пользователя или пароль')
    return token