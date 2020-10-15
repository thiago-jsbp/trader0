# -*- coding: utf-8 -*-

from .core.data import *
from .core.olap import *
from .core.oltp import *
from .core.test import *
from multiprocessing import Process


def operation(market):
    """
        todo

    :param market:
    :return:
    """

    try:
        logg(spacer, market)

        while market in setup()['enabled'].split() and not halt():
            t_delta = time()
            run_mode = setup()['runMode'].upper()

            debug('', market)
            debug('[run_mode = {}]'.format(run_mode), market)

            if run_mode == 'TEST':
                public_api(market, t_delta)
                private_api(market, t_delta)
            else:
                probe(market, broadway(market, rotate(market)))
            t_delta = time() - t_delta

            delay = int(setup()['dbUpdateMinutes']) * 60
            if delay > t_delta:
                w = delay - t_delta

                debug('', market)
                debug(msgg(103, secs2human(w)), market)
                wait(seconds=w)
        logg('', market)
        logg(spacer, market)

    except AttributeError:
        logg(format_exc(), market)
        operation(market)
    except:
        logg(format_exc(), market)


def control(t_wait=3):
    """
        Start a new process for each enabled plugin.

    :param t_wait:
    :return:
    """

    try:
        logg(msgg(101))
        bots = {Process(target=operation, args=(exchange_name,))
                for exchange_name in setup()['enabled'].split()}

        for b in bots:
            b.start()

        while not halt():
            wait()

        for b in bots:
            b.join(t_wait)
        wait(seconds=t_wait)

        for b in bots:
            b.terminate()
        halt(removing=True)

        logg(msgg(102))
        logg()
    except:
        logg(format_exc())


if __name__ == '__main__':
    spacer = '$$$$$ $$$$$ $$$$$ $$$$$ $$$$$ $$$$$ $$$$$'
    control()
