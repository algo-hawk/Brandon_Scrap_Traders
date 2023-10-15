'''
Trading System Part 1: Liquidity Provider
- The goal is to mimic an exchange that will send price updates to the trading system
- We will call the price update function to take the order update and format it, then send to trading strategy

Purpose: The purpose of the "Liquidity Provider" is to pull and format all of the data I need, and send the
 price updates to the trading strategy (lp_2_ts gateway). It has two modes:
1. Simulation: The simulation mode aims to simulate real time trading. Basically it reads line by line of an excel
 file and handles the price update
2. Real time: Pulls from the kraken exchange

Misc:
You will only call two functions:
1. update_data(): This updates optimization (training data), simulation (testing data), and real time (in both real time
 and simulation mode it writes the real time data so we can plot real time and stuff).
    NOTE: STREAMLIT PROMPTS ARE CURRENTLY BUILT IN, IF YOU DON'T WANT TO USE IN STREAMLIT CHANGE TO USER INPUTS
2. pull_ticker_info(): You will put this in a while loop. This is how it continuously pulls data, either in simulation
    mode or in real time from kraken exchange


IMPORTANT NOTES:
- BOTH REAL TIME AND SIMULATION FEED THE PRICE UPDATES TO THE TRADING STRATEGY THE SAME WAY FOR CONSISTENCY
    Format: price_update = {
                            'Datetime': (Datetime object) %m/%d/%y %H:%M
                            'price': (float) current close price
                                }
'''
from random import randrange
from random import sample, seed
from collections import deque
import os
import csv
from datetime import datetime
import threading
import time
import krakenex
from pykrakenapi import KrakenAPI
import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta


class LiquidityProvider:
    def __init__(self, lp_2_ts=None, mode='Simulation'):
        """
        SETUP:
        - Initialize Kraken API
        - Determine Mode: Simulation or Real Time
        - Initialize Data
        """
        self.lp_2_ts = lp_2_ts                   # Gateway from liquidity provider to trading strategy
        self.api = KrakenAPI(krakenex.API())     # Initialize the kraken api (API KEYS WILL GO HERE)
        self.ticker = None                       # Initialize the crypto to use (WILL CHANGE WITH WEBSITE)
        self.simulation_data = pd.DataFrame()    # This is where I will store the pandas df of the simulation data
        self.optimization_data = pd.DataFrame()  # This is where I will store the optimization data
        self.simulation_counter = 0              # Simulation Counter to keep track of what day ur on in simulation (YOU ARE PROMPTED IN WEBSITE)
        self.mode = mode                         # Initialize the mode (simulation or real time)



    #Updating data with what we will use
    def update_data(self):
        """
        - Call this function everytime you want to update data. WILL NOT INITIALIZE
        """
        self._update_optimization_data()
        self._update_simulation_data()
        self._update_realtime_data()

    def _update_optimization_data(self):
        """
        - Low Level function that checks for optimization data and creates it if it doesn't find it
        - Added streamlit input to ask at initialization to ask for the timeframes you want for data and the ticker
        """
        folder = 'Optimization_Data'
        if not os.path.exists(folder):
            print(f'{folder} Folder Not Found... Creating Now')
            os.makedirs(folder)
        file_path = os.path.join(folder, f'{self.ticker}_Optimization_Data.csv')
        print(f'{self.ticker}_Optimization_Data.csv File  Found... Updating it now')
        '''
        if st.button("Click to Update Optimization Data"):
            # Sidebar to input start and end dates
            st.header("Enter Optimization Date Range")
            # Calculate the date ranges (1.5 years ago to 6 months ago)
            one_and_half_years_ago = datetime.date.today() - relativedelta(years=1, months=6)
            six_months_ago = datetime.date.today() - relativedelta(months=6)
            begin_date = st.date_input("Start Date", one_and_half_years_ago)
            end_date = st.date_input("End Date", six_months_ago)
            if start_date > end_date:
                st.error("Start date should be before end date")
        
            else:
        '''
        one_year_ago = datetime.date.today() - relativedelta(years=1)   #Take these out when you fix UX just initializing for now
        six_months_ago = datetime.date.today() - relativedelta(months=6)
        formatted_ticker = self.ticker[:-3] + '-' + self.ticker[-3:]
        self.optimization_data = yf.download(formatted_ticker, start=one_year_ago, end=six_months_ago)
        self.optimization_data.to_csv(file_path)

    def _update_simulation_data(self):
        """
        - Low Level function that prompts user for data selection and downloads/saves the dataframe
        """
        folder = 'Simulation_Data'
        if not os.path.exists(folder):  # Checks if Simulation Data folder exists, if not create it
            print(f'{folder} Folder Not Found... Creating Now')
            os.makedirs(folder)
        file_path = os.path.join(folder, f'{self.ticker}_Simulation_Data.csv')  # filepath always stored in local variable
        print(f'{self.ticker}_Simulation_Data.csv File Not Found... Updating it now')
        '''
        if st.button("Click to Update Simulation Data"):
            # Header to input start and end dates
            st.header("Enter Simulation Date Range")
            # Calculate the date ranges (1.5 years ago to 6 months ago)
            six_months_ago = datetime.date.today() - relativedelta(months=6)
            begin_date = st.date_input("Start Date", six_months_ago)
            end_date = st.date_input("End Date", datetime.date.today())
            if start_date > end_date:
                st.error("Start date should be before end date")
            else:
        '''
        six_months_ago = datetime.date.today() - relativedelta(months=6)
        formatted_ticker = self.ticker[:-3] + '-' + self.ticker[-3:]
        self.simulation_data = yf.download(formatted_ticker, start=six_months_ago, end=datetime.date.today())
        self.simulation_data.to_csv(file_path)
    def _update_realtime_data(self):
        '''
        This function is called in init. This is so that everytime we boot up the program, it will search for the file
        where we will store the price data, and if it is there. It will clear it. For good practice for simulations we
        will still write the data
        '''
        folder = "RealTime_StockData"
        csv_file = f"{self.ticker}_RealTime_Price_Data.csv"
        if not os.path.exists(folder):
            os.makedirs(folder)
        file_path = os.path.join(folder, csv_file)
        if os.path.exists(file_path):
            os.remove(file_path)  # Delete the file



    #Pulling Price updates from either simulation data or real time
    def pull_ticker_info(self):
        '''
        If in 'Real Time' Mode, pull from exchange every 10 second (possibility of intraday handled)
        If in 'Simulation', iterate through close and date of csv file. if not created, download most recent year
            from yahoo finance
        '''
        if self.mode == 'Real Time':
            try:
                ticker_info = self.api.get_ticker_information(self.ticker)  #API LIBRARY FUNCTION CALL SEE PYKRAKENAPI DOCS
                current_datetime = datetime.now()
                formatted_datetime = current_datetime.strftime('%m/%d/%y %H:%M')
                price_update = {
                    'Datetime': formatted_datetime,
                    'price': ticker_info.iloc[-1]['c'][0]
                }
                print('--------------------------------------------------------')
                self.simulation_counter += 1    # Update Simulation Counter
                print('LP1 Event: Price Pulled From Kraken API: ', price_update)
                self._update_simultaneously(price_update)
                print('LP1 Event: Price Update Sent to Trading Strategy')
                print('--------------------------------------------------------')
            except Exception as e:
                print('Brandon Note: The following Error May be a kraken API error ')
                print(f"Error occurred while pulling data: {e}")

        if self.mode == 'Simulation':
            price_update = self._pull_simulation_priceupdate(self.simulation_data)
            self._update_simultaneously(price_update)
            print('LP1 Simulation Event: Sending Price Update to Trading Strategy: ', price_update)
    def _pull_simulation_priceupdate(self, data):
        if self.simulation_counter < len(data):
            print('--------------------------------------------------------')
            print(f'Simulation Day {self.simulation_counter} / {len(data)}')
            print('--------------------------------------------------------')
            print(data)
            row = data.iloc[self.simulation_counter]
            date = row.name.strftime('%m/%d/%y %H:%M')
            close = row['Close']
            price_update = {
                'Datetime': date,
                'price': close
            }
            self.simulation_counter += 1
        else:
            return None

        return price_update



    #Multithreaded Pieces
    def _update_trading_system_price(self, price_update):
        self.lp_2_ts.append(price_update)
    def _update_price_csv(self, price_update):
        folder = "RealTime_StockData"
        csv_file = f"{self.ticker}_RealTime_Price_Data.csv"
        file_path = os.path.join(folder, csv_file)
        if os.path.exists(file_path):
            with open(file_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([price_update['Datetime'], price_update['price']])
        else:
            with open(file_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Datetime', 'price'])
                writer.writerow([price_update['Datetime'], price_update['price']]) 
    def _update_simultaneously(self, price_update):
        thread1 = threading.Thread(target=self._update_trading_system_price, args=(price_update,))
        thread2 = threading.Thread(target=self._update_price_csv, args=(price_update,))
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()




#===========================================================================================================================
#UTILS AND MISC FUNCTIONS THAT DONT DIRECTLY RELATE TO THE TRADING SYSTEM





































