# main.py
import argparse
from scraper import get_paper_links, download_pdf
from PDFparser import extract_text_and_links
from filters import is_dataset_or_code_link
from utils import save_json


def run_agent(conference_url: str, output_path: str):
    paper_links = get_paper_links(conference_url)
    all_links = []
    for idx, url in enumerate(paper_links, 1):
        try:
            pdf = download_pdf(url)
            _, links = extract_text_and_links(pdf)
            candidates = [ln for ln in links if is_dataset_or_code_link(ln)]
            all_links.extend(candidates)
            print(f"[{idx}] Found {len(candidates)} candidates.")
        except Exception as e:
            print(f"[{idx}] Error: {e}")
    unique = list(set(all_links))
    print(f"Total unique links: {len(unique)}")
    save_json(output_path, unique)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract dataset/code links from OpenReview papers.")
    parser.add_argument('conference_url', help='URL of the OpenReview conference')
    parser.add_argument('output_path', help='Path to save the JSON results')
    args = parser.parse_args()
    run_agent(args.conference_url, args.output_path)
