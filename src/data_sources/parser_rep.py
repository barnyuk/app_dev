"""Fetch and normalize base-station data from the map service."""

import math

import requests

OPERATOR_MNC = {'A1': '1', 'BEST': '4', 'BE_CLOUD': '6'}
MAP_URL = 'https://xn--80atti9b.xn--80ad2a0b1c.xn--90ais/elitegis/rest/services/TEST/Test1sl/MapServer/4/query'
REQUEST_TIMEOUT = 30
STATUS = 'эксплуатация'


def validate_station(operator: str, bsn_id: str) -> str:
    """Validate identifiers before using them in queries or file names."""
    if operator not in OPERATOR_MNC:
        raise ValueError(f'Unsupported operator: {operator}')
    bsn_id = str(bsn_id)
    if not bsn_id or not bsn_id.isascii() or not bsn_id.isdigit():
        raise ValueError('Base-station number must contain only ASCII digits.')
    return bsn_id


def parse_api_response(data_list: list) -> tuple[dict, bool]:
    if not data_list:
        raise ValueError('No base-station data found.')
    data = data_list[0]['attributes']
    oblast, district, city, street = (
        data.get(key) for key in ('oblast', 'district', 'city', 'street')
    )
    address = ', '.join(part for part in (
        f'{oblast} обл.' if oblast else '',
        f'{district} р-н.' if district else '',
        f'н.п. {city}' if city else '',
        street or '',
    ) if part)
    result = {'address': address, 'standarts': [], 'freq': {}}

    for item in data_list:
        attrs = item.get('attributes') or {}
        azimuth, standard, frequency, status = (
            attrs.get(key) for key in ('azimuth', 'standart', 'freq', 'status')
        )
        if standard is None or frequency is None or azimuth is None or status.lower()!=STATUS:
            continue
        azimuth = float(azimuth)
        numeric_frequency = float(frequency)
        if (not math.isfinite(azimuth) or not math.isfinite(numeric_frequency)
                or numeric_frequency <= 0 or not numeric_frequency.is_integer()):
            raise ValueError('Invalid frequency or azimuth in map response.')
        frequency = str(int(numeric_frequency))
        standard = str(standard)
        if standard not in result['standarts']:
            result['standarts'].append(standard)
        azimuths = result['freq'].setdefault(frequency, [])
        if azimuth not in azimuths:
            azimuths.append(azimuth)

    result['freq'] = {
        key: sorted(values)
        for key, values in sorted(result['freq'].items(), key=lambda item: int(item[0]))
    }
    if not result['freq']:
        raise ValueError('No usable frequencies found for this base station.')
    return result, city == 'Минск'


def get_data_from_maps(operator: str, bsn_id: str, token: str) -> tuple[dict, bool]:
    bsn_id = validate_station(operator, bsn_id)
    if not token:
        raise ValueError('An authentication token is required.')
    response = requests.get(
        MAP_URL,
        params={
            'f': 'json',
            'token': token,
            'where': f"mnc = '{OPERATOR_MNC[operator]}' AND bsn = '{bsn_id}'",
            'returnCountOnly': 'false',
            'outFields': '*',
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or 'error' in payload:
        raise ValueError('The map service rejected the query.')
    features = payload.get('features')
    if not isinstance(features, list):
        raise ValueError('Invalid map response: missing features.')
    if not features:
        raise ValueError(f'No data found for {operator} / БС {bsn_id}.')
    return parse_api_response(features)