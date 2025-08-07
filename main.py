import re
import time
import json
import pandas as pd
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Use new headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def parse_date(text):
    # Try to find ISO date format yyyy-mm-dd
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    # Else try pandas to parse
    try:
        return str(pd.to_datetime(text).date())
    except:
        return None

def scrape_patents(url, max_pages=3):
    driver = setup_driver()
    driver.get(url)
    time.sleep(5)

    all_data = []
    current_page = 0

    while current_page < max_pages:
        items = driver.find_elements(By.TAG_NAME, "search-result-item")
        print(f"Page {current_page+1}: Found {len(items)} patents")

        for item in items:
            try:
                title = item.find_element(By.CSS_SELECTOR, "h3").text.strip()

                # Extract patent ID and link from state-modifier tag attribute data-result
                state_mod = item.find_element(By.CSS_SELECTOR, "state-modifier")
                data_result = state_mod.get_attribute("data-result")
                patent_id = data_result.split("/")[-1]

                abstract = item.find_element(By.CSS_SELECTOR, "span#htmlContent").text.strip()
                date_text = item.find_element(By.CSS_SELECTOR, "h4.dates").text.strip()
                date_parsed = parse_date(date_text)

                all_data.append({
                    "title": title,
                    "abstract": abstract,
                    "date": date_parsed,
                    "patent_id": patent_id
                })
            except Exception as e:
                print(f"Skipping patent due to error: {e}")

        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "pagination-button[aria-label='Next page']")
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(5)
            current_page += 1
        except Exception:
            print("No next page found or last page reached.")
            break

    driver.quit()
    return all_data

def plot_trends(data):
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors='coerce')
    df = df.dropna(subset=["date"])
    df["month"] = df["date"].dt.to_period('M')

    trend = df.groupby("month").size()
    trend.index = trend.index.to_timestamp()

    plt.figure(figsize=(10,6))
    plt.bar(trend.index, trend.values, width=20)
    plt.title("Patent Filing Trends (Monthly)")
    plt.xlabel("Month")
    plt.ylabel("Number of Patents")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    search_url = "https://patents.google.com/?q=(AI+Healthcare)&before=priority:20250721&after=priority:20220315"

    print("Starting PatentTrendX scraper...")
    patent_list = scrape_patents(search_url, max_pages=3)
    print(f"Scraped {len(patent_list)} patents.")

    with open("patent_data.json", "w", encoding="utf-8") as f:
        json.dump(patent_list, f, indent=2)

    plot_trends(patent_list)