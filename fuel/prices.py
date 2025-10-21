import pandas as pd
import requests
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup

INPUT_CSV = "items.csv"
OUTPUT_DIR = "prices"
REGIONS = ["C-J6MT", "UALX-3", "jita", "amarr", "dodixie"]
BASE_URL = "https://appraise.gnf.lt/item/{}#{}"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_prices_from_page(type_id, region):
    url = BASE_URL.format(type_id, region)
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        tab = soup.find("div", id=region)
        if not tab:
            print(f"Region tab {region} not found for item {type_id}")
            return None

        tables = tab.find_all("table")
        if not tables or len(tables) < 2:
            print(f"Missing expected tables for {region} item {type_id}")
            return None

        def extract_table_data(table):
            result = {}
            for row in table.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    key = th.text.strip()
                    val = td.text.strip().replace(",", "").replace(" ISK", "")
                    try:
                        val = float(val)
                    except:
                        val = None
                    result[key] = val
            return result

        sell_data = extract_table_data(tables[0])
        buy_data = extract_table_data(tables[1])

        combined = {}
        for k, v in sell_data.items():
            combined[f"Sell_{k}"] = v
        for k, v in buy_data.items():
            combined[f"Buy_{k}"] = v

        return combined

    except Exception as e:
        print(f"Error fetching {type_id} {region}: {e}")
        return None


def update_prices_for_region(region):
    df_items = pd.read_csv(INPUT_CSV)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output_data = []

    print(f"\n=== Requesting data for {region} ===")

    for _, row in df_items.iterrows():
        item_name = row["Item"]
        type_id = int(row["ID"])
        print(f"→ {item_name} ({type_id})")

        prices = parse_prices_from_page(type_id, region)
        if prices:
            prices["Item"] = item_name
            prices["TypeID"] = type_id
            prices["Region"] = region
            prices["Timestamp"] = timestamp
            output_data.append(prices)

        time.sleep(0.5)

    if output_data:
        new_df = pd.DataFrame(output_data)

        output_file = os.path.join(OUTPUT_DIR, f"prices_{region}.csv")

        if os.path.exists(output_file):
            old_df = pd.read_csv(output_file)
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        combined_df.to_csv(output_file, index=False)
        print(f"Data saved/appended to {output_file}")
    else:
        print(f"No data collected for {region}")


def get_all_prices():
    for region in REGIONS:
        update_prices_for_region(region)
        time.sleep(1)


if __name__ == "__main__":
    get_all_prices()
