#!/usr/bin/python3
# -*- coding: iso-8859-1 -*
""" Python starter bot for the Crypto Trader games, from ex-Riddles.io """
__version__ = "1.0"

import sys
import math

def calculate_bollinger_bands(prices, period, confidence_level=0.85):
    if len(prices) < period:
        return None, None
    
    sma = sum(prices[-period:]) / period
    variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
    std_dev = math.sqrt(variance)
    
    z_score = math.sqrt(2) * std_dev
    upper_band = sma + z_score
    lower_band = sma - z_score
    
    return upper_band, lower_band

def calculate_rsi(prices, period=14):
    if len(prices) < period:
        return None
    
    gains = [0]
    losses = [0]
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gain = change
            loss = 0
        else:
            gain = 0
            loss = abs(change)
        
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_md(prices, period):
    if len(prices) < period:
        return None, None
    md_plus = sum([max(prices[i] - prices[i-1], 0) for i in range(len(prices) - period, len(prices))])
    md_minus = sum([max(prices[i-1] - prices[i], 0) for i in range(len(prices) -period, len(prices))])
    return md_plus, md_minus

def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    
    return ema

class Bot:
    def __init__(self):
        self.botState = BotState()

    def run(self):
        while True:
            reading = input()
            if len(reading) == 0:
                continue
            self.parse(reading)

    def parse(self, info: str):
        tmp = info.split(" ")
        if tmp[0] == "settings":
            self.botState.update_settings(tmp[1], tmp[2])
        if tmp[0] == "update":
            if tmp[1] == "game":
                self.botState.update_game(tmp[2], tmp[3])
        if tmp[0] == "action":
            print("je suis dans action", file=sys.stderr)
            self.perform_action()

    def perform_action(self):
        period = 10
        dollars = self.botState.stacks["USDT"]
        btc_balance = self.botState.stacks.get("BTC", 0)
        current_closing_price = self.botState.charts["USDT_BTC"].closes[-1]
        affordable = dollars / current_closing_price
        
        ema_7 = self.botState.charts["USDT_BTC"].calculate_ema(7)
        ema_14 = self.botState.charts["USDT_BTC"].calculate_ema(14)
        ema_21 = self.botState.charts["USDT_BTC"].calculate_ema(21)
        ema_50 = self.botState.charts["USDT_BTC"].calculate_ema(50)
        ema_200 = self.botState.charts["USDT_BTC"].calculate_ema(200)
        upper_band, lower_band = self.botState.charts["USDT_BTC"].calculate_bollinger_bands(30)
        rsi = self.botState.charts["USDT_BTC"].calculate_rsi(30)
        md_plus, md_minus = self.botState.charts["USDT_BTC"].calculate_md(14)
        
        if any(indicator is None for indicator in [ema_7, ema_14, ema_21, ema_50, ema_200, upper_band, lower_band, rsi, md_plus, md_minus]):
            print("no_moves", flush=True)
            return
        
        print(f'EMA 7: {ema_7}, EMA 14: {ema_14}, EMA 21: {ema_21}, EMA 50: {ema_50}, EMA 200: {ema_200}', file=sys.stderr)
        print(f'Upper Band: {upper_band}, Lower Band: {lower_band}', file=sys.stderr)
        print(f'RSI: {rsi}, MD+: {md_plus}, MD-: {md_minus}', file=sys.stderr)
        print(f'Dollars: {dollars}, BTC: {btc_balance}', file=sys.stderr)
        
        last_temp = self.botState.charts["USDT_BTC"].closes[-1]

        safety_margin = 0.1
        upper_band *= (1 - safety_margin)
        lower_band *= (1 + safety_margin)
        rsi_threshold_low = 35
        rsi_threshold_high = 35

        previous_prices = self.botState.charts["USDT_BTC"].closes[-period - 1:-1]
        is_downtrend = all(price > current_closing_price for price in previous_prices)

        if is_downtrend and last_temp < lower_band and rsi < rsi_threshold_low and dollars > 100 and last_temp < ema_21 and md_minus > md_plus:
            amount_to_buy = 0.05 * affordable
            self.botState.stacks["BTC"] += amount_to_buy
            self.botState.stacks["USDT"] -= amount_to_buy * current_closing_price
            print(f'buy USDT_BTC {amount_to_buy}', flush=True)
        elif last_temp > upper_band and rsi > rsi_threshold_high and btc_balance > 0 and last_temp > ema_21 and md_plus > md_minus:
            amount_to_sell = btc_balance
            self.botState.stacks["BTC"] -= amount_to_sell
            self.botState.stacks["USDT"] += amount_to_sell * current_closing_price
            print(f'sell USDT_BTC {amount_to_sell}', flush=True)
        else:
            print("no_moves", flush=True)

class Candle:
    def __init__(self, format, intel):
        tmp = intel.split(",")
        for (i, key) in enumerate(format):
            value = tmp[i]
            if key == "pair":
                self.pair = value
            if key == "date":
                self.date = int(value)
            if key == "high":
                self.high = float(value)
            if key == "low":
                self.low = float(value)
            if key == "open":
                self.open = float(value)
            if key == "close":
                self.close = float(value)
            if key == "volume":
                self.volume = float(value)

    def __repr__(self):
        return str(self.pair) + str(self.date) + str(self.close) + str(self.volume)

class Chart:
    def __init__(self):
        self.dates = []
        self.opens = []
        self.highs = []
        self.lows = []
        self.closes = []
        self.volumes = []
        self.indicators = {}

    def add_candle(self, candle: Candle):
        self.dates.append(candle.date)
        self.opens.append(candle.open)
        self.highs.append(candle.high)
        self.lows.append(candle.low)
        self.closes.append(candle.close)
        self.volumes.append(candle.volume)

    def calculate_moving_average(self, window_size):
        return moving_average(self.closes, window_size)
    
    def calculate_bollinger_bands(self, period):
        return calculate_bollinger_bands(self.closes, period)

    def calculate_rsi(self, period):
        return calculate_rsi(self.closes, period)
    
    def calculate_ema(self, period):
        return calculate_ema(self.closes, period)

    def calculate_md(self, period):
        return calculate_md(self.closes, period)
    
class BotState:
    def __init__(self):
        self.timeBank = 0
        self.maxTimeBank = 0
        self.timePerMove = 1
        self.candleInterval = 1
        self.candleFormat = []
        self.candlesTotal = 0
        self.candlesGiven = 0
        self.initialStack = 0
        self.transactionFee = 0.1
        self.date = 0
        self.stacks = dict()
        self.charts = dict()

    def update_chart(self, pair: str, new_candle_str: str):
        if not (pair in self.charts):
            self.charts[pair] = Chart()
        new_candle_obj = Candle(self.candleFormat, new_candle_str)
        self.charts[pair].add_candle(new_candle_obj)

    def update_stack(self, key: str, value: float):
        self.stacks[key] = value

    def update_settings(self, key: str, value: str):
        if key == "timebank":
            self.maxTimeBank = int(value)
            self.timeBank = int(value)
        if key == "time_per_move":
            self.timePerMove = int(value)
        if key == "candle_interval":
            self.candleInterval = int(value)
        if key == "candle_format":
            self.candleFormat = value.split(",")
        if key == "candles_total":
            self.candlesTotal = int(value)
        if key == "candles_given":
            self.candlesGiven = int(value)
        if key == "initial_stack":
            self.initialStack = int(value)
        if key == "transaction_fee_percent":
            self.transactionFee = float(value)

    def update_game(self, key: str, value: str):
        if key == "next_candles":
            new_candles = value.split(";")
            self.date = int(new_candles[0].split(",")[1])
            for candle_str in new_candles:
                candle_infos = candle_str.strip().split(",")
                self.update_chart(candle_infos[0], candle_str)
        if key == "stacks":
            new_stacks = value.split(",")
            for stack_str in new_stacks:
                stack_infos = stack_str.strip().split(":")
                self.update_stack(stack_infos[0], float(stack_infos[1]))

def moving_average(data, window_size):
    if len(data) < window_size:
        return None
    return sum(data[-window_size:]) / window_size

if __name__ == "__main__":
    mybot = Bot()
    mybot.run()
