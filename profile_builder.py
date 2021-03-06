'''
Blended Distillation Profile Builder
'''

import math
import pandas as pd
import numpy as np
from scipy.interpolate import pchip

class BlendedProfileBuilder():
    '''
    Blended distillation builder class for processing blended oil profiles
    '''

    def __init__(self, code1, code2, volume1, volume2, refresh=False):
        '''
        Args:
            code1 (str): The first oil code parameter.
            code2 (str): The second oil code paramter.
            volume1 (float): The volume share of first oil code.
            volume2 (float): The volume share of second oil code.
            refresh (bool): Flag to refresh profile data from web.
        '''
        if volume1 <= 0 or volume1 >= 1 or volume2 <= 0 or volume2 >= 1:
            raise ValueError

        self.profile_percentages = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99]
        self.code1 = code1
        self.code2 = code2
        self.volume1 = volume1
        self.volume2 = volume2
        self.refresh = refresh

    @staticmethod
    def extract_profiles_from_web():
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

    @staticmethod
    def load_processed_profile(code):
        '''
        Load distillation profile from file store and process
        (isolate mass recovery and temperature features)
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

    @staticmethod
    def get_discrete_temperature_range(profile_df):
        '''
        Generate temperature points based on min/max range of profile
        '''
        return np.arange(math.ceil(profile_df['temperature'].min()),
            math.floor(profile_df['temperature'].max()), 1)

    @staticmethod
    def get_global_temperature_range(df1, df2):
        '''
        Generate global temperature points based on min/max range of profile pair
        '''
        min_val = min(df1['temperature'].min(), df2['temperature'].min())
        max_val = max(df1['temperature'].max(), df2['temperature'].max())
        return np.arange(math.ceil(min_val), math.floor(max_val), 1)

    def get_recovery_interpolation(self, profile_df):
        '''
        Get interpolation over profile range using monotonic cubic splines to find new points
        https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.PchipInterpolator.html

        Using same fit function used by Crude Monitor on distillation
        profile interpolation calculator.

        Setting temperature as 'x' variable, will get interpolations
        for 'Recovery %' over the range.
        '''
        x_values = np.array(profile_df['temperature'])
        y_values = np.array(profile_df['recovery'])

        temperature_range = self.get_discrete_temperature_range(profile_df)

        interpolation_fit = pchip(x_values,y_values)
        interpolation = pd.DataFrame({'temperature': temperature_range,
            'recovery': interpolation_fit(temperature_range)})
        interpolation = interpolation.set_index('temperature')
        return interpolation

    @staticmethod
    def merge_interpolations_over_range(interp1, interp2, temperature_range):
        '''
        Merge interpolations from input pair into the specified temperature range
        '''
        merged_df = pd.DataFrame({'temperature': temperature_range})
        merged_df = merged_df.set_index('temperature')
        merged_df = merged_df.join(interp1).join(interp2, rsuffix='_2').reset_index()
        merged_df = merged_df.fillna(method='ffill').fillna(value=0)
        return merged_df

    def compute_blended_profile(self, pair_df, share1, share2, df1, df2):
        '''
        Compute blended distillation profile using volume share and reversed interpolation
        '''

        # at each temperature point, compute blended recovery rate
        pair_df['blended'] = share1 * pair_df['recovery'] + share2 * pair_df['recovery_2']

        # using blended recovery rate, perform an interpolatio to now
        # get temperatures at each recovery level
        blended_interp = pchip(pair_df['blended'], pair_df['temperature'])
        temperatures = blended_interp(self.profile_percentages)

        blended_df = pd.DataFrame({'recovery': self.profile_percentages, 'temperature': temperatures})

        # compute maximum possible overall recovery rate for blended mixture and
        # set any recovery points above this to NaN in final profile
        recovery_max = df1['recovery'].max() * share1 + df2['recovery'].max() * share2
        over_max = blended_df[blended_df['recovery'] > recovery_max]['temperature'].index
        blended_df.loc[over_max, 'temperature'] = np.nan

        return blended_df

    def run(self):
        '''
        Execute blended distillation profile builder
        Refresh distillation profiles if specified
        '''
        if self.refresh:
            self.extract_profiles_from_web()

        # load distillation profiles and create recovery interpolations
        profile1_df = self.load_processed_profile(self.code1)
        profile2_df = self.load_processed_profile(self.code2)
        recovery1 = self.get_recovery_interpolation(profile1_df)
        recovery2 = self.get_recovery_interpolation(profile2_df)

        # using global temperature range for profile pair, merge interpolations and then
        # generate final blended distillation profile
        global_range = self.get_global_temperature_range(profile1_df, profile2_df)
        paired_recovery = self.merge_interpolations_over_range(recovery1, recovery2, global_range)
        blended_df = self.compute_blended_profile(paired_recovery,
            self.volume1, self.volume2, profile1_df, profile2_df)

        return blended_df

if __name__ == "__main__":

    print("\nBlended Distillation Profile Builder...")

    # load valid oil profiles from file store
    valid_profiles_df = pd.read_csv("data/oil-profiles.csv")
    valid_oil_codes = valid_profiles_df['Code'].unique()

    print("\nDistillation profile available for following oil codes:")
    print(valid_oil_codes)

    # prompt user for blended oil mixture details
    while True:
        print("\nEnter a first vaild oil code:")
        input_code1 = input().upper()
        print("\nEnter a second vaild oil code:")
        input_code2 = input().upper()
        print("\nEnter a volume for the first oil code:")
        input_volume1 = input()
        print("\nEnter a volume for the second oil code:")
        input_volume2 = input()
        print("\nDo you want to update distillation profiles from Crude Monitor? (Y/N)")
        input_update = input().upper()

        if input_code1 not in valid_oil_codes or input_code2 not in valid_oil_codes:
            print("\nYou entered at least one invalid oil code or code with no data. Try again.")
            continue

        try:
            input_volume1 = float(input_volume1)
            input_volume2 = float(input_volume2)
            total_volume = input_volume1 + input_volume2
            input_share1 = input_volume1 / total_volume
            input_share2 = input_volume2 / total_volume
        except ValueError:
            print("\nYou entered at least one invalid volume. Try again.")
            continue

        if len(input_update) > 0 and input_update[0] in ['Y','N']:
            input_update = input_update[0] == 'Y'
        else:
            print("\nYou entered an invalid entry for updating profiles. Try again.")
            continue

        break

    # generate blended distillation profiel using builder
    builder = BlendedProfileBuilder(input_code1, input_code2, 
        input_share1, input_share2, input_update)
    blended_profile_df = builder.run()

    print(f"\nBlended distillation profile for {input_code1} ({input_share1*100:.1f}%) and {input_code2} ({input_share2*100:.1f}%):")
    print(blended_profile_df)
