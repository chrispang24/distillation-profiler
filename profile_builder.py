import pandas as pd

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

    def run(self):
        print("Running Blended Distillation Profile Builder...")
        self.extract_profiles_from_web()


if __name__ == "__main__":

    builder = BlendedProfileBuilder()
    builder.run()