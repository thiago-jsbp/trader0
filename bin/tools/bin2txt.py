#!/usr/bin/env python3
# -*- coding: iso-8859-1 -*-

from collections.abc import Iterable
from os import listdir
from os.path import basename
from pickle import load, UnpicklingError
from traceback import format_exc
import numpy as np
import pandas as pd


def logg(msg, filename='error.txt'):
    """
        todo

    :param msg:
    :param filename:
    :return:
    """

    with open(filename, 'w') as fp:
        fp.write(msg)


def obj2str(data):
    """
        todo

    :param data:
    :return:
    """

    try:
        td = type(data)

        if td in [np.ndarray, pd.Series, pd.DataFrame]:
            data = np.array(data).tolist()
        elif td == dict:
            data = sorted({k: obj2str(v)
                           for k, v in data.items()}.items())
        elif isinstance(data, Iterable):
            data = [obj2str(n) for n in data]
        return str(data)
    except:
        logg(format_exc())


def disc(filename, data=None):
    """
        todo

    :param filename:
    :param data:
    :return:
    """

    try:
        if data is None:
            with open(filename, 'rb') as fp:
                return load(fp)
        else:
            with open(filename, 'w') as fp:
                fp.write(obj2str(data))

    except UnpicklingError:  # text file
        pass
    except:
        logg(format_exc(), filename + '.err')


for input_file in set(listdir('.')) - {basename(__file__)}:
    tmp = disc(input_file)
    if tmp is not None:
        disc(input_file + '.txt', tmp)
