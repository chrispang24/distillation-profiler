import pandas as pd
import numpy as np
import math
from scipy.interpolate import pchip

class BlendedProfileBuilder():

    def __init__(self):
        pass

    def extract_profiles_from_web(self):
        '''
        Extract distillation profile tables from Crude Monitor website and load into file store
        '''

        oils = pd.read_csv("data/oil-codes.csv")
        profiles_df = pd.DataFrame()

        for code in oils['Code']:
            try:
                # distillation profile can be read from Crude Monitor website
                url = f'https://www.crudemonitor.ca/crudes/dist.php?acr={code}&time=recent'
                tables = pd.read_html(url)

                # distillation profile is first table on webpage
                oil_profile_df = tables[0]
                oil_profile_df["Code"] = code
                profiles_df = profiles_df.append(oil_profile_df)
                print(f"Successfully read profile for oil code {code}.")
            except:
                print(f"No distillation profile found for oil code {code}.")

        profiles_df.to_csv("data/oil-profiles.csv")

    def load_processed_profile(self, code):
        '''
        Load distillation profile from file store and process (isolate mass recovery and temperature features)
        '''

        profile_df = pd.read_csv("data/oil-profiles.csv")

        # isolate relevant columns and rename
        profile_df = profile_df[['Mass % Recovered', 'Temperature( oC )', 'Code']]
        profile_df = profile_df[profile_df['Code'] == code].reset_index(drop=True)
        profile_df.columns = ['recovery', 'temperature', 'code']

        # set initial boiling point (IBP) to 0
        profile_df['recovery'][profile_df['recovery'] == 'IBP'] = 0

        # remove blank recovery point temperature values
        blank_temps = profile_df[profile_df['temperature'] == '-'].index
        profile_df.drop(blank_temps, inplace=True)

        # set data types after cleaning
        profile_df = profile_df.astype({'recovery': 'int'})
        profile_df = profile_df.astype({'temperature': 'float64'})

        return profile_df

    def get_discrete_temperature_range(self, df):
        '''
        Compute temperature range based on min/max of profile
        '''
        return np.arange(math.ceil(df['temperature'].min()), math.floor(df['temperature'].max()), 1)

    def get_global_temperature_range(self, df1, df2):
        '''
        Compute global temperature range based on min/max of profile pair
        '''
        min_val = min(df1['temperature'].min(), df2['temperature'].min())
        max_val = max(df1['temperature'].max(), df2['temperature'].max())
        return np.arange(math.ceil(min_val), math.floor(max_val), 1)

    def get_recovery_interpolation(self, df):
        '''
        Get interpolation over profile range using monotonic cubic splines to find the value of new points
        https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.PchipInterpolator.html

        Using same fit function used by Crude Monitor on distillation profile - interpolation calculator.

        Setting temperature as 'x' variable, will get interpolated values for 'Recovery %' over the range.
        '''
        x = np.array(df['temperature'])
        y = np.array(df['recovery'])

        range = self.get_discrete_temperature_range(df)

        interpolation_fit = pchip(x,y)
        interpolation = pd.DataFrame({'temperature': range, 'recovery': interpolation_fit(range)})
        interpolation = interpolation.set_index('temperature')
        return interpolation

    def merge_interpolations_over_range(self, interp1, interp2, range):
        '''
        Merge interpolations from input pair into the specified temperature range
        '''
        df = pd.DataFrame({'temperature': range})
        df = df.set_index('temperature')
        df = df.join(interp1).join(interp2, rsuffix='_2').reset_index()
        df = df.fillna(method='ffill').fillna(value=0)
        return df

    def compute_blended_profile(self, df, share1, share2, df1, df2):

        profile_percentages = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99] 

        df['blended'] = share1 * df['recovery'] + share2 * df['recovery_2']
        blended_interp = pchip(df['blended'], df['temperature'])
        temperatures = blended_interp(profile_percentages)

        blended_df = pd.DataFrame({'recovery': profile_percentages, 'temperature': temperatures})

        recovery_max = df1['recovery'].max() * share1 + df2['recovery'].max() * share2
        over_max = blended_df[blended_df['recovery'] > recovery_max]['temperature'].index
        blended_df.loc[over_max, 'temperature'] = np.nan
        return blended_df

    def run(self):
        print("Running Blended Distillation Profile Builder...")
        # self.extract_profiles_from_web()

        share1, share2 = 0.01, 0.99

        profile1_df = self.load_processed_profile('AHS')
        profile2_df = self.load_processed_profile('OSH')
        
        recovery1 = self.get_recovery_interpolation(profile1_df)
        recovery2 = self.get_recovery_interpolation(profile2_df)

        pair_range = self.get_global_temperature_range(profile1_df, profile2_df)
        paired_recoveries = self.merge_interpolations_over_range(recovery1, recovery2, pair_range)
        blended_df = self.compute_blended_profile(paired_recoveries, share1, share2, profile1_df, profile2_df)
        print(blended_df)

if __name__ == "__main__":

    builder = BlendedProfileBuilder()
    builder.run()