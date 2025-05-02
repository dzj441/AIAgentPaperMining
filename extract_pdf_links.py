from collections import defaultdict

def extract_relevant_links(text):
    pdf_links = defaultdict(list)
    current_pdf = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith(".pdf:") or line.endswith(".pdf"):
            current_pdf = line.rstrip(":")
        elif current_pdf:
            if any(keyword in line.lower() for keyword in ['dataset', 'benchmark', 'github']):
                pdf_links[current_pdf].append(line)

    return pdf_links

with open('D:\data_mining\AIAgentPaperMining\extracted_urls.txt', 'r', encoding='utf-8') as file:
    txt_content = file.read()
result = extract_relevant_links(txt_content)
for pdf, links in result.items():
    print(f"{pdf}:")
    for link in links:
        print(f"  {link}")
with open('extract_pdf_links.txt', 'w', encoding='utf-8') as out_file:
    for pdf, links in result.items():
        out_file.write(f"{pdf}:\n")
        for link in links:
            out_file.write(f"  {link}\n")