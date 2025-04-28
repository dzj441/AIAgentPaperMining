# main.py
import argparse
from scraper import get_paper_links_via_api, download_pdf_bytes
from PDFparser import extract_text_and_links
from filters import is_dataset_or_code_link
from utils import save_json
import os
from pathlib import Path

# follow maybe follow such steps: 1. download into a dir; 2. open dir and get candidates 3. validate candidates via LLM and Heuristic rules 4. save to json
def main(args):
    # download_pdf(args)   
    print("[INFO] START EXTRACTING LINKS!")
    # 2. open dir and get candidates 3. validate candidates via LLM and Heuristic rules 4. save to json
    run_agent(args)

def download_pdf(args):
    paper_links = get_paper_links_via_api()
    os.makedirs(args.pdf_dir,exist_ok=True)
    # 1. download pdfs into dir
    for idx, url in enumerate(paper_links):
        try:
            paper_id,pdf_bytes = download_pdf_bytes(url)
            filename = os.path.join(args.pdf_dir, f"{paper_id}.pdf")
            with open(filename, "wb") as f:
                    f.write(pdf_bytes)
            print(f"[{idx}] Success: {e}")

        except Exception as e:
            print(f"[{idx}] Error: {e}")

def run_agent(args):
    all_links = []

    for idx,pdf in enumerate(Path(args.pdf_dir).glob("*.pdf")):
        try:
            pdf_bytes = pdf.read_bytes()
            _, links = extract_text_and_links(pdf_bytes)
            candidates = [ln for ln in links if is_dataset_or_code_link(ln)]
            all_links.extend(candidates)
            print(f"[{idx}] Found {len(candidates)} candidates.")
        except Exception as e:
            print(f"[{idx}] Error: {e}")

    unique = list(set(all_links))
    print(f"Total unique links: {len(unique)}")
    save_json(args.output_path, unique)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract dataset/code links from OpenReview papers.")
    parser.add_argument('--conference_url',default=" ",help='URL of the OpenReview conference')
    parser.add_argument('--output_path',default='testresults/result.json' ,help='Path to save the JSON results')
    parser.add_argument('--pdf_dir',default='toyPDFset',help='Path to save the downloaded PDFs')
    args = parser.parse_args()
    main(args)