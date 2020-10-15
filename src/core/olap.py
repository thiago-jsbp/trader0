# -*- coding: utf-8 -*-

from .web import *
from math import log
from ta.momentum import *
from ta.trend import *
from ta.volatility import *
from ta.volume import *
import pandas as pd

db_suffix = '.oa'
exchange_obj = None
freq = []


def broadway(exchange_id, symbols_dict):
    """
        https://www.pokernews.com/pokerterms/broadway.htm

    :param exchange_id:
    :param symbols_dict:
    :return:
    """

    global exchange_obj, freq
    bw = {}

    try:
        if halt():
            return bw

        t_delta = time()
        exchange_obj = exchange(exchange_id)
        logg(category=exchange_obj.id)

        logg(msgg(401), exchange_obj.id)
        logg(msgg(402), exchange_obj.id)
        logg(category=exchange_obj.id)

        tmp = {}
        for s_name, s_file in sorted(symbols_dict.items()):
            if not halt():
                bull, bear = _index(s_name, disk(s_file))
                if bull > 0:
                    tmp[s_name] = bull
                elif bear > 0:
                    tmp[s_name] = -bear
                else:
                    tmp[s_name] = 0.
            else:
                return bw

        tz = 'UTC'
        tmp = pd.DataFrame(tmp, index=[pd.Timestamp(t_delta * 1E9, tz=tz)])

        avg_freq = rnd(sum(freq) / len(freq), 3)
        freq = []
        debug('avg_freq = ' + str(avg_freq), exchange_obj.id)

        db_file = exchange_obj.id + db_suffix
        db_key, cache = 'triggers', disk(db_file)
        if db_key in cache and type(cache[db_key]) == pd.DataFrame:
            tmp = pd.concat([cache[db_key], tmp])

        db_limit = t_delta - int(setup()['dbLimitHours']) * secs_in_hour
        pd_oldest = pd.Timestamp(1E9 * db_limit, tz=tz)
        if not int(setup()['offline']):
            tmp = tmp[tmp.index > pd_oldest]
        disk(db_file, tmp)

        bw = {str(k): float(v) for k, v in dict(tmp[-1:]).items()}
        bw = {k: v for k, v in bw.items() if v != 0}

        s_bw = str(sorted(bw.items(), key=lambda k: k[1], reverse=True))
        logg(category=exchange_obj.id)
        logg(msgg(403, s_bw), exchange_obj.id)

        t_delta, ls = time() - t_delta, len(symbols_dict)
        av_delta = ls if ls == 0 else t_delta / ls
        logg(msgg(304, (secs2human(t_delta), av_delta)), exchange_obj.id)
        logg(msgg(404), exchange_obj.id)
    except:
        logg(format_exc(), exchange_obj.id)
    return bw


def _index(symbol_id, history_data):
    """
        Momentum, Trend, Volatility and Volume, combined.

    :param symbol_id:
    :param history_data:
    :return:
    """

    global freq
    ii = {'IX': (0., 0.)}

    try:
        assert type(history_data) == dict and 'hh' in history_data
        frequency, hh = 0., history_data['hh']

        tt = hh[:, 0]
        if len(set(tt)) > 1:
            dh = np.diff(tt)
            frequency = secs_in_hour / sum(dh) * (len(dh) + 1)
        freq.append(frequency)

        history_df = _candlesticks(hh, int(setup()['ohlcMinutes']) * secs_in_minute)
        ii = {k: list(n + abs(n) for n in v)
              for k, v in {'MM': _momentum(history_df),
                           'TR': _trend(history_df),
                           'VA': _volatility(history_df),
                           'VO': _volume(history_df), }.items()}
        ii['IX'] = list(float(np.prod(triggers))
                        for triggers in list(zip(*ii.values())))
        ii['FF'] = frequency
        debug(symbol_id + ': ' + str(sorted(ii.items())), exchange_obj.id)

        assert len(history_df)
        assert min(history_df['Low']) > 1E-6
        if ii['IX'][0] > 0:
            assert ii['FF'] > 120

    except AssertionError:
        ii['IX'] = 0., 0.
    except:
        logg(format_exc(), exchange_obj.id)
    return ii['IX']


def _candlesticks(history_array, time_frame=180):
    """
         todo

    :param history_array:
    :param time_frame:
    :return:
    """

    void = np.array([], dtype='float64').reshape(0, 6)
    cols = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']

    try:
        assert len(history_array)
        assert secs_in_minute <= time_frame <= secs_in_hour

        time_array = history_array[:, 0]
        inf, sup = int(min(time_array)), int(max(time_array)) + time_frame
        tmp1 = {int(t - t % time_frame): [] for t in range(inf, sup, time_frame)}

        for epoch, amount, price in history_array:
            tmp1[int(epoch - epoch % time_frame)] += [(
                abs(amount) * price, price,)]

        ohlc, tmp2 = None, []
        for timestamp, trades_list in sorted(tmp1.items()):
            if len(trades_list):
                notionals, prices = list(zip(*trades_list))
                ohlc = prices[0], max(prices), min(prices), prices[-1]
            else:
                notionals = [0.]
                ohlc = 4 * (ohlc[-1],)
            tmp2 += [(timestamp,) + ohlc + (sum(notionals),)]
        return pd.DataFrame(np.array(tmp2)[1:-1, :], columns=cols)

    except AssertionError:
        pass
    except:
        logg(format_exc(), exchange_obj.id)
    return pd.DataFrame(void, columns=cols)


def _momentum(history_df, threshold=30.):
    """
        https://www.investopedia.com/terms/m/momentum.asp

    :param history_df:
    :param threshold:
    :return:
    """

    buy_trigger, sell_trigger = 0., 0.

    try:
        assert len(history_df)

        # hh = history_df['High']
        # ll = history_df['Low']
        cc = history_df['Close']

        w_rsi = _wrap(rsi, (cc,))
        # w_wr = _wrap(wr, (hh, ll, cc))

        threshold_up = 100. - threshold
        if w_rsi is not None:
            buy_trigger = threshold - w_rsi
            sell_trigger = w_rsi - threshold_up

    except AssertionError:
        pass
    except:
        logg(format_exc(), exchange_obj.id)
    return buy_trigger, sell_trigger


def _trend(history_df, threshold=26.5):
    """
        https://www.investopedia.com/terms/t/trend.asp

    :param history_df:
    :param threshold:
    :return:
    """

    buy_trigger, sell_trigger = 0., 0.

    try:
        assert len(history_df)

        hh = history_df['High']
        ll = history_df['Low']
        # cc = history_df['Close']

        # w_vip = _wrap(vortex_indicator_pos, (hh, ll, cc))
        # w_vin = _wrap(vortex_indicator_neg, (hh, ll, cc))
        w_mi = _wrap(mass_index, (hh, ll))

        if w_mi is not None:
            buy_trigger = w_mi - threshold
            sell_trigger = -buy_trigger

    except AssertionError:
        pass
    except:
        logg(format_exc(), exchange_obj.id)
    return buy_trigger, sell_trigger


def _volatility(history_df, threshold=1):
    """
        https://www.investopedia.com/terms/v/volatility.asp

    :param history_df:
    :param threshold:
    :return:
    """

    buy_trigger, sell_trigger = 0, 0

    try:
        assert len(history_df)

        hh = history_df['High']
        ll = history_df['Low']
        cc = history_df['Close']

        w_bol_l = _wrap(bollinger_lband_indicator, (cc,))
        w_kel_l = _wrap(keltner_channel_lband_indicator, (hh, ll, cc))
        w_don_l = _wrap(donchian_channel_lband_indicator, (cc,))

        buy_bands = w_bol_l, w_kel_l, w_don_l
        if None not in buy_bands:
            buy_trigger = sum(buy_bands) - threshold

        w_bol_h = _wrap(bollinger_hband_indicator, (cc,))
        w_kel_h = _wrap(keltner_channel_hband_indicator, (hh, ll, cc))
        w_don_h = _wrap(donchian_channel_hband_indicator, (cc,))

        sell_bands = w_bol_h, w_kel_h, w_don_h
        if None not in sell_bands:
            sell_trigger = sum(sell_bands) - threshold

    except AssertionError:
        pass
    except:
        logg(format_exc(), exchange_obj.id)
    return buy_trigger, sell_trigger


def _volume(history_df, threshold=0.):
    """
        https://www.investopedia.com/terms/v/volume.asp

    :param history_df:
    :param threshold:
    :return:
    """

    buy_trigger, sell_trigger = 0., 0.

    try:
        assert len(history_df)

        hh = history_df['High']
        ll = history_df['Low']
        cc = history_df['Close']
        vv = history_df['Volume']

        w_cmf = _wrap(chaikin_money_flow, (hh, ll, cc, vv))
        # w_nvi = _wrap(negative_volume_index, (cc, vv))

        if w_cmf is not None:
            buy_trigger = threshold - w_cmf
            sell_trigger = -buy_trigger

    except AssertionError:
        pass
    except:
        logg(format_exc(), exchange_obj.id)
    return buy_trigger, sell_trigger


def _wrap(func, params):
    """
        todo

    :param func:
    :param params:
    :return:
    """

    try:
        x = func(*params)
        x = x[~np.isnan(x) & ~np.isinf(x)]

        return float(x.tolist()[-1])
    except:
        return
