'''
Generation tests for BlendedProfileBuilder
'''

import itertools
import pandas as pd
from profile_builder import BlendedProfileBuilder

def generate_paired_blends(oil_codes):
    '''
    Generate blended pairs for all oil code pairings
    and store results to file store
    '''

    blended_profiles_df = pd.DataFrame()

    for pair in itertools.combinations(oil_codes,2):
        code1, code2 = pair
        volume1, volume2 = 0.5, 0.5

        print(f"Running builder for oil pairing: {code1}, {code2}")
        model = BlendedProfileBuilder(code1, code2, volume1, volume2)
        blended_df = model.run()
        blended_df["code1"] = code1
        blended_df["code2"] = code2
        blended_df["share1"] = volume1
        blended_df["share2"] = volume2
        blended_profiles_df = blended_profiles_df.append(blended_df)

    blended_profiles_df.to_csv("data/blended-profiles-all-pairings.csv")

def generate_percentage_blends(oil_codes):
    '''
    Generate blended results for all valid blend percentage ranges
    and store results to file store
    '''

    if len(oil_codes) <= 1:
        print("Not enough oil codes with valid data")
        return

    code1 = oil_codes[0]
    code2 = oil_codes[1]

    percentage_profiles_df = pd.DataFrame()

    for volume1 in range(1,100):
        share1 = volume1/100.0
        share2 = (100 - volume1)/100.0

        print(f"Running builder for percentage pairing: {share1:.2f}, {share2:.2f}")
        model = BlendedProfileBuilder(code1, code2, share1, share2)
        blended_df = model.run()
        blended_df["code1"] = code1
        blended_df["code2"] = code2
        blended_df["share1"] = share1
        blended_df["share2"] = share2
        percentage_profiles_df = percentage_profiles_df.append(blended_df)

    percentage_profiles_df.to_csv("data/blended-profiles-all-percentages.csv")

if __name__ == "__main__":

    print("\nTest suite for BlendedProfileBuilder...")

    # Retrieve valid oil codes with stored profile data
    profiles_df = pd.read_csv(("data/oil-profiles.csv"))
    valid_oil_codes = profiles_df['Code'].unique()

    print("\nGenerating 50-50% profiles for all oil code pairings...")
    generate_paired_blends(valid_oil_codes)

    print("\nGenerating profiles for all blend ranges [1-99] for first pair...")
    generate_percentage_blends(valid_oil_codes)
