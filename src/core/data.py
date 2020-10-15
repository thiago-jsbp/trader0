# -*- coding: utf-8 -*-

from .web import *
from os import listdir

db_suffix = '.dt'
exchange_obj = None


def rotate(exchange_id):
    """
        todo

    :param exchange_id:
    :return:
    """

    global exchange_obj
    pool = {}

    try:
        if halt():
            return pool

        t_delta = time()
        exchange_obj = exchange(exchange_id)
        logg('', exchange_obj.id)
        logg(msgg(301), exchange_obj.id)

        if int(setup()['offline']):
            pool = {fname.split('.')[1].replace('_', '/').upper(): fname
                    for fname in listdir('data')
                    if fname.startswith(exchange_obj.id) and '_' in fname}
            c = len(pool)
        else:
            pool, symbols_list = {}, sorted(symbols(exchange_obj))
            ls = len(symbols_list)
            logg(msgg(302, ls), exchange_obj.id)
            logg('', exchange_obj.id)

            db_limit = int(setup()['dbLimitHours'])
            c, last, partial = 0, 0, 0
            for ss in symbols_list:
                if not halt():
                    s_data, s_file = _merge(ss, t_delta, db_limit)
                    if len(s_data):
                        pool[ss] = s_file

                    partial = rnd(100 * c / ls, 1)
                    if not int(setup()['debug']) and partial - last > 20:
                        logg(msgg(303, partial), exchange_obj.id)
                        last = partial
                    c += 1
                else:
                    break

        t_delta = time() - t_delta
        av_delta = c if c == 0 else t_delta / c
        logg('', exchange_obj.id)
        logg(msgg(304, (secs2human(t_delta), av_delta)), exchange_obj.id)
        logg(msgg(305), exchange_obj.id)
    except:
        logg(format_exc(), exchange_obj.id)
    return pool


def _merge(symbol, current_time, db_limit=8, reset=False):
    """
        todo

    :param symbol:
    :param current_time:
    :param db_limit:
    :param reset:
    :return:
    """

    void = np.array([], dtype='float64').reshape(0, 3)
    tmp, db_file = {}, None

    try:
        db_file = exchange_obj.id + '.' + to_ascii(symbol)
        tmp = disk(db_file)

        if reset or not len(tmp):
            disk(db_file, {'hh': void, 'dl': db_limit})
            tmp = disk(db_file)
        elif db_limit > tmp['dl']:
            return _merge(symbol, current_time, db_limit, True)
        else:
            tmp['dl'] = db_limit

        h1 = tmp['hh']
        time_array = h1[:, 0]
        oldest = current_time - db_limit * secs_in_hour

        if len(h1):
            lag = float((current_time - max(time_array)) / secs_in_hour)
            h1 = h1[time_array > oldest]
            h2 = history(exchange_obj, symbol, current_time, lag)
        else:
            h1 = history(exchange_obj, symbol, current_time, db_limit)
            h2 = void

        tmp['hh'] = np.concatenate([h1, h2])
        disk(db_file, tmp)

        hh, lag = tmp['hh'], 0.
        if len(hh):
            tt = hh[:, 0]
            lag = rnd(float(max(tt) - min(tt)) / secs_in_hour, 3)

        params = symbol, len(h1), len(h2), lag
        debug(msgg(306, params), exchange_obj.id)
    except:
        logg(format_exc(), exchange_obj.id)
    return tmp, db_file
