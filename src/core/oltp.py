# -*- coding: utf-8 -*-

from .web import *
from random import sample

db_suffix = '.ot'
exchange_obj = None
cache, nakamoto = None, None
btc_quota, usd_quota = .001, 10.


def probe(exchange_id, broadway):
    """
        Detecting some good trading opportunities...

    :param exchange_id:
    :param broadway:
    :return:
    """

    global cache, exchange_obj

    try:
        if halt():
            return

        t_delta = time()
        exchange_obj = exchange(exchange_id)
        logg(category=exchange_obj.id)
        logg(msgg(501), exchange_obj.id)

        bulls = {k: v for k, v in broadway.items() if v > 0}
        bears = {k: -v for k, v in broadway.items() if v < 0}
        cache = {}

        if not int(setup()['offline']):
            _clear(bears)
            _reload()
            holdings = _report()
            assert holdings is not None

            if holdings[2] >= usd_quota:
                if len(bulls):
                    goal = _chase(bulls)
                    if goal not in [0, None]:
                        logg(msgg(502, goal), exchange_obj.id)
                else:
                    logg(msgg(503), exchange_obj.id)
            else:
                logg(msgg(504), exchange_obj.id)

        t_delta = time() - t_delta
        logg(msgg(505, secs2human(t_delta)), exchange_obj.id)
        logg(msgg(506), exchange_obj.id)

    except AssertionError:
        logg(msgg(507, 'probe()'), exchange_obj.id)
        debug(format_exc(), exchange_obj.id)
    except:
        logg(format_exc(), exchange_obj.id)


def _update():
    """
        todo

    :return:
    """

    global cache, nakamoto

    try:
        if not len(cache):
            debug('', exchange_obj.id)
            debug('UPDATE: ', exchange_obj.id, tabs)

            orders_full = orders(exchange_obj, id_only=False)
            cache = {'symbols': symbols(exchange_obj),
                     'balance': balance(exchange_obj),
                     'orders': set() if not len(orders_full) else set(
                         list(zip(*orders_full))[0]),
                     'orders_full': orders_full, }
            cache['symbols_fiat'] = {s for s in cache['symbols'] if s[:4] == 'BTC/'}

            if len(cache['symbols_fiat']):
                cache['symbols_usd'] = {s for s in cache['symbols_fiat']
                                        if 'USD' in s or 'PAX' in s}
                if 'BTC/USDT' in cache['symbols_usd']:
                    nakamoto = 'BTC/USDT'
                elif 'BTC/USD' in cache['symbols_usd']:
                    nakamoto = 'BTC/USD'
                else:
                    # For example: 'BTC/EUR', 'BTC/BRL', 'BTC/RUR' etc.
                    ranking = [(_ticker(s)[0], s) for s in cache['symbols_fiat']]
                    nakamoto = sorted((p, s) for p, s in ranking if p > 0)[0][1]
                fee_symbol = nakamoto
            else:
                nakamoto, fee_symbol = 'BTC/FIAT', sample(list(cache['symbols']), 1)
                cache['symbols_usd'] = set()

            cache['fee'] = 100 * exchange_obj.calculate_fee(
                fee_symbol, 'limit', 'buy', 1., 1.)['rate']
            debug('cache ~= ' + str({k: type(v) for k, v
                                     in cache.items()}), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id)


def _clear(broadway):
    """
        Checking for unprofitable/overdue/winner orders.

    :return:
    """

    global cache
    symbol = None

    try:
        take_profit = float(setup()['takeProfit'])
        stop_loss = float(setup()['stopLoss'])
        maturity = int(setup()['maturityHours'])

        logg(category=exchange_obj.id)
        logg('PURGE: ', exchange_obj.id)
        logg(msgg(512, (stop_loss, maturity)), exchange_obj.id)

        _update()
        fix, now = 1 + 2 * cache['fee'] / 100, time()
        for order_id, epoch_millis, symbol, amount, price in cache['orders_full']:
            l_ask, h_bid = _ticker(symbol)
            assert l_ask * h_bid

            buy_price = price / fix / (1 + take_profit / 100)
            underdog = 100 * (h_bid / buy_price - 1) < -stop_loss
            expired = now - epoch_millis / 1E3 > maturity * secs_in_hour
            rewarding = symbol in broadway

            if underdog or expired or rewarding:
                logg(msgg(5131 if underdog else 5132, order_id), exchange_obj.id, tabs)
                cancel(exchange_obj, order_id)
                cache = {}
                wait(seconds=3)

                _update()
                order_id, sell_price = _selling(
                    symbol, margin=-1, fee_adjusted=False)
                cache = {}
                wait(seconds=3)

                assert sell_price > 0
                logg(msgg(510, ('SELL', sell_price)), exchange_obj.id, tabs)
                logg(msgg(511, order_id), exchange_obj.id, tabs)
    except AssertionError:
        logg(msgg(523, ('_purge()', symbol)), exchange_obj.id, tabs)
        debug(format_exc(), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id, tabs)


def _reload():
    """
        Checking for idle money in altcoins.

    :return:
    """

    global cache
    symbol = None

    try:
        logg(category=exchange_obj.id)
        logg('RELOAD: ', exchange_obj.id)
        logg(msgg(508), exchange_obj.id)

        _update()
        for currency, (available, on_orders) in cache['balance'].items():
            if available > 0 == on_orders:
                _update()
                symbol = currency + '/BTC'

                if symbol in cache['symbols']:
                    l_ask, h_bid = _ticker(symbol)
                    assert l_ask * h_bid > 0

                    if available * h_bid * 1.5 >= btc_quota:
                        logg(msgg(509, (currency, available)), exchange_obj.id, tabs)

                        take_profit = float(setup()['takeProfit'])
                        order_id, sell_price = _selling(
                            symbol, margin=take_profit, referential=l_ask)
                        cache = {}
                        wait(seconds=3)

                        assert sell_price > 0
                        logg(msgg(510, ('SELL', sell_price)), exchange_obj.id, tabs)
                        logg(msgg(511, order_id), exchange_obj.id, tabs)
    except AssertionError:
        logg(msgg(523, ('_reload()', symbol)), exchange_obj.id, tabs)
        debug(format_exc(), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id, tabs)


def _report():
    """
        Briefly reporting the current status of your assets.

    :return:
    """

    global nakamoto

    try:
        _update()
        # nakamoto == 'BTC/defaultFIAT'

        l_ask_naka, h_bid_naka = 0., 0.
        if '?' not in nakamoto:
            # there's any fiduciary on this site?
            l_ask_naka, h_bid_naka = _ticker(nakamoto)
            assert l_ask_naka * h_bid_naka > 0

        fee, holdings = 1 - cache['fee'] / 100, {}
        for currency, (available, on_orders) in cache['balance'].items():
            holdings[currency] = [0., 0.]
            subtotal = available + on_orders
            btc_fiat = nakamoto[:3] + '/' + currency

            if currency + '/' == nakamoto[:4]:
                # (avoid "currency == nakamoto[:3]" to not catch BTCX or so...)
                # currency: BTC
                btctotal = subtotal

            elif btc_fiat in cache['symbols_fiat']:
                if btc_fiat in cache['symbols_usd']:
                    # currency: USD, USDT, TUSD, USDC, PAX etc...
                    l_ask_fiat, h_bid_fiat = l_ask_naka, h_bid_naka
                    if not btc_fiat == nakamoto:
                        l_ask_fiat, h_bid_fiat = _ticker(btc_fiat)
                else:
                    # currency: EUR, RUR, JPY, BRL, GBP etc...
                    l_ask_fiat, h_bid_fiat = _ticker(btc_fiat)
                assert l_ask_fiat * h_bid_fiat > 0
                btctotal = subtotal / l_ask_fiat

            else:
                # currency: ETH, LTC, XMR etc... (ALTCOINS)
                l_ask_alt, h_bid_alt = _ticker(currency + '/' + nakamoto[:3])
                assert l_ask_alt * h_bid_alt > 0
                btctotal = subtotal * h_bid_alt
            holdings[currency] = [fee * btctotal, fee * btctotal * h_bid_naka]

        holdings_btc, holdings_fiat = list(zip(*holdings.values()))
        holdings = sum(holdings_btc), nakamoto[4:], sum(holdings_fiat)

        logg(category=exchange_obj.id)
        logg('REPORT: ', exchange_obj.id)
        logg(msgg(514, cache['balance']), exchange_obj.id)
        logg(msgg(515, holdings), exchange_obj.id)
        logg(msgg(516, sorted(cache['orders_full'])), exchange_obj.id)

        return holdings
    except AssertionError:
        logg(msgg(507, '_report()'), exchange_obj.id)
        debug(format_exc(), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id, tabs)


def _chase(broadway, max_spread=1.):
    """
        Just combining the sequence of BUY and SELL operations.

    :param broadway:
    :return:
    """

    global cache
    base, quote, btc = None, None, None
    chosen, profit_goal = None, 0.

    try:
        logg(category=exchange_obj.id)
        logg('CHASE: ', exchange_obj.id)

        tmp = {}
        for ss, ii in broadway.items():
            sd = _ticker(ss, with_spread=True)[2]  # spread
            if 0. < sd < max_spread:
                tmp[ss] = rnd(ii / sd, 8)
        tmp = sorted(tmp.items(), key=lambda k: k[1], reverse=True)
        logg(msgg(5171, tmp[:5]), exchange_obj.id)

        if not len(tmp):
            logg(msgg(5172), exchange_obj.id)
            return profit_goal
        else:
            chosen = tmp[0][0]

        sc = _split(chosen, with_btc=False)
        assert sc is not None
        base, quote = sc

        if not nakamoto[:4] in {s[:4] for s in dict(tmp)}:
            _update()
            assert quote in cache['balance']
            logg(msgg(5173, chosen), exchange_obj.id)

            if cache['balance'][quote][0] >= btc_quota:
                logg(msgg(518, chosen), exchange_obj.id)
                buy_order_id, buy_price = _buying(chosen, margin=0)
                cache = {}
                wait(seconds=30)

                assert buy_price > 0
                logg(msgg(510, ('BUY', buy_price)), exchange_obj.id, tabs)
                logg(msgg(511, buy_order_id), exchange_obj.id, tabs)

                _update()
                if buy_order_id not in cache['orders']:
                    # order was totally filled!

                    take_profit = float(setup()['takeProfit'])
                    sell_order_id, sell_price = _selling(
                        chosen, margin=take_profit, referential=buy_price)
                    cache = {}
                    wait(seconds=3)

                    assert sell_price > 0
                    logg(msgg(510, ('SELL', sell_price)), exchange_obj.id, tabs)
                    logg(msgg(511, sell_order_id), exchange_obj.id, tabs)

                    _update()
                    profit_goal = 100 * (sell_price / buy_price - 1) - 2 * cache['fee']
                elif base in cache['balance']:
                    # order was partially filled!

                    logg(msgg(5191, buy_order_id), exchange_obj.id, tabs)
                    cancel(exchange_obj, buy_order_id)
                    cache = {}

                    _update()
                    buy_order_id, buy_price = _buying(chosen, margin=-1,
                                                      check_balance=False)
                    cache = {}
                    wait(seconds=20)

                    assert buy_price > 0
                    logg(msgg(510, ('BUY', buy_price)), exchange_obj.id, tabs)
                    logg(msgg(511, buy_order_id), exchange_obj.id, tabs)
                else:
                    # order was totally NOT filled!

                    logg(msgg(5192, buy_order_id), exchange_obj.id, tabs)
                    cancel(exchange_obj, buy_order_id)
                    cache = {}

                logg(category=exchange_obj.id)
                logg(msgg(520, chosen), exchange_obj.id)
            else:
                logg(msgg(521), exchange_obj.id)
        else:
            logg(msgg(522), exchange_obj.id)
    except AssertionError:
        logg(msgg(507, '_chase()'), exchange_obj.id, tabs)

        _update()
        debug(msgg(516, sorted(cache['orders_full'])), exchange_obj.id, tabs)
        debug(msgg(524, (chosen, base, quote, btc)), exchange_obj.id, tabs)
        debug(format_exc(), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id, tabs)
    return profit_goal


def _buying(symbol, margin=1., check_balance=True):
    """
        This will try to BUY the given symbol, by the best market conditions.

    :param symbol:
    :param margin:
    :return:
    """

    buying = None

    try:
        logg(category=exchange_obj.id)
        logg('BUYING: ', exchange_obj.id, tabs)
        assert not symbol[:4] == nakamoto[:4]

        l_ask, h_bid = _ticker(symbol)
        assert l_ask * h_bid > 0

        if type(margin) == float:
            price = (1 - margin / 100) * l_ask  # margin in % points
        else:  # type(margin) == int:
            price = l_ask - (1E-8 * margin)  # margin in satoshies
        amount = btc_quota / price

        params = _rectify({'exchange_obj': exchange_obj, 'symbol': symbol,
                           'amount': amount, 'price': price, },
                          cache['balance'] if check_balance else None)
        
        logg(msgg(525, (l_ask, h_bid)), exchange_obj.id, tabs)
        logg(msgg(527, ('BUY', symbol, params)), exchange_obj.id, tabs)

        buying = fire(**params)
        assert buying is not None
    except AssertionError:
        logg(msgg(523, ('_buying()', symbol)), exchange_obj.id, tabs)
        debug(format_exc(), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id, tabs)
    return buying  # (order_id, price)


def _selling(symbol, margin=1., referential=None, fee_adjusted=True, check_balance=True):
    """
        This will try to SELL the given symbol, by the best market conditions.

    :param symbol:
    :param margin:
    :param referential:
    :param fee_adjusted:
    :return:
    """

    base, quote, btc = None, None, None
    selling = None

    try:
        logg(category=exchange_obj.id)
        logg('SELLING: ', exchange_obj.id, tabs)
        assert not symbol[:4] == nakamoto[:4]

        l_ask, h_bid = _ticker(symbol)
        assert l_ask * h_bid > 0

        if referential is None:
            referential = h_bid

        tmp = _split(symbol)
        assert tmp is not None
        (base, quote), btc = tmp

        if not setup()['runMode'].upper() in ['LIVE', 'TEST']:
            amount = -btc_quota / l_ask
        else:
            assert base in cache['balance']
            amount = -cache['balance'][base][0]
        assert -amount > 0

        fix = 1 + 2 * cache['fee'] / 100 if fee_adjusted else 1
        price = fix * referential
        if type(margin) == float:
            price *= (1 + margin / 100)  # margin in % points
        else:  # type(margin) == int:
            price += (1E-8 * margin)  # margin in satoshies

        params = _rectify({'exchange_obj': exchange_obj, 'symbol': symbol,
                           'amount': amount, 'price': price, },
                          cache['balance'] if check_balance else None)
        logg(msgg(526, referential), exchange_obj.id, tabs)
        logg(msgg(527, ('SELL', symbol, params)), exchange_obj.id, tabs)

        selling = fire(**params)
        assert selling is not None
    except AssertionError:
        logg(msgg(507, '_selling()'), exchange_obj.id, tabs)
        debug(msgg(524, (symbol, base, quote, btc)), exchange_obj.id, tabs)
        debug(format_exc(), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id, tabs)
    return selling  # (order_id, price)


def _rectify(order_params, balance_dict=None):
    """
        todo

    :param order_params:
    :return:
    """

    base, quote, btc = None, None, None

    try:
        params = order_params
        if not setup()['runMode'].upper() in ['LIVE', 'TEST']:
            params['amount'] = rnd(params['amount'], 8)
            params['price'] = rnd(params['price'], 8)
            return params
        max_amount, min_amount, amount_prec, max_price, min_price, \
            price_prec = cache['symbols'][params['symbol']]

        amount_mod = abs(params['amount'])
        amount_sig = params['amount'] / amount_mod
        m = 10 ** amount_prec
        amount_lot = (amount_sig + 1) / (2 * m)

        amount_trunc = int(m * amount_mod) / m
        if amount_trunc < amount_mod:
            amount_mod = amount_trunc + amount_lot

        if max_amount is not None:
            amount_mod = min(amount_mod, max_amount)

        if min_amount is not None:
            amount_mod = max(amount_mod, min_amount)
        params['amount'] = amount_sig * amount_mod

        price_mod = params['price']  # price is ALWAYS positive!
        m = 10 ** price_prec
        price_lot = (amount_sig - 1) / (-2 * m)

        price_trunc = int(m * price_mod) / m
        if price_trunc < price_mod:
            price_mod = price_trunc + price_lot

        if max_price is not None:
            price_mod = min(price_mod, max_price)

        if min_price is not None:
            price_mod = max(price_mod, min_price)
        params['price'] = price_mod

        if balance_dict is not None:
            tmp = _split(params['symbol'])
            assert tmp is not None
            (base, quote), btc = tmp

            if params['amount'] > 0:
                # BUYING
                assert quote in balance_dict
                assert balance_dict[quote][0] >= params['amount'] * params['price']
            else:
                # SELLING
                assert base in balance_dict
                assert balance_dict[base][0] >= -params['amount']
        return params
    except AssertionError:
        logg(msgg(507, '_rectify()'), exchange_obj.id, tabs)
        debug(msgg(524, (order_params['symbol'], base, quote, btc)),
              exchange_obj.id, tabs)
        debug(format_exc(), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id, tabs)


def _ticker(symbol, with_spread=False):
    """
        todo

    :param symbol:
    :return:
    """

    l_ask, h_bid, spread = 0., 0., 0.

    try:
        bb = book(exchange_obj, symbol, 1)
        assert bb is not None and len(bb)

        l_ask, h_bid = float(bb[0, 0]), float(bb[-1, 0])
        spread = 100 * (l_ask / h_bid - 1)
    except AssertionError:
        logg(msgg(507, '_ticker()'), exchange_obj.id, tabs)
        debug(msgg(528, (l_ask, h_bid)), exchange_obj.id, tabs)
        debug(format_exc(), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id, tabs)
    return (l_ask, h_bid, spread) if with_spread else (l_ask, h_bid)


def _split(symbol, with_btc=True):
    """
        todo

    :param symbol:
    :param with_btc:
    :return:
    """

    base, quote, btc = None, None, None

    try:
        sym_bol = to_ascii(symbol, lower_case=False, split_seq=True)
        base, quote = sym_bol[0], sym_bol[-1]
        btc = nakamoto[:3]
        assert btc in (base, quote)

    except AssertionError:
        logg(msgg(507, '_split()'), exchange_obj.id, tabs)
        debug(msgg(524, (symbol, base, quote, btc)), exchange_obj.id, tabs)
        debug(format_exc(), exchange_obj.id, tabs)
    except:
        logg(format_exc(), exchange_obj.id, tabs)

    if not with_btc:
        return base, quote
    return (base, quote), btc
