import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. Page Configuration & UI Layout
st.set_page_config(page_title="SEO Title Tag Generator")

st.title("Bulk SEO Title Tag Generator")

st.header("By SEOAirman")

st.write(
    "Paste your URLs below. Each page will be crawled and a new, "
    "perfectly optimized title tag will be written. You will have the "
    "option to export these as a CSV if desired."
)

# 2. Securely Retrieve the OpenAI API Key from Streamlit Cloud Secrets
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = None

if not api_key:
    st.warning(
        "⚠️ API Key missing. Please configure your 'OPENAI_API_KEY' "
        "in your Streamlit dashboard secrets."
    )

# 3. User Input Box
url_input = st.text_area(
    "Enter your URLs (one URL per line):",
    height=200,
    placeholder="https://example.com\nhttps://example.com/about"
)

# 4. Clean and Normalize URLs
cleaned_urls = []

for url in url_input.splitlines():
    url = url.strip()

    if url == "":
        continue

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    cleaned_urls.append(url)

# Optional testing preview
# st.write(cleaned_urls)


# 5. Helper Function to Scrape Website Headings and Content
def scrape_url(url):
    try:
        # Disguise the script as a regular web browser to prevent some security blocks
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract current title tag
            current_title = (
                soup.title.string.strip()
                if soup.title and soup.title.string
                else "No current title tag"
            )

            # Extract H1s
            h1s = [h1.get_text(strip=True) for h1 in soup.find_all("h1")]

            # Extract body text
            body_text = (
                soup.body.get_text(" ", strip=True)[:1000]
                if soup.body
                else "No readable text content found"
            )

            # Combine the elements for the AI to analyze
            return (
                f"Current Title: {current_title}\n"
                f"Main Headings: {', '.join(h1s) if h1s else 'No H1 found'}\n"
                f"Page Content Snippet: {body_text}"
            )

        else:
            return f"Error: Unable to fetch page. Status Code: {response.status_code}"

    except Exception as e:
        return f"Error: Connection failed. {str(e)}"


# 6. The Core Execution Engine
if st.button("Generate SEO Title Tags"):
    if not cleaned_urls:
        st.error("Please enter at least one URL.")

    elif not api_key:
        st.error("Cannot proceed. An OpenAI API Key is required to run this tool.")

    else:
        results = []

        # Initialize the OpenAI client
        client = OpenAI(api_key=api_key)

        # Display a visual progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        for index, url in enumerate(cleaned_urls):
            status_text.text(
                f"Optimizing title tag... ({index + 1}/{len(cleaned_urls)}): {url}"
            )

            # Step A: Scrape the page
            page_data = scrape_url(url)

            # Step B: If scraping failed, log the error.
            # If it worked, send it to OpenAI.
            if "Error:" in page_data:
                results.append(
                    {
                        "URL": url,
                        "Optimized_Title": page_data
                    }
                )

            else:
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are an elite SEO Specialist. Analyze the provided "
                                    "web page content and generate a single, highly optimized "
                                    "meta title tag.\n\n"
                                    "Strict Constraints:\n"
                                    "1. Length must be between 50 and 60 characters including spaces. "
                                    "Absolute maximum of 60 characters.\n"
                                    "2. Front-load the primary keyword or main topic at the very "
                                    "beginning of the title.\n"
                                    "3. Output ONLY the final title string. Do not include quotes, "
                                    "explanations, markdown, or text like 'Here is your title:'."
                                )
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"URL: {url}\n\n"
                                    f"Scraped Page Context:\n{page_data}"
                                )
                            }
                        ]
                    )

                    ai_title = response.choices[0].message.content.strip()

                    results.append(
                        {
                            "URL": url,
                            "Optimized_Title": ai_title
                        }
                    )

                except Exception as e:
                    results.append(
                        {
                            "URL": url,
                            "Optimized_Title": f"Generation Error: {str(e)}"
                        }
                    )

            # Update visual progress bar
            progress_bar.progress((index + 1) / len(cleaned_urls))

        # 7. Display the Outputs
        status_text.text("Generation complete!")

        df = pd.DataFrame(results)

        # Show interactive preview table on screen
        st.dataframe(df, use_container_width=True)

        # Generate the physical CSV file download button
        csv_data = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="💾 Download CSV Spreadsheet",
            data=csv_data,
            file_name="seo_titles_export.csv",
            mime="text/csv"
        )
