import os
import re
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')

# GoXtop API configuration
GOXTOP_BASE_URL = os.getenv('GOXTOP_BASE_URL', 'https://goxtop.com/api/v.1').rstrip('/')
GOXTOP_API_KEY = os.getenv('GOXTOP_API_KEY', '').strip()
GOXTOP_CREATE_PATH = os.getenv('GOXTOP_CREATE_PATH', '/create')
GOXTOP_TIMEOUT = int(os.getenv('GOXTOP_TIMEOUT', '20'))
DRY_RUN = os.getenv('DRY_RUN', 'true').strip().lower() == 'true'


def env_code(name):
    """Read a supplier product/denomination code from Render env vars."""
    return os.getenv(name, '').strip()


# The values in provider_code must be the exact GoXtop Pack/denom values.
# Keep these on the server; never expose the GoXtop API key to the browser.
CATALOG = {
    'freefire': {
        'game_code': os.getenv('GOXTOP_FREEFIRE_GAME_CODE', 'freefire_global').strip(),
        'products': [
            {'id': 'ff-0', 'name': '25 Diamonds', 'price': 35, 'provider_code': env_code('FF_25_CODE')},
            {'id': 'ff-1', 'name': '50 Diamonds', 'price': 50, 'provider_code': env_code('FF_50_CODE')},
            {'id': 'ff-2', 'name': '115 Diamonds', 'price': 100, 'provider_code': env_code('FF_115_CODE')},
            {'id': 'ff-3', 'name': '240 Diamonds', 'price': 220, 'provider_code': env_code('FF_240_CODE')},
            {'id': 'ff-4', 'name': '610 Diamonds', 'price': 550, 'provider_code': env_code('FF_610_CODE')},
            {'id': 'ff-5', 'name': '1240 Diamonds', 'price': 1100, 'provider_code': env_code('FF_1240_CODE')},
            {'id': 'ff-6', 'name': '2530 Diamonds', 'price': 2130, 'provider_code': env_code('FF_2530_CODE')},
            {'id': 'ff-7', 'name': 'Weekly Membership', 'price': 220, 'provider_code': env_code('FF_WEEKLY_CODE')},
            {'id': 'ff-8', 'name': 'Monthly Membership', 'price': 1048, 'provider_code': env_code('FF_MONTHLY_CODE')},
        ],
    },
    'efootball': {
        'game_code': os.getenv('GOXTOP_EFOOTBALL_GAME_CODE', 'efootball').strip(),
        'products': [],
    },
}


def goxtop_request(method, path, **kwargs):
    if not GOXTOP_API_KEY:
        raise RuntimeError('GOXTOP_API_KEY is not configured on the server')

    headers = dict(kwargs.pop('headers', {}) or {})
    headers['x-api-key'] = GOXTOP_API_KEY
    headers.setdefault('Accept', 'application/json')
    headers.setdefault('Content-Type', 'application/json')

    url = f"{GOXTOP_BASE_URL}/{path.lstrip('/')}"
    return requests.request(method, url, headers=headers, timeout=GOXTOP_TIMEOUT, **kwargs)


def safe_json(response):
    try:
        return response.json()
    except ValueError:
        return {'raw': response.text[:500]}


def find_product(game, product_id):
    for product in CATALOG.get(game, {}).get('products', []):
        if product['id'] == product_id:
            return product
    return None


def valid_order_id(order_id):
    return bool(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', order_id or ''))


@app.get('/')
def home():
    return send_from_directory('.', 'index.html')


@app.get('/api/health')
def health():
    return jsonify({
        'ok': True,
        'dry_run': DRY_RUN,
        'goxTop_configured': bool(GOXTOP_API_KEY),
    })


@app.get('/api/games')
def games():
    response = goxtop_request('GET', '/games')
    return jsonify(safe_json(response)), response.status_code


@app.get('/api/products/<game_code>')
def products(game_code):
    response = goxtop_request('GET', f'/products/{game_code}')
    return jsonify(safe_json(response)), response.status_code


@app.get('/api/balance')
def balance():
    response = goxtop_request('GET', '/balance')
    return jsonify(safe_json(response)), response.status_code


@app.post('/api/orders')
def create_order():
    body = request.get_json(silent=True) or {}
    game = str(body.get('game', '')).lower().strip()
    product_id = str(body.get('product_id', '')).strip()
    user_id = str(body.get('user_id', '')).strip()
    server_id = str(body.get('server_id', '')).strip()

    if game not in CATALOG:
        return jsonify({'success': False, 'error': 'Unsupported game'}), 400

    if not user_id or len(user_id) > 80 or not re.fullmatch(r'[A-Za-z0-9_\- ]+', user_id):
        return jsonify({'success': False, 'error': 'Invalid player/user ID'}), 400

    product = find_product(game, product_id)
    if not product:
        return jsonify({'success': False, 'error': 'Invalid product'}), 400

    if not product['provider_code']:
        return jsonify({
            'success': False,
            'error': 'Supplier product code is not configured for this package',
        }), 503

    partner_orderid = (
        'LAMA-'
        + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        + '-'
        + uuid.uuid4().hex[:8].upper()
    )

    # GoXtop reseller API uses denom and userid for the create request.
    # provider_code must be the exact Pack value returned by GoXtop products API.
    payload = {
        'partner_orderid': partner_orderid,
        'game': CATALOG[game]['game_code'],
        'denom': product['provider_code'],
        'userid': user_id,
    }

    # Keep optional server support for games that require it.
    if server_id:
        payload['server_code'] = server_id

    if DRY_RUN:
        return jsonify({
            'success': True,
            'dry_run': True,
            'order': {
                'partner_orderid': partner_orderid,
                'game': game,
                'product': product['name'],
                'amount': product['price'],
                'status': 'awaiting_payment',
                'supplier_payload_preview': {
                    **payload,
                    'note': 'Not sent because DRY_RUN=true',
                },
            },
        })

    response = goxtop_request('POST', GOXTOP_CREATE_PATH, json=payload)
    return jsonify(safe_json(response)), response.status_code


@app.get('/api/orders/<partner_orderid>')
def order_status(partner_orderid):
    if not valid_order_id(partner_orderid):
        return jsonify({'success': False, 'error': 'Invalid order ID'}), 400

    response = goxtop_request('GET', f'/{partner_orderid}')
    return jsonify(safe_json(response)), response.status_code


@app.post('/api/orders/<partner_orderid>/track')
def track_order(partner_orderid):
    if not valid_order_id(partner_orderid):
        return jsonify({'success': False, 'error': 'Invalid order ID'}), 400

    response = goxtop_request('POST', f'/{partner_orderid}/track')
    return jsonify(safe_json(response)), response.status_code


@app.errorhandler(Exception)
def handle_error(error):
    app.logger.exception(error)
    return jsonify({'success': False, 'error': 'Server error'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')))
