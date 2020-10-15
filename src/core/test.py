# -*- coding: utf-8 -*-

from .web import *

db_suffix = '.tt'


def public_api(exchange_id, current_time):
    """
        todo

    :param exchange_id:
    :param current_time:
    :return:
    """

    tmp = {'Ok': False}
    func_name = 'public_api()'

    try:
        logg('', exchange_id)
        logg(msgg(601, (exchange_id.upper(), func_name)), exchange_id)

        if int(setup()['offline']):
            tmp['offline'] = True
        else:
            tmp['Exchange'] = exchange(exchange_id)
            assert 'ccxt' in str(type(tmp['Exchange']))

            tmp['Symbols'] = symbols(tmp['Exchange'], btc_only=True)
            assert type(tmp['Symbols']) == dict and len(tmp['Symbols'])

            hh, ss = [], set(tmp['Symbols'])
            while len(ss) and not (type(hh) == np.ndarray and len(hh)):
                hh = history(tmp['Exchange'], ss.pop())

            tmp['History'] = hh
            assert type(tmp['History']) == np.ndarray and len(
                tmp['History'])

            b_key = 'Book (INT=5)'
            tmp[b_key] = book(tmp['Exchange'], ss.pop(), 5)
            assert type(tmp[b_key]) == np.ndarray

            b_key = 'Book (FLOAT=.5)'
            tmp[b_key] = book(tmp['Exchange'], ss.pop(), .5)
            assert type(tmp[b_key]) == np.ndarray

            b_key = 'Book (N=0)'
            tmp[b_key] = book(tmp['Exchange'], ss.pop(), 0)
            assert type(tmp[b_key]) == np.ndarray
        tmp['Ok'] = True
    except:
        tmp['CRASH_REPORT'] = format_exc()

    logg('', exchange_id)
    logg(msgg(602, (exchange_id.upper(), func_name, tmp)), exchange_id)
    db_file = exchange_id + db_suffix
    cache = {k: v for k, v in disk(db_file).items()
             if (current_time - k) / secs_in_hour < int(setup()['dbLimitHours'])}

    tmp['Exchange'] = str(tmp['Exchange'])  # in order to avoid "TypeError: can't pickle _thread.RLock objects"
    if current_time in cache:
        cache[current_time][func_name] = tmp
    else:
        cache[current_time] = {func_name: tmp}
    disk(db_file, cache)
    return tmp


def private_api(exchange_id, current_time):
    """
        todo

    :param exchange_id:
    :param current_time:
    :return:
    """

    tmp = {'Ok': False}
    func_name = 'private_api()'

    try:
        logg('', exchange_id)
        logg(msgg(601, (exchange_id.upper(), func_name)), exchange_id)

        if int(setup()['offline']):
            tmp['offline'] = True
        else:
            tmp['Exchange'] = exchange(exchange_id)
            assert 'ccxt' in str(type(tmp['Exchange']))

            tmp['Balance'] = balance(tmp['Exchange'])
            assert type(tmp['Balance']) == dict and len(tmp['Balance'])

            params = {'exchange_obj': tmp['Exchange'], 'symbol': 'BTC/USDT', }
            btc_amount, usd_amount = .001, 10.

            if tmp['Balance']['BTC'][0] >= btc_amount:
                params['amount'] = -btc_amount
                price = book(tmp['Exchange'], params['symbol'], 20)[0, 0]
                price = max(price, usd_amount / btc_amount)
                params['price'] = rnd(float(price), 8)

                tmp['Fire.SELL'] = {'(order_id, price)': fire(**params)}
                params['exchange_obj'] = str(
                    params['exchange_obj'])  # in order to avoid "TypeError: can't pickle _thread.RLock objects"
                tmp['Fire.SELL'].update(params)
                assert None not in tmp

            if 'USDT' in tmp['Balance'] and tmp['Balance']['USDT'][0] >= usd_amount:
                price = book(tmp['Exchange'], params['symbol'], 20)[-1, 0]
                params['price'] = rnd(float(price), 8)
                params['amount'] = max(btc_amount, usd_amount / params['price'])

                tmp['Fire.BUY'] = {'(order_id, price)': fire(**params)}
                params['exchange_obj'] = str(
                    params['exchange_obj'])  # in order to avoid "TypeError: can't pickle _thread.RLock objects"
                tmp['Fire.BUY'].update(params)
                assert None not in tmp

            tmp['Orders'] = orders(tmp['Exchange'])
            assert tmp['Orders'] is not None

            tmp['Orders_FULL'] = orders(tmp['Exchange'], id_only=False)
            assert tmp['Orders'] is not None

            orders_buffer = set()
            if 'Fire.SELL' in tmp:
                orders_buffer.add(tmp['Fire.SELL']['(order_id, price)'][0])
            if 'Fire.BUY' in tmp:
                orders_buffer.add(tmp['Fire.BUY']['(order_id, price)'][0])

            tmp['Cancel'] = {cancel(tmp['Exchange'], order_id)
                             for order_id in orders_buffer}
            assert None not in tmp['Cancel']
        tmp['Ok'] = True
    except:
        tmp['CRASH_REPORT'] = format_exc()

    logg('', exchange_id)
    logg(msgg(602, (exchange_id.upper(), func_name, tmp)), exchange_id)
    db_file = exchange_id + db_suffix
    cache = {k: v for k, v in disk(db_file).items()
             if (current_time - k) / secs_in_hour < int(setup()['dbLimitHours'])}

    tmp['Exchange'] = str(tmp['Exchange'])  # in order to avoid "TypeError: can't pickle _thread.RLock objects"
    if current_time in cache:
        cache[current_time][func_name] = tmp
    else:
        cache[current_time] = {func_name: tmp}
    disk(db_file, cache)
    return tmp
