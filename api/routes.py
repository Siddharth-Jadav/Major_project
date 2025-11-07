from flask import Blueprint, jsonify, request, send_from_directory
import os

from services.demo_data import (
    list_symbols,
    quotes_all,
    summary_for_symbol,
    technicals_for_symbol,
    fundamentals_for_symbol,
)

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.get('/health')
def health():
    return {'status': 'ok'}


# DEMO-ONLY: These standard endpoints now read from the CSV

@bp.get('/tickers')
def tickers():
    q = (request.args.get('q') or '').strip()
    limit_param = request.args.get('limit', '200')
    if str(limit_param).lower() == 'all':
        # get total
        total = list_symbols(q=q, limit=10**9, offset=0)['total']
        limit = total
    else:
        try:
            limit = int(limit_param)
        except Exception:
            limit = 200

    try:
        offset = int(request.args.get('offset', '0'))
    except Exception:
        offset = 0

    return jsonify(list_symbols(q=q, limit=limit, offset=offset))


@bp.get('/quotes_all')
def quotes():
    total = list_symbols(q='', limit=10**9, offset=0)['total']
    limit_param = request.args.get('limit', '200')
    if str(limit_param).lower() == 'all':
        limit = total
    else:
        try:
            limit = int(limit_param)
        except Exception:
            limit = 200
    try:
        offset = int(request.args.get('offset', '0'))
    except Exception:
        offset = 0

    return jsonify(quotes_all(limit=limit, offset=offset))


@bp.get('/summary')
def summary():
    symbol = (request.args.get('symbol') or '').strip()
    if not symbol:
        return jsonify(error='symbol is required'), 400
    try:
        return jsonify(summary_for_symbol(symbol))
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception:
        return jsonify(error='Failed to create demo summary'), 500


@bp.get('/technicals')
def technicals():
    symbol = (request.args.get('symbol') or '').strip()
    if not symbol:
        return jsonify(error='symbol is required'), 400
    try:
        return jsonify(technicals_for_symbol(symbol))
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception:
        return jsonify(error='Failed to fetch demo technicals'), 500


@bp.get('/fundamentals')
def fundamentals():
    symbol = (request.args.get('symbol') or '').strip()
    if not symbol:
        return jsonify(error='symbol is required'), 400
    try:
        return jsonify(fundamentals_for_symbol(symbol))
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception:
        return jsonify(error='Failed to fetch demo fundamentals'), 500


@bp.get('/csv')
def download_csv():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    return send_from_directory(data_dir, "stock_static_100.csv", as_attachment=True)
