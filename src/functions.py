
#%%
import pandas as pd
import numpy as np


# #%%
# input_dir = './materials/'
# bid_filename = 'raw_bid_data_2024-06-13.xlsx'
# nem_filename = 'NEM Registration and Exemption List.xlsx'

# raw_bids = pd.read_excel(input_dir + bid_filename)
# nem_registery = pd.read_excel(input_dir + nem_filename, sheet_name='PU and Scheduled Loads')

# %%
volbands_columns = ['BANDAVAIL{}'.format(i) for i in range(1,11)]
priceband_columns = ['PRICEBAND{}'.format(i) for i in range(1,11)]

def prepare_data(raw_bids, nem_registery):
    nem_registery = nem_registery[['Region','DUID' , 'Fuel Source - Descriptor','Reg Cap generation (MW)']]
    raw_bids.rename(columns = {'duid' : 'DUID'},inplace=True)
    nem_registery = nem_registery.rename(columns={'Fuel Source - Descriptor': 'Fuel',
                                                  'Reg Cap generation (MW)': 'Capacity'})
    nem_registery.loc[nem_registery.Fuel=='Grid','Fuel'] = 'Battery'
    nem_registery.loc[nem_registery.Fuel=='Water','Fuel'] = 'Hydro'
    df_bids = raw_bids.merge(nem_registery , on = ['DUID'], how = 'left')
    df_bids = df_bids 
    return df_bids, nem_registery

def adjust_band_vols_by_maxavail(row):
    """This function adjust volume bands based on max available"""
    remaining_vol = row["MAXAVAIL"]
    adjusted_volumes = []
    for col in volbands_columns:
        if remaining_vol > row[col]:
            adjusted_volumes.append(row[col])
            remaining_vol -= row[col]
        else:
            adjusted_volumes.append(remaining_vol)
            remaining_vol = 0
    return adjusted_volumes


#%%
# region = 'VIC1'
# interval_datetime = '2024-06-13 11:10:00'

def calc_energy_supply_interval(df_bids:pd.DataFrame , region:str , interval_datetime:str, adjust_by_maxavail:bool = True):
    """this function prepares the supply curve dataframe using bids dataframe with/without
    adjust volumes based on Max Availability of plants
    
    inputs:
    -----------
    df_bids: output of prepare_data - i.e. raw bids merged to NEM registery df
    region:  NEM regions
    interval_datetime: in the format of 'yyyy-mm-dd HH:MM:SS'
    adjust_by_maxavail: boolean - if true adjust the volume in bid bands based on MAXAVAIL column using adjust_band_vols_by_maxavail funct
    
    outputs:
    -----------
    df_supply: dataframe of supply curve
    
    Example
    -----------
    df_supply = calc_energy_supply_interval(df_bids, 'VIC1', '2024-06-13 11:10:00')
    """

    df_bids_region = df_bids.loc[(df_bids.Region==region) & (df_bids.interval_datetime == interval_datetime)]
    if df_bids_region.empty:
        raise ValueError("df bids is empty")
    
    if adjust_by_maxavail:
        df_bids_region[volbands_columns] = df_bids_region.apply(lambda row :pd.Series(adjust_band_vols_by_maxavail(row)),axis=1)

    df_filtered = df_bids_region[['DUID'] + priceband_columns + volbands_columns]

    #unpivot the bid df to have bid bands as separate rows
    price_df = df_filtered.melt(id_vars=['DUID'], value_vars=priceband_columns, var_name='Price_Band', value_name='Price')
    price_df['Band_index'] = price_df['Price_Band'].str.extract(r'(\d+)').astype(int)
    
    volume_df = df_filtered.melt(id_vars=['DUID'], value_vars=volbands_columns, var_name='Volume_Band', value_name='Volume')
    volume_df['Band_index'] = volume_df['Volume_Band'].str.extract(r'(\d+)').astype(int)

    df_supply = price_df.merge(volume_df , on = ['DUID','Band_index'])
    df_supply.drop(['Price_Band','Volume_Band'],axis=1,inplace=True)
    
    #sort df based on price and calculate cumulative volume
    df_supply = df_supply.sort_values('Price')
    df_supply['Cumulative_Volume'] = df_supply['Volume'].cumsum()
    df_supply['interval_datetime'] = pd.to_datetime(interval_datetime)
    
    #add additional columns useful for further analysis
    df_supply['rrp'] = df_bids_region['rrp'].iloc[0]
    df_supply['forecasted_rrp'] = df_bids_region['forecasted_rrp'].iloc[0]
    df_supply = df_supply.merge(df_bids_region[['DUID','Fuel','TOTALCLEARED','Capacity']],how='left',on='DUID')
    return df_supply


def find_price_setter_interval(df_supply):
    """this function gets the price setter using df_supply of one interval and region based on
    the proximity of rrp and price bands with non-zero volumes"""
    df_price_set = df_supply.copy()
    df_price_set['dist_to_rrp'] = np.abs(df_price_set['rrp'] - df_price_set['Price'])
    df_price_set = df_price_set.sort_values('dist_to_rrp')
    price_setter = df_price_set[(df_price_set['Volume'] > 0)].iloc[[0]]
    return price_setter

def price_setter_by_fuel(df_bids , region:str, start_date:str, end_date:str):
    """this function finds price setter for each 5-min interval between start and end date
    using bids dataframe and  calc_energy_supply_interval and find_price_setter_interval functions

    inputs:
    -----------
    df_bids: output of prepare_data - i.e. raw bids merged to NEM registery df
    region:  NEM regions
    start_date : in format of 'yyyy-mm-dd'
    end_date : in format of 'yyyy-mm-dd'
    
    outputs:
    -----------
    price_setters: dataframe of price setters on 5-min basis
    
    Example
    -----------
    df_supply = price_setter_by_fuel(df_bids , region='VIC1', start_date = '2024-06-13', end_date:'2024-06-14')
    """
   
    intervals = pd.date_range(start=start_date, end=end_date, freq='5min')
    price_setters = []
    for interval in intervals:
        try:
            df_supply = calc_energy_supply_interval(df_bids, region , interval)
            df_price_setter = find_price_setter_interval(df_supply)
            price_setters.append(df_price_setter)
        except:
            continue
    price_setters = pd.concat(price_setters)
    return price_setters

def calc_gen_revenue(df_bids):
    """this function calculates each assets earning on interval basis"""
    time_resolution = 5
    df_revenue = df_bids.copy()
    df_revenue['revenue'] = df_revenue['rrp'] * df_revenue['TOTALCLEARED'] * time_resolution / 60
    df_revenue.fillna(0,inplace=True)
    return df_revenue[['DUID' , 'interval_datetime', 'TOTALCLEARED', 'rrp','revenue']]


def corr_revenue_vs_price_setting_intervals(df_revenue, price_setters):
    """This function calculates a dataframe for daily revenue vs num of intervals each DUID set the price """
    time_resolution = 5
    df_revenue_daily = df_revenue[['DUID','revenue','TOTALCLEARED']].groupby('DUID',as_index=False).sum()
    df_revenue_daily['MWh'] = df_revenue_daily['TOTALCLEARED'] * (time_resolution/60)
    price_setters = convert_datetime_to_period(price_setters, 'interval_datetime', resolution = 5)
    price_setters_summary = price_setters[['DUID','Price']].groupby('DUID',as_index=False).agg(num_price_set=('Price', 'count'))

    df_revenue_daily = df_revenue_daily.merge(price_setters_summary, on ='DUID', how='left')
    df_revenue_price_setters = df_revenue_daily.loc[~df_revenue_daily.num_price_set.isna()]
    return df_revenue_price_setters

def corr_revenue_vs_price_setter_fuel(df_revenue, price_setters):
    """This function calculates a dataframe for daily revenue vs total num of intervals / peak intervals that 
    each fuel set the price """
    time_resolution = 5
    df_revenue_daily = df_revenue[['DUID','revenue','TOTALCLEARED']].groupby('DUID',as_index=False).sum()
    df_revenue_daily['MWh'] = df_revenue_daily['TOTALCLEARED'] * (time_resolution/60)
    price_setters = convert_datetime_to_period(price_setters, 'interval_datetime', resolution = 5)
    price_setters['peak_period'] = (((price_setters['interval_period'] <= 240) &  (price_setters['interval_period'] >=216)) | ((price_setters['interval_period'] <= 108) &  (price_setters['interval_period'] >=84))).astype(int)
    price_setters_summary = price_setters[['DUID','Price','peak_period','Fuel']].groupby(['DUID','Fuel'],as_index=False).agg(num_price_set=('Price', 'count'), num_peak_intvals = ('peak_period','sum'))
    df_revenue_daily_fuel = df_revenue_daily.merge(price_setters_summary, on ='DUID', how='right')
    df_revenue_daily_fuel= df_revenue_daily_fuel.groupby('Fuel').sum(numeric_only=True)
    return df_revenue_daily_fuel

def convert_datetime_to_period(df, datetime_col, resolution = 5):
    df['interval_period'] = df[datetime_col].dt.hour * 60/ resolution + df[datetime_col].dt.minute / resolution + 1 
    return df

def calc_clearing_success_rate_interval(df_supply):
    """this function calculates the success rate of each DUID based on its bid bands volume and total cleared for each 5min interval using df_supply"""
    eps = 0.00001
    interval_datetime = df_supply.interval_datetime.iloc[0]
    df_success = df_supply.loc[df_supply.Price<=df_supply['forecasted_rrp']]
    df_success = df_success.groupby(['DUID','Fuel'],as_index=False).agg(vol_bid = ('Volume','sum'),TOTALCLEARED = ('TOTALCLEARED','first') )
    df_success['success_rate'] = df_success['TOTALCLEARED']  / (df_success['vol_bid']  + eps )
    df_success['success_rate'] = df_success['success_rate'].clip(upper=1)
    df_success['interval_datetime'] = interval_datetime
    return df_success

def calc_clearing_success_rate(df_bids , region, start_date, end_date):
    """this function calculates the success rate of each DUID based on its bid bands volume and total cleared for 
    a date range and region using calc_energy_supply_interval, calc_clearing_success_rate_interval"""
    intervals = pd.date_range(start=start_date, end=end_date, freq='5min')
    df_success_rates = []
    for interval in intervals:
        try:
            df_supply = calc_energy_supply_interval(df_bids, region , interval)
            df_success_interval = calc_clearing_success_rate_interval(df_supply)
            df_success_rates.append(df_success_interval)
        except:
            continue
    df_success_rates = pd.concat(df_success_rates)
    return df_success_rates

def price_bands_clustering_interval(df_supply ,price_bins, duids):
    df = df_supply.loc[df_supply.DUID.isin(duids)]
    df['bin'] = pd.cut(df['Price'], bins=price_bins, right=False)
    bin_volumes = df[['interval_datetime','DUID','bin','Volume']].groupby(['interval_datetime','DUID','bin'],observed = False,as_index=False).sum(numeric_only=True)
    bin_volumes = bin_volumes.pivot_table(index=['interval_datetime','DUID'],values='Volume',columns= 'bin')
    bin_volumes.reset_index(inplace=True)
    return bin_volumes

def price_bands_clustering(df_bids, region, start_date, end_date, price_bins, duids):
    intervals = pd.date_range(start=start_date, end=end_date, freq='5min')
    bin_volumes = []
    for interval in intervals:
        try:
            df_supply = calc_energy_supply_interval(df_bids, region , interval)
            bin_volumes_interval = price_bands_clustering_interval(df_supply ,price_bins, duids)
            bin_volumes.append(bin_volumes_interval)
        except:
            continue
    bin_volumes = pd.concat(bin_volumes)
    return bin_volumes