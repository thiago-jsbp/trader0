# -*- coding: utf-8 -*-

from .common import *
from ccxt.base.errors import AuthenticationError, ExchangeError, ExchangeNotAvailable, RequestTimeout
from requests.exceptions import ConnectionError, HTTPError, ReadTimeout
from socket import gaierror, timeout
from urllib3.exceptions import MaxRetryError, NewConnectionError, ReadTimeoutError
import ccxt
import numpy as np

db_suffix = '.ww'
net_errors = (AuthenticationError, ExchangeError, ExchangeNotAvailable, RequestTimeout,
              ConnectionError, HTTPError, ReadTimeout,
              gaierror, timeout,
              MaxRetryError, NewConnectionError, ReadTimeoutError)
secs_in_hour, tabs = 3600, 2
net_errors_counter = 0


def exchange(exchange_id):
    """
        todo

    :param exchange_id:
    :return:
    """

    argv = locals()
    exchange_obj = None

    try:
        auth = setup(exchange_id.upper(), config_path='bin/.keys')
        exchange_obj = getattr(ccxt, exchange_id)(dict(auth))
        exchange_obj.options['warnOnFetchOpenOrdersWithoutSymbol'] = False
        if not int(setup()['offline']):
            exchange_obj.loadMarkets()

    except net_errors:
        return _net_except(exchange_obj, exchange, argv, format_exc())
    except:
        logg(format_exc(), exchange_id)
    return exchange_obj


def symbols(exchange_obj, btc_only=True):
    """
        todo

    :param exchange_obj:
    :param btc_only:
    :return:
    """

    argv = locals()
    tmp = {}

    try:
        wait()
        tmp = {d['symbol']: (d['limits']['amount']['max'],
                             d['limits']['amount']['min'],
                             d['precision']['amount'],
                             d['limits']['price']['max'],
                             d['limits']['price']['min'],
                             d['precision']['price'],)
               for d in exchange_obj.fetch_markets()
               if d['active']}

        if btc_only:
            return {k: v for k, v in tmp.items()
                    if (k[:4] == 'BTC/' or k[-4:] == '/BTC')
                    and 'BNB' not in k}

    except net_errors:
        return _net_except(exchange_obj, symbols, argv, format_exc())
    except:
        logg(format_exc(), exchange_obj.id)
    return tmp


def history(exchange_obj, symbol, cutoff=None, hours=1):
    """
        Many thanks to "xmatthias":
        https://github.com/xmatthias
        https://github.com/ccxt/ccxt/issues/5697

    :param exchange_obj:
    :param symbol:
    :param cutoff:
    :param hours:
    :return:
    """

    argv = locals()
    void = np.array([], dtype='float64').reshape(0, 3)

    try:
        if cutoff is None:
            cutoff = time()
        since = int(1E3 * (cutoff - hours * secs_in_hour))
        until = int(1E3 * cutoff)

        wait()
        data = exchange_obj.fetch_trades(symbol, since=since)
        if not len(data):
            return void

        old_id = data[-1]['id']
        while data[-1]['timestamp'] < until and not halt():
            wait()
            tmp = exchange_obj.fetch_trades(symbol, params={
                'fromId': old_id}, limit=1000)
            new_id = tmp[-1]['id']

            if len(tmp) and new_id != old_id:
                data.extend(tmp)
                old_id = data[-1]['id']
            else:
                break

        hh = [(e, a, p) for t, (e, a, p) in sorted(
            {int(d['id']): (d['timestamp'] / 1E3,
                            [1, -1][d['side'] == 'sell'] * d['amount'],
                            d['price']) for d in data}.items()
        ) if since < 1E3 * e <= until]
        if len(hh):
            return np.array(hh)

    except net_errors:
        return _net_except(exchange_obj, history, argv, format_exc())
    except:
        logg(format_exc(), exchange_obj.id)
    return void


def book(exchange_obj, symbol, margin=0):
    """
        todo

    :param exchange_obj:
    :param symbol:
    :param margin:
    :return:
    """

    argv = locals()
    void = np.array([], dtype='float64').reshape(0, 2)

    try:
        wait()
        req = exchange_obj.fetch_order_book(symbol, limit=300)
        asks = [(p, a) for p, a in sorted(req['asks'])]
        bids = [(p, -a) for p, a in sorted(req['bids'], reverse=True)]

        if margin > 0:
            if type(margin) == float:
                h_ask = (1 + margin / 100) * asks[0][0]
                l_bid = (1 - margin / 100) * bids[0][0]
                asks = [(p, a) for p, a in asks if p <= h_ask]
                bids = [(p, a) for p, a in bids if p >= l_bid]
            else:
                asks, bids = asks[:margin], bids[:margin]

        bb = sorted(asks + bids, reverse=True)
        if len(bb):
            return np.array(bb)

    except IndexError:
        pass
    except net_errors:
        return _net_except(exchange_obj, book, argv, format_exc())
    except:
        logg(format_exc(), exchange_obj.id)
    return void


def balance(exchange_obj):
    """
        todo

    :param exchange_obj:
    :return:
    """

    argv = locals()
    tmp = {'BTC': (0., 0.)}

    try:
        wait()
        req = exchange_obj.fetch_balance()

        for currency, available in req['free'].items():
            on_orders = req['used'][currency]
            if available + on_orders > 0:
                tmp[currency] = (available, on_orders)

        if exchange_obj.id == 'bittrex' and 'BTXCRD' in tmp:
            del tmp['BTXCRD']

    except net_errors:
        return _net_except(exchange_obj, balance, argv, format_exc())
    except:
        logg(format_exc(), exchange_obj.id)
    return tmp


def fire(exchange_obj, symbol, amount, price, order_type='limit'):
    """
        todo

    :param exchange_obj:
    :param symbol:
    :param amount:
    :param price:
    :param order_type:
    :return:
    """

    argv = locals()
    req = {}

    try:
        if not setup()['runMode'].upper() in ['LIVE', 'TEST']:
            return 'PLAY_' + str(int(1E3 * time())), price

        params = (symbol, order_type, 'buy', amount, price) if amount > 0 else (
            symbol, order_type, 'sell', -amount, price)

        wait()
        req = exchange_obj.create_order(*params)
        _cached(exchange_obj, req)

    except net_errors:
        return _net_except(exchange_obj, fire, argv, format_exc())
    except:
        logg(format_exc(), exchange_obj.id)
    return req['id'], req['price']


def orders(exchange_obj, id_only=True):
    """
        todo

    :param exchange_obj:
    :param id_only:
    :return:
    """

    argv = locals()
    tmp = set()

    try:
        if not setup()['runMode'].upper() in ['LIVE', 'TEST']:
            return tmp

        orders_cache = _cached(exchange_obj)['data']
        eligible = {order_dict['symbol'] for order_dict in orders_cache.values()}

        for ss in eligible:
            wait()
            for order_dict in exchange_obj.fetch_open_orders(symbol=ss):
                if order_dict['status'] == 'open':
                    side = -1 if order_dict['side'] == 'sell' else 1
                    tmp.add((order_dict['id'], order_dict['timestamp'],
                             order_dict['symbol'], side * order_dict['amount'],
                             order_dict['price']))
        if id_only and len(tmp):
            return set(list(zip(*tmp))[0])

    except net_errors:
        return _net_except(exchange_obj, orders, argv, format_exc())
    except:
        logg(format_exc(), exchange_obj.id)
    return tmp


def cancel(exchange_obj, order_id):
    """
        todo

    :param exchange_obj:
    :param order_id:
    :return:
    """

    argv = locals()
    minus_sign = '-'

    try:
        if not setup()['runMode'].upper() in ['LIVE', 'TEST']:
            return minus_sign + order_id

        orders_cache = _cached(exchange_obj)['data']
        if order_id not in orders_cache:
            return minus_sign

        cached_order = orders_cache[order_id]
        symbol = cached_order['symbol']

        if cached_order['status'] == 'open':
            wait()
            exchange_obj.cancel_order(order_id, symbol)

            cached_order['status'] = 'canceled'
            _cached(exchange_obj, cached_order)
            return minus_sign + order_id.upper()

    except net_errors:
        return _net_except(exchange_obj, cancel, argv, format_exc())
    except:
        logg(format_exc(), exchange_obj.id)
    return minus_sign


def _cached(exchange_obj, order_data=None, before_millis=None):
    """
        todo

    :param exchange_obj:
    :param order_data:
    :param before_millis:
    :return:
    """

    argv = locals()
    db_file = exchange_obj.id + db_suffix
    tmp = {}

    try:
        if before_millis is None:
            before_millis = exchange_obj.milliseconds() - 7 * 24 * secs_in_hour * 1000

        # DEPRECATED: purge_cached_orders()
        # https://github.com/ccxt/ccxt/issues/7681
        # exchange_obj.purge_cached_orders(before_millis)

        template = {'data': {}, 'last': 0., }
        tmp = disk(db_file)
        if not tmp.keys() == template.keys():
            tmp = template

        if order_data is not None:
            tmp['data'][order_data['id']] = order_data

        now = time()
        if now - tmp['last'] > secs_in_hour:
            wait()
            tmp['data'].update({order_dict['id']: order_dict
                                for order_dict in exchange_obj.fetch_open_orders()})
            tmp['last'] = now
            debug(msgg(701), exchange_obj.id, tabs)
        tmp['data'] = {k: v for k, v in tmp['data'].items()
                       if v['timestamp'] >= before_millis}
        disk(db_file, tmp)

    except net_errors:
        return _net_except(exchange_obj, _cached, argv, format_exc())
    except:
        logg(format_exc(), exchange_obj.id)
    return tmp


def _net_except(exchange_obj, func_obj, func_params, errmsg, delay=12):
    """
        todo

    :param exchange_obj:
    :param func_obj:
    :param func_params:
    :param errmsg:
    :param delay:
    :return:
    """

    global net_errors_counter

    try:
        if net_errors_counter < 5:
            debug(msgg(702, delay), exchange_obj.id)
            wait(seconds=delay)
            net_errors_counter += 1
            return func_obj(**func_params)
        else:
            logg(errmsg, exchange_obj.id)
            net_errors_counter = 0

    except:
        logg(format_exc(), exchange_obj.id)
