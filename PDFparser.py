# parser.py

import re
import pymupdf

def extract_text_and_links(pdf_bytes: bytes) -> tuple:
    """Extract full text and all external URLs from a PDF."""
    text = []
    links = []
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        text.append(page.get_text())
        for link in page.get_links():
            uri = link.get('uri')
            if uri:
                links.append(uri)
    doc.close()
    full_text = "\n".join(text)

    # regex find extra URLs
    extra_urls = re.findall(r'(?:http[s]?://|www\.)\S+', full_text)
    for url in extra_urls:
        url = url.rstrip('；。；，,."]')
        links.append(url)

    # dedupe preserving order
    seen = set()
    unique = []
    for url in links:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return full_text, unique


if __name__ == "__main__":
    import sys
    pdf_path = r"iclr2025_oral_papers\0ctvBgKFgc.pdf"

    # 读取 PDF 文件为 bytes
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        print(f"无法读取文件 {pdf_path}: {e}")
        sys.exit(1)

    # 调用函数并打印结果
    full_text, links = extract_text_and_links(pdf_bytes)

    print("=== 提取到的文本 ===")
    with open("test.txt", "w", encoding="utf-8", errors="ignore") as f:
        f.write(full_text) # validate that all things are printed out

    # print(len(full_text))
    print("\n=== 提取到的链接 ===")
    for url in links:
        print(url)