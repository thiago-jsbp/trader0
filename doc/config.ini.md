# Kebnekaise

### The file 'bin/config.ini' commented:
    
    [DEFAULT]
    # Obviously, make sure you have some REAL money deposited at your favorite website.
    enabled = binance poloniex
    
    # 'test': just test the API plugins/wrappers.
    # 'play': simulate normal trades using play money.
    # 'live': make normal LIVE trades, with REAL money.
    runMode = live
    
    offline = 0                      | 0=False, 1=True (the "data" folder cannot be empty).
    debug = 0                        | 0=False, 1=True.
    verbose = 1                      | 0=False, 1=True.
    langFile = src/i18n/en.ini       | translations for the user interface (logs).
    
    dbUpdateMinutes = 7              | minimum time between two consecutive updates (rotates) in the database.
    dbLimitHours = 12                | maximum time an info will be left in the database.
    ohlcMinutes = 5                  | size in minutes to each candlesticks (core.olap._candlesticks()).    
    takeProfit = 3.                  | minimum intended profit (in %) on an investment.
    stopLoss = 2.                    | maximum acceptable loss. WARNING: Make sure you have "maxSpread" far below this.
    maturityHours = 8                | maximum wait time before canceling an order, in minutes.

You can change this settings WITHOUT stop the robot: It is always reading that file during each execution of the main loop, and dynamically changing its behavior.


[![donateLitecoin](https://img.shields.io/badge/Donate-LTC-red)](https://insight.litecore.io/address/LbtTecTv6QfrLWPsBykNumXMbD9YMxbu1R)
[![donateEthereum](https://img.shields.io/badge/Donate-ETH-green)](https://etherscan.io/address/0x2AB999d431823738ddA5Dc14c66A6FfB0f24C8aD)
[![donateDash](https://img.shields.io/badge/Donate-DASH-blue)](https://explorer.dash.org/address/XoingbjbZyee9CQzfu24v5FD7AStHwNYdz)
