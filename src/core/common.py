# -*- coding: utf-8 -*-

from collections.abc import Iterable
from configparser import ConfigParser
from multiprocessing import RLock
from os import mkdir, makedirs, mknod, remove, stat
from os.path import dirname, exists
from pickle import dump, load, HIGHEST_PROTOCOL
from time import gmtime, sleep, strftime, time
from traceback import format_exc

turning_off = False
verbose = None
secs_in_minute = 60
disk_errors_counter = 0


def logg(message='', category=None, tabs_before=0):
    """
        todo

    :param message:
    :param category:
    :param tabs_before:
    :return:
    """

    argv = locals()
    clock = strftime('%Y.%m.%d.UTC.%H.%M.%S', gmtime())
    global verbose

    if category is not None and len(category):
        category = '.' + category
    else:
        category = ''

    path = 'logs/' + clock[:10] + to_ascii(category)
    pattern = '({0}) ' + '\t' * tabs_before + '{1}\n'

    try:
        if int(time()) % secs_in_minute < 20 or verbose is None:
            verbose = int(setup()['verbose'])

        if verbose:
            with open(path + '.log', 'a') as fp:
                fp.write(pattern.format(clock, message))

    except KeyError:
        return _disk_except(logg, argv, format_exc())
    except:
        with open(path + '.err', 'a') as fp:
            fp.write(pattern.format(clock, format_exc()))


def debug(message='', category=None, tabs_before=0):
    """
        todo

    :param message:
    :param category:
    :param tabs_before:
    :return:
    """

    argv = locals()

    try:
        if int(setup()['debug']):
            logg(message, category, tabs_before)

    except KeyError:
        return _disk_except(debug, argv, format_exc())
    except:
        logg(format_exc())


def setup(section='DEFAULT', entry=None, value=None,
          config_path='bin/config.ini', delay=3):
    """
        todo

    :param section:
    :param entry:
    :param value:
    :param config_path:
    :return:
    """

    argv = locals()

    try:
        parser = ConfigParser(allow_no_value=True,
                              inline_comment_prefixes=('|',),
                              interpolation=None)
        parser.optionxform = str
        parser.read(config_path)

        if value is not None:
            parser.set(section, entry, value)
            with open(config_path, 'w') as fp:
                parser.write(fp)
        else:
            section = dict(parser)[section]
            return section if entry is None else section[entry]

    except KeyError:
        return _disk_except(setup, argv, format_exc())
    except:
        logg(format_exc())


def msgg(message_id, format_params=None):
    """
        todo

    :param message_id:
    :param format_params:
    :return:
    """

    argv = locals()

    try:
        msg = setup(entry=message_id, config_path=setup()['langFile'])
        if format_params is not None:
            if type(format_params) == tuple:
                return msg.format(*format_params)
            else:
                return msg.format(format_params)
        return msg

    except KeyError:
        return _disk_except(msgg, argv, format_exc())
    except:
        logg(format_exc())


def check_file(fqfn, exclude=False, is_directory=False):
    """
        Ensures the existence or removal of the dir/file whose path is given.

    :param fqfn:
    :param exclude:
    :param is_directory:
    :return:
    """

    try:
        d_perms, f_perms = 0o700, 0o600
        path = dirname(fqfn)

        if exclude:
            remove(fqfn)
        elif is_directory:
            mkdir(fqfn, mode=d_perms)
        else:
            if len(path):
                makedirs(path, mode=d_perms, exist_ok=True)

            if not exists(fqfn):
                mknod(fqfn, mode=f_perms)

            if stat(fqfn).st_size == 0:
                with open(fqfn, 'wb') as fp:
                    dump(dict(), fp, HIGHEST_PROTOCOL)
        return 0
    except:
        logg(format_exc())
        return 1


def unlock(data):
    """
        (UNSTABLE: DON'T USE!)
        todo: fix

        In order to avoid
            "TypeError: can't pickle _thread.RLock objects"
            (see: "src/core/test.py")

    :param data:
    :return:
    """

    try:
        td = type(data)

        if issubclass(td, type(RLock)):
            return str(td)
        elif isinstance(data, Iterable):
            return [unlock(n) for n in data]
        elif td == dict:
            return {k: unlock(v) for k, v in data.items()}
        else:
            return data
    except:
        logg(format_exc())


def disk(filename, data=None):
    """
        todo

    :param filename:
    :param data:
    :return:
    """

    try:
        filename = 'data/' + filename
        check_file(filename)

        if data is None:
            with open(filename, 'rb') as fp:
                data = load(fp)
                return data if type(data) == dict else {'data': data}
        else:
            with open(filename, 'wb') as fp:
                dump(data if type(data) == dict else {'data': data},
                     fp, HIGHEST_PROTOCOL)
    except EOFError:
        return {}
    except TypeError:
        # todo: fix
        #
        # In order to avoid
        #       "TypeError: can't pickle _thread.RLock objects"
        #       (see: "src/core/test.py")
        #
        # disk(filename.split('/')[1], unlock(data))
        logg(format_exc())
    except:
        logg(format_exc())


def halt(sending=False, removing=False):
    """
        READ for the HALT command, SEND it, or CLEAN the HALT file.

        IMPORTANT:
            In order to prevents the system from ignoring your halt commands, please
            don't forget to include this test in your (heavy) loops!

        Examples:
            while not halt():
                (some complex or slow code here, like
                downloads or some kind of fancy calculations...)

            for element in data:
                if not halt():
                    (some complex or slow code here, like
                    downloads or some kind of fancy calculations...)

    :param sending:
    :param removing:
    :return:
    """

    global turning_off

    try:
        halt_file = '.halt'
        if removing:
            check_file(halt_file, exclude=True)
        elif sending:
            check_file(halt_file)
        elif turning_off:
            return turning_off
        else:
            turning_off = exists(halt_file)
            return turning_off
    except:
        logg(format_exc())


def to_ascii(sequence, sep='_', lower_case=True, split_seq=False):
    """
        todo

    :param sequence:
    :param sep:
    :param lower_case:
    :param split_seq:
    :return:
    """

    try:
        sequence = ''.join(c if c.isalnum() or c == '.' else sep for c in sequence)

        while 2 * sep in sequence:
            sequence = sequence.replace(2 * sep, sep)
        sequence = sequence.lower() if lower_case else sequence.upper()

        return tuple(sequence.split(sep)) if split_seq else sequence
    except:
        logg(format_exc())


def secs2human(seconds):
    """
        Converts something like '141372986.576' into '4y 5m 23d 2h 34min 8.576s'.

    :param seconds:
    :return:
    """

    try:
        tmp = ''
        for k, v in [('y', 31556952), ('m', 2629746), ('d', 86400),
                     ('h', 3600), ('min', 60), ]:
            if seconds > v:
                n = int(seconds / v)
                seconds -= n * v
                tmp += '{}{} '.format(n, k)

        ss = round(seconds, 3)
        if ss > 0:
            return tmp + '{}s'.format(ss)
        return tmp[:-1]
    except:
        logg(format_exc())


def rnd(number, ndigits=3):
    """
        This was created just to solve some ridiculous "-0.0" problems...
        https://docs.python.org/3.7/tutorial/floatingpoint.html#tut-fp-issues

    :param number:
    :param ndigits:
    :return:
    """

    try:
        n = round(float(number), int(ndigits))

        return abs(n) if n == 0 else n
    except:
        logg(format_exc())


def wait(minutes=None, seconds=1 / 3):
    """
        SECURITY DELAY: in order to NOT get your IP banned!

    :param minutes:
    :param seconds:
    :return:
    """

    try:
        if minutes is not None:
            tt = minutes * secs_in_minute
        else:
            tt = seconds
        c = 1000
        tt /= c

        for n in range(c):
            if not halt():
                sleep(tt)
            else:
                break
    except:
        logg(format_exc())


def _disk_except(func_obj, func_params, errmsg, delay=3):
    """
        todo

    :param func_obj:
    :param func_params:
    :param errmsg:
    :param delay:
    :return:
    """

    global disk_errors_counter

    try:
        if disk_errors_counter < 3:
            debug(msgg(201, delay))
            wait(seconds=delay)
            disk_errors_counter += 1
            return func_obj(**func_params)
        else:
            disk_errors_counter = 0
            logg(errmsg)
    except:
        logg(format_exc())
