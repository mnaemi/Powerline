import pandas as pd
from src import functions as fn
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns

def plot_energy_supply_curve(df_bids , region, interval_datetime,adjust_by_maxavail=True):
    """this function plots the supply curve using the calc_energy_supply_interval from functions module
    
    inputs:
    -----------
    df_bids: output of prepare_data - i.e. raw bids merged to NEM registery df
    region:  NEM regions
    interval_datetime: in the format of 'yyyy-mm-dd HH:MM:SS'
    adjust_by_maxavail: boolean - if true adjust the volume in bid bands based on MAXAVAIL column using adjust_band_vols_by_maxavail funct
    
    outputs:
    -----------
    plotly figure 
    
    Example
    -----------
    fig = plot_energy_supply_curve(df_bids, 'VIC1', '2024-06-13 11:10:00')
    """
    df_supply = fn.calc_energy_supply_interval(df_bids, region , interval_datetime,adjust_by_maxavail)

    rrp = df_supply.rrp.iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_supply['Cumulative_Volume'], y=df_supply['Price'], mode='lines', name='Supply'))
    fig.add_trace(go.Scatter(x=[df_supply['Cumulative_Volume'].min(), df_supply['Cumulative_Volume'].max()], 
                             y=[rrp , rrp], mode='lines', line=dict(color='red', dash='dash'),name='RRP'))
    fig.update_layout(title="Supply Curve", xaxis_title="Volume (MW)", yaxis_title="Price ($/MWh)", legend_title="Legend")
    return fig



def plot_energy_supply_curve_by_fuel(df_bids , region, interval_datetime):
    df_supply = fn.calc_energy_supply_interval(df_bids, region , interval_datetime)
    rrp = df_supply.rrp.iloc[0]
    fig = plt.figure(figsize=[12,8])
    sns.scatterplot(
    data=df_supply,
    x='Cumulative_Volume',
    y='Price',
    hue='Fuel',  
    s=50,
    edgecolor='none' 
    )
    plt.axhline(y=rrp, color='r', linestyle='--', label="RRP")

def plot_price_setter_by_fuel(price_setters):
    price_setters['Fuel_index'] = pd.Categorical(price_setters['Fuel']).codes + 1 
    fig, ax = plt.subplots(figsize=[12,8])
    sns.scatterplot(
        data=price_setters,
        x='interval_datetime',
        y='Fuel_index',
        hue='Fuel',       
        palette='Set1',   
        s=50,            
        edgecolor='none'
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M')) 


def plot_duid_revenue_with_price_setting(df_revenue, price_setters, DUID = 'MURRAY'):
    df_revenue_duid = df_revenue.loc[df_revenue.DUID == DUID]
    price_setter_duid = price_setters[['DUID', 'interval_datetime']]
    price_setter_duid.rename(columns = {'DUID':'price_setter_DUID'},inplace=True)
    df_corr = df_revenue_duid.merge(price_setter_duid , how = 'left', on=['interval_datetime'])
    df_corr['price_set'] = (df_corr['DUID'] == df_corr['price_setter_DUID']).astype(int)
    

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(x=df_corr['interval_datetime'], y=df_corr['revenue'], mode='lines', name='Revenue'),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=df_corr['interval_datetime'], y=df_corr['price_set'], mode='none', name='Price Set',fill='tozeroy'),
        secondary_y=True
    )
    fig.update_layout(
        title_text="Revenue and Price Set",
        xaxis_title="Interval Datetime",
        yaxis_title="Revenue ($)",
        legend_title="Legend"
    )
    fig.update_yaxes(title_text="Price Set Active", secondary_y=True)

    fig.show()
    correlation = df_corr['revenue'].corr(df_corr['price_set'])
    print(f"The correlation between revenue and price_set is: {correlation}")

def plot_success_rate_by_tod(df_success_rates, by_fuel= True):
    df_success_rates = fn.convert_datetime_to_period(df_success_rates, 'interval_datetime')
    df_success_tod = df_success_rates[['interval_period','success_rate']].groupby('interval_period',as_index=False).mean()
    
    df_success_by_fuel_tod = df_success_rates[['interval_period','Fuel','success_rate']].groupby(['Fuel','interval_period'],as_index=False).mean()

    if by_fuel:
        fig = plt.figure()
        sns.lineplot(
            data=df_success_by_fuel_tod,
            x='interval_period',
            y='success_rate',
            hue='Fuel'
        )
        return df_success_tod, df_success_by_fuel_tod
    else:
        fig = plt.figure()
        sns.lineplot(df_success_tod, x= 'interval_period', y= 'success_rate')
        return df_success_tod
    
def plot_price_band_vol_movement(df_price_band_clusters, duid):
    df_plot = df_price_band_clusters.copy()
    df_plot= df_plot.loc[df_plot.DUID==duid]
    df_plot = df_plot.set_index(['interval_datetime'])
    fig, ax = plt.subplots(figsize=[12, 8])
    df_plot.plot(kind='area', stacked=True, ax=ax)
    plt.ylabel('MW')
    plt.title(duid)
    return fig

