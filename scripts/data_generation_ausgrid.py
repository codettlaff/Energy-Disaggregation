"""Generate processed Ausgrid solar home data."""
import os
import pandas as pd

def generate_ausgrid_data():

    base_dir = os.path.join(os.path.dirname(__file__), '..')
    data_dir = os.path.join(base_dir, 'data', 'ausgrid')
    processed_data_dir = os.path.join(base_dir, 'processed_data')
    os.makedirs(processed_data_dir, exist_ok=True)

    # Load each yearly CSV, skipping the explanatory first row, and drop the empty 'Row Quality' column
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    df_list = [
        pd.read_csv(os.path.join(data_dir, f), skiprows=1, low_memory=False)
        .drop(columns='Row Quality', errors='ignore')
        for f in csv_files
    ]
    merged_df = pd.concat(df_list, ignore_index=True, sort=False)

    # Wide (48 half-hour columns) -> long (time, kWh)
    id_cols = merged_df.columns[:5]
    df_long = merged_df.melt(
        id_vars=id_cols,
        value_vars=merged_df.columns[5:],
        var_name='time',
        value_name='kWh')

    # Combine date and time into a single datetime column
    df_long['datetime'] = pd.to_datetime(
        df_long['date'].astype(str) + ' ' + df_long['time'],
        format='mixed',
        dayfirst=True,
        errors='coerce')
    df_long = df_long.drop(columns=['date', 'time'])

    # One row per customer/datetime, one column per consumption category (CL, GC, GG)
    df = df_long.pivot_table(
        index=['Customer', 'Generator Capacity', 'Postcode', 'datetime'],
        columns='Consumption Category',
        values='kWh',
        aggfunc='sum').reset_index()

    df['Pload'] = df['CL'] + df['GC']
    df['Pgen'] = df['GG']
    df['Pnet'] = df['Pload'] + df['Pgen']
    df = df.drop(columns=['CL', 'GC', 'GG'], errors='ignore')

    df.to_csv(os.path.join(processed_data_dir, 'ausgrid_processed_data.csv'), index=False)

if __name__ == "__main__":
    generate_ausgrid_data()