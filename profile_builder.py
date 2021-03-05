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
        profile_df.columns = ['Recovery', 'Temperature', 'Code']

        # set initial boiling point (IBP) to 0
        profile_df['Recovery'][profile_df['Recovery'] == 'IBP'] = 0

        # remove blank recovery point temperature values
        blank_temps = profile_df[profile_df['Temperature'] == '-'].index
        profile_df.drop(blank_temps, inplace=True)

        # set data types after cleaning
        profile_df = profile_df.astype({'Recovery': 'int'})
        profile_df = profile_df.astype({'Temperature': 'float64'})

        return profile_df

    def get_interpolation_fit(self, df, range):
        '''
        Get interpolation over specified range using monotonic cubic splines to find the value of new points
        https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.PchipInterpolator.html

        Using same fit function used by Crude Monitor on distillation profile - interpolation calculator.

        Setting temperature as 'x' variable, will get interpolated values for 'Recovery %' over the range.
        '''
        x = np.array(df['Temperature'])
        y = np.array(df['Recovery'])

        interpolation_fit = pchip(x,y)
        return interpolation_fit(range)

    def run(self):
        print("Running Blended Distillation Profile Builder...")
        # self.extract_profiles_from_web()

        profile_df = self.load_processed_profile('AHS')

        interpolation_range = np.arange(math.ceil(profile_df['Temperature'].min()), math.floor(profile_df['Temperature'].max()), 1)
        interpolation = self.get_interpolation_fit(profile_df, interpolation_range)
        print(interpolation)





if __name__ == "__main__":

    builder = BlendedProfileBuilder()
    builder.run()