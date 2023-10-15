import warnings
from matplotlib.dates import AutoDateLocator, AutoDateFormatter
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np
import pandas as pd
import statistics as stats
import math as math
from IPython.display import display
from matplotlib import pyplot as plt
import yfinance as yf
from statistics import stdev
sns.set()

'''
Brandons notes:

- This could work. Add the mean reversion support and resistance and add that in the trading condition. The program should then trade well.


'''

def apo_nulladjusted(data, NUM_PERIODS_FAST=12, NUM_PERIODS_SLOW=26, SMA_NUM_PERIODS=15, APO_BUY_VALUE=-0.1, APO_SELL_VALUE=0.1, trading_cash=5000, MIN_NUM_DAYS_SINCE_LAST_TRADE=7, show_charts=False, show_special=False):

    # Downloading Data
    data = data

    # Variables that define/control strategy trading behavior and profit/loss management (these will stay the same in every program)
    orders = []  # +1 buy, -1 sell, 0 no action
    positions = []  # tracking positions, + long, - short, 0 no position
    pnls = []  # Total pnls, pnls already locked in and open ones
    portfolio_value_log = [] # Keeping track of portfolio value
    trading_cash_log = [] # Keeping track of available cash to trade with
    price_history = [] # Price history for SMA calculation

    #Initializing Variables (these will stay the same for each program)
    last_buy_price = 0  # Prevents over-trading at/around the same price
    last_sell_price = 0 # ^
    position = 0  # Current position of trading strategy
    buy_sum_price_qty = 0  # Cost of summation of every buy order (price * amt)
    buy_sum_qty = 0  # Summation of buy trades since last time being flat
    sell_sum_price_qty = 0
    sell_sum_qty = 0
    open_pnl = 0  # Open/Unrealized PnL
    closed_pnl = 0  # Closed/Realized Pnl
    position_holding_time = 0 #Current number of days with an open position
    MIN_PRICE_MOVE_FROM_LAST_TRADE = data['Close'][0] * .05 # minimum price movement before next trade to prevent overtrading
    NUM_SHARES_PER_TRADE = 10 #Number of shares to trade with
    MIN_NUM_DAYS_SINCE_LAST_TRADE = MIN_NUM_DAYS_SINCE_LAST_TRADE
    trading_cash = float(trading_cash) #what is available to trade with:
    initial_cash = trading_cash  # trading cash changes so this value stores initial value


    #The next chunk up until the buy/sell loop will be the statistical calculations/variable holders that will change with every trading algo

    # Storing variables for statistical calculations
    ema_fast_values = []
    ema_slow_values = []
    apo_values = []  # apo values
    std_deviations = []  # stdev values
    APO_VALUE_FOR_BUY_ENTRY = APO_BUY_VALUE
    APO_VALUE_FOR_SELL_ENTRY = APO_SELL_VALUE


    # Perform fast and slow EMA calculations:
    NUM_PERIODS_FAST = NUM_PERIODS_FAST
    K_FAST = 2 / (NUM_PERIODS_FAST + 1)
    ema_fast = 0  # initial value

    NUM_PERIODS_SLOW = NUM_PERIODS_SLOW
    K_SLOW = 2 / (NUM_PERIODS_SLOW + 1)
    ema_slow = 0  # initial value

    close = data['Close']
    for close_price in close:
        price_history.append(close_price)

        # Only hold history of how many days used
        if len(price_history) > SMA_NUM_PERIODS:
            del (price_history[0])

        # Variance and Standard Deviation Calculations
        sma = stats.mean(price_history)
        variance = 0
        for hist_price in price_history:
            variance = variance + ((hist_price - sma) ** 2)

        stdev = math.sqrt(variance / len(price_history))
        std_deviations.append(stdev)

        # Updating fast and slow EMA
        if (ema_fast == 0):  #:First observation
            ema_fast = close_price
            ema_slow = close_price
        else:
            ema_fast = (close_price - ema_fast) * K_FAST + ema_fast
            ema_slow = (close_price - ema_slow) * K_SLOW + ema_fast

        ema_fast_values.append(ema_fast)
        ema_slow_values.append(ema_slow)

        apo = ema_fast - ema_slow
        apo_values.append(apo)

        # Logic for Sell Trades
        if position > 0 and ((apo > APO_VALUE_FOR_SELL_ENTRY and abs(close_price - last_sell_price) > MIN_PRICE_MOVE_FROM_LAST_TRADE)) \
                and position_holding_time > MIN_NUM_DAYS_SINCE_LAST_TRADE:
            orders.append(-1)
            last_sell_price = close_price
            position -= NUM_SHARES_PER_TRADE
            sell_sum_price_qty += (close_price * NUM_SHARES_PER_TRADE)
            sell_sum_qty += NUM_SHARES_PER_TRADE
            trading_cash += (close_price * NUM_SHARES_PER_TRADE) #Update the Trading Cash Variable
            #print('Sell ', NUM_SHARES_PER_TRADE, ' @ ', close_price, 'Position: ', position)
            position_holding_time = 0

        # Logic for Buy Trades
        elif ((apo < APO_VALUE_FOR_BUY_ENTRY and abs(
                close_price - last_buy_price) > MIN_PRICE_MOVE_FROM_LAST_TRADE )) and position_holding_time > MIN_NUM_DAYS_SINCE_LAST_TRADE:
            orders.append(1)
            last_buy_price = close_price
            position += NUM_SHARES_PER_TRADE
            buy_sum_price_qty += (close_price * NUM_SHARES_PER_TRADE)
            buy_sum_qty += NUM_SHARES_PER_TRADE
            trading_cash -= (close_price * NUM_SHARES_PER_TRADE) #Update the Trading Cash Variable
            #print('Buy ', NUM_SHARES_PER_TRADE, ' @ ', close_price, 'Position: ', position)
            position_holding_time = 0

        # Logic for if no trade happens:
        else:
            orders.append(0)

        # Append Position to log
        positions.append(position)

        ###Profit and Loss (Within Iteration)###
        if position > 0:
            if sell_sum_qty > 0:
                open_pnl = abs(sell_sum_qty) * (sell_sum_price_qty / sell_sum_qty - buy_sum_price_qty / buy_sum_qty)
            open_pnl += abs(sell_sum_qty - position) * (close_price - buy_sum_price_qty / buy_sum_qty)

        elif position < 0:
            if buy_sum_qty > 0:
                open_pnl = abs(buy_sum_qty) * (sell_sum_price_qty / sell_sum_qty - buy_sum_price_qty / buy_sum_qty)
            open_pnl += abs(buy_sum_qty - position) * (sell_sum_price_qty / sell_sum_qty - close_price)

        # This is where you update closed_pnl i.e. when its flat
        else:
            closed_pnl += (sell_sum_price_qty - buy_sum_price_qty)
            buy_sum_price_qty = 0
            buy_sum_qty = 0
            sell_sum_price_qty = 0
            sell_sum_qty = 0
            last_buy_price = 0
            last_sell_price = 0

        # Print Profit and Loss:
        #print('Open Profit and Loss: ', open_pnl, 'Closed Profit and Loss: ', closed_pnl)
        #print('Trading Cash', trading_cash)
        pnls.append(closed_pnl + open_pnl)
        trading_cash_log.append(trading_cash)

        # Calculating Portfolio Value
       # portfolio_value_log.append(trading_cash + (open_pnl))
        position_holding_time += 1
        portfolio_value_log.append(trading_cash + (close_price * position))

    #In case you are still holding stock at the end. Add its value to your trading cash:
    if position > 0:
        trading_cash += close_price * position
        trading_cash_log[-1] = trading_cash #Changing the last one so so you can call it as the final portfolio value

    data = data.assign(ClosePrice=pd.Series(close, index=data.index))
    data = data.assign(Fast10DayEMA=pd.Series(ema_fast_values, index=data.index))
    data = data.assign(Slow40DayEMA=pd.Series(ema_slow_values, index=data.index))
    data = data.assign(APO=pd.Series(apo_values, index=data.index))
    data = data.assign(Trades=pd.Series(orders, index=data.index))
    data = data.assign(Position=pd.Series(positions, index=data.index))
    data = data.assign(PNL=pd.Series(pnls, index=data.index))
    data = data.assign(TradingCash=pd.Series(trading_cash_log, index=data.index))
    data = data.assign(PortfolioValue=pd.Series(portfolio_value_log, index=data.index))

    final_day_percentage = round(float((trading_cash_log[-1] - initial_cash) / initial_cash * 100), 2)
    final_day_total = trading_cash
    threshold_value = round(float((close[-1] - close[0]) / close[0] * 100), 2)
    print('Final Portfolio Value: ', final_day_total)
    print('Final Percent Return: {} %'.format(final_day_percentage))
    print('Threshold % (Just buying and holding): {} %'.format(threshold_value))

    if show_special:
        # Creating figure and axis

        fig = plt.figure(facecolor='#07000d', figsize=(12, 12))
        plt.style.use('dark_background')
        ax1 = plt.subplot2grid((6, 4), (0, 0), rowspan=2, colspan=4)

        data['ClosePrice'].plot(ax=ax1, color='#f5f5f5', lw=2)
        ax1.plot(data.loc[data.Trades == 1.0].index, data.ClosePrice[data.Trades == 1.0], '^', markersize=10, color='#00ff00',
                 label='Buy')
        ax1.plot(data.loc[data.Trades == -1.0].index, data.ClosePrice[data.Trades == -1.0], 'v', markersize=10,
                 color='#dc143c', label='Sell')
        plt.title('New Volatility Adjusted APO Trading Strategy')

        ###The following block is my following style usage:
        # First up is formatting the axis automatically
        locator = AutoDateLocator()
        formatter = AutoDateFormatter(locator)

        # My style and label for the first axis which is time (x) v price (y)
        ax1.grid(True, color='w', linestyle='dotted')
        plt.xlabel('Date/Time')
        ax1.xaxis.set_major_locator(locator)
        ax1.xaxis.set_major_formatter(formatter)
        ax1.spines['bottom'].set_color('#0000cd')
        ax1.spines['top'].set_color('#0000cd')
        ax1.spines['left'].set_color('#0000cd')
        ax1.spines['right'].set_color('#0000cd')
        ax1.tick_params(axis='y', colors='w')
        plt.gca().yaxis.set_major_locator(mticker.MaxNLocator())
        ax1.tick_params(axis='x', colors='w')
        plt.ylabel('Price in $')
        plt.legend()

        # My style, label, also setting the axis automatically (set_major_locator) for the second (APO) axis
        ax2 = plt.subplot2grid((6, 4), (2, 0), sharex=ax1, rowspan=2, colspan=4)
        data['APO'].plot(ax=ax2, color='#00EEEE', lw=2, legend=True)
        plt.ylim(-.5, .5)
        plt.ylabel('APO')
        ax2.grid(True, linestyle='dotted')

        # Style, etc for the third axis which is portfolio value
        ax3 = plt.subplot2grid((6, 4), (4, 0), sharex=ax2, rowspan=2, colspan=4)

        # Plotting Portfolio Value
        data['PortfolioValue'].plot(ax=ax3, color='#9E1B32', lw=2, legend=True)

        # Formatting Values to be placed in the graph

        format_total = '{:.2f}'.format(final_day_total)
        format_final_day_percentage = '{:.2f}'.format(final_day_percentage)
        format_threshold_value = '{:.2f}'.format(threshold_value)
        plt.text(data.index.values[0], data['PortfolioValue'].max() * (8 / 10), 'Total Portfolio Value Using Volatility Adjusted Strategy (APO): ${}\nTotal Return: {}%\nThreshold Value: {}%'.format(format_total, format_final_day_percentage, format_threshold_value))
        plt.gca().yaxis.set_major_locator(mticker.MaxNLocator())
        plt.ylabel('Total Portfolio Value')
        ax3.grid(True, linestyle='dotted')

        # Finishing Touches
        # Autoscaling the chart to the data as well as the plot function
        fig.autofmt_xdate()
        plt.autoscale()
        plt.tight_layout()

        plt.show()



    #Part for printing the charts
    if show_charts:

        #Weekly Losses
        num_days = len(data.index)
        pnl = data['PNL']
        weekly_losses = []
        monthly_losses = []

        for i in range(0, num_days):
            if i >= 5 and pnl[i - 5] > pnl[i]:
                weekly_losses.append(pnl[i] - pnl[i - 5])
            if i >= 20 and pnl[i - 20] > pnl[i]:
                monthly_losses.append(pnl[i] - pnl[i - 20])

        plt.hist(weekly_losses, 50)
        plt.gca().set(title='Weekly Loss Distribution', xlabel='$', ylabel='Frequency')
        plt.show()

        #Monthly Losses
        # Display Monthly Losses
        plt.hist(monthly_losses, 50)
        plt.gca().set(title='Monthly Loss Distribution', xlabel='$', ylabel='Frequency')
        plt.show()


        #Position Distribution
        positions = data['Position']
        plt.hist(positions, 20)
        plt.gca().set(title='Position Distribution', xlabel='Shares', ylabel='Frequency')
        plt.show()


        #Position Holding Time
        position_holding_times = []
        current_pos = 0
        current_pos_start = 0

        for i in range(0, num_days):
            pos = data['Position'].iloc[i]
            if current_pos == 0:
                if pos != 0:
                    current_pos = pos
                    current_pos_start = i
                continue

            # Going from long position to flat or short position or
            # Going from short position to flat or long position
            if current_pos * pos <= 0:
                current_pos = pos
                position_holding_times.append(i - current_pos_start)
                current_pos_start = i

        plt.hist(position_holding_times, 100)
        plt.gca().set(title='Position Holding Time Distribution', xlabel='Holding Time Days', ylabel='Frequency')
        plt.show()


        #Weekly/Monthly Number of Executions
        executions_this_week = 0
        executions_per_week = []
        last_week = 0
        for i in range(0, num_days):
            if data['Trades'].iloc[i] != 0:
                executions_this_week += 1

            if i - last_week >= 5:
                executions_per_week.append(executions_this_week)
                executions_this_week = 0
                last_week = i

        plt.hist(executions_per_week, 10)
        plt.gca().set(title='Weekly number of executions Distribution', xlabel='Number of executions',
                      ylabel='Frequency')
        plt.show()

        # Now look at max executions per month
        executions_this_month = 0
        executions_per_month = []
        last_month = 0

        for i in range(0, num_days):
            if data['Trades'].iloc[i] != 0:
                executions_this_month += 1

            if i - last_month >= 20:
                executions_per_month.append(executions_this_month)
                executions_this_month = 0
                last_month = i

        plt.hist(executions_per_month, 10)
        plt.gca().set(title='Monthly number of executions Distribution', xlabel='Number of executions',
                      ylabel='Frequency')
        plt.show()



        #Plot APO
        # PLOT APO
        data['APO'].plot(x='Date', legend=True)
        plt.show()

        #Total Traded Volume:
        traded_volume = 0
        for i in range(0, num_days):
            if data['Trades'].iloc != 0:
                traded_volume += abs(data['Position'].iloc[i] - data['Position'].iloc[i - 1])
        print('Total Traded Volume: ', traded_volume)






        return data
    else:
        return data




def build_parameter_logs(dataframe, NUM_PERIODS_FAST_LIST, NUM_PERIODS_SLOW_LIST, SMA_NUM_PERIODS_LIST, APO_BUY_VALUE_LIST, APO_SELL_VALUE_LIST):
    NUM_PERIODS_FAST_LOG = []
    NUM_PERIODS_SLOW_LOG = []
    SMA_NUM_PERIODS_LOG = []
    APO_BUY_VALUE_LOG = []
    APO_SELL_VALUE_LOG = []
    MIN_PRICE_MOVE_FROM_LAST_TRADE_LOG = []
    return_log = []
    percent_return_log = []
    transaction_number_log = []

    # Creating copy of data for prevention of dataframe issues
    dataframe = dataframe.copy()

    total_number_combos = len(NUM_PERIODS_FAST_LIST) * len(NUM_PERIODS_SLOW_LIST) * len(SMA_NUM_PERIODS_LIST) * len(APO_BUY_VALUE_LIST) *  len(APO_SELL_VALUE_LIST)
    combo_counter = 1

    temp_parameter_log = []
    for fast_num_days in NUM_PERIODS_FAST_LIST:
        for slow_num_days in NUM_PERIODS_SLOW_LIST:
            for sma_num_days in SMA_NUM_PERIODS_LIST:
                for apo_buy_value in APO_BUY_VALUE_LIST:
                    for apo_sell_value in APO_SELL_VALUE_LIST:

                            #Append values to the temporary (current iteration) parameter log
                            temp_parameter_log.append(fast_num_days)
                            temp_parameter_log.append(slow_num_days)
                            temp_parameter_log.append(sma_num_days)
                            temp_parameter_log.append(apo_buy_value)
                            temp_parameter_log.append(apo_sell_value)



                            #Append values to the relative logs
                            NUM_PERIODS_FAST_LOG.append(fast_num_days)
                            NUM_PERIODS_SLOW_LOG.append(slow_num_days)
                            SMA_NUM_PERIODS_LOG.append(sma_num_days)
                            APO_BUY_VALUE_LOG.append(apo_buy_value)
                            APO_SELL_VALUE_LOG.append(apo_sell_value)


                            #Print current parameters and perform the trading function
                            print('\n')
                            print('*'*50)
                            print('Printing Current Parameters: ', temp_parameter_log)

                            index_parameter_dataframe = apo_non_ra(dataframe, *temp_parameter_log)

                            # Reset Temporary parameter Log
                            temp_parameter_log = []

                            # Record Transaction Number
                            transactions = []
                            transaction_number_log.append(len(transactions))

                            # Return the relative final portfolio value for the trading parameters
                            return_log.append(index_parameter_dataframe['PortfolioValue'][-1])


                            # Adding a little visualization so I can see how long it will take to run
                            print('Trading Iteration {} / {}'.format(combo_counter, total_number_combos))
                            combo_counter += 1
                            print('Final Portfolio Value: ', index_parameter_dataframe['PortfolioValue'][-1])
                            print('*' * 50)
                            print('\n')

    # Creation of 'Base' log, which will then stem into the entire parameter log as well as the top 20 log
    log = {'fast_num_days': NUM_PERIODS_FAST_LOG,
           'slow_num_days': NUM_PERIODS_SLOW_LOG,
           'sma_num_days': SMA_NUM_PERIODS_LOG,
           'apo_buy_values': APO_BUY_VALUE_LOG,
           'apo_sell_values': APO_SELL_VALUE_LOG,
           'Portfolio_Final_Value': return_log,
           'Transaction Number': transaction_number_log}
    parameter_log = pd.DataFrame(log, columns=['fast_num_days', 'slow_num_days', 'sma_num_days',
                                               'apo_buy_values', 'apo_sell_values',
                                               'Portfolio_Final_Value',
                                               'Transaction Number'])

    #The finale of the code
    #Create parameter log and top20 parameter log
    top20_log = parameter_log.nlargest(20, 'Portfolio_Final_Value')

    #Reset top20 log index to prevent complications for new dataframe
    top20_log.reset_index(inplace=True, drop=True)

    #Return the parameter logs, display top 20
    display(top20_log)
    return parameter_log, top20_log


#tsla_data6m = yf.download('TSLA', period='6mo')
#tsla = apo_non_ra(tsla_data6m, NUM_PERIODS_FAST=5, NUM_PERIODS_SLOW=25, SMA_NUM_PERIODS=6, APO_BUY_VALUE=-0.18, APO_SELL_VALUE=0.06, trading_cash=5000, MIN_NUM_DAYS_SINCE_LAST_TRADE=14, show_charts=False, show_special=True)

'''
#Parameter Logs to Iterate through
NUM_PERIODS_FAST_LIST = [5, 10, 15, 20, 25]
NUM_PERIODS_SLOW_LIST = [25, 30, 35, 40, 45]
SMA_NUM_PERIODS_LIST = [6, 12, 18, 24, 30]
APO_BUY_VALUE_LIST = [-.06, -.12, -.18, -.24, -.30]
APO_SELL_VALUE_LIST = [.06, .12, .18, .24, .30]


tsla_data6m = yf.download('TSLA', period='6mo')
tlsa6m, tsla6mtop20 = build_parameter_logs(tsla_data6m, NUM_PERIODS_FAST_LIST, NUM_PERIODS_SLOW_LIST, SMA_NUM_PERIODS_LIST, APO_BUY_VALUE_LIST, APO_SELL_VALUE_LIST)
'''