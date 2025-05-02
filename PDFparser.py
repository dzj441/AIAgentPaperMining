# # parser.py

# import re
# import pymupdf

# def extract_text_and_links(pdf_bytes: bytes) -> tuple:
#     """Extract full text and all external URLs from a PDF."""
#     text = []
#     links = []
#     doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
#     for page in doc:
#         text.append(page.get_text())
#         for link in page.get_links():
#             uri = link.get('uri')
#             if uri:
#                 links.append(uri)
#     doc.close()
#     full_text = "\n".join(text)

#     # regex find extra URLs
#     extra_urls = re.findall(r'(?:http[s]?://|www\.)\S+', full_text)
#     for url in extra_urls:
#         url = url.rstrip('；。；，,."]')
#         links.append(url)

#     # dedupe preserving order
#     seen = set()
#     unique = []
#     for url in links:
#         if url not in seen:
#             seen.add(url)
#             unique.append(url)
#     return full_text, unique


# def remove_prefix_urls(url_list):
#     url_list = sorted(set(url_list), key=len)
#     filtered_urls = []
#     for i, url in enumerate(url_list):
#         is_prefix = False
#         for other_url in url_list[i+1:]:
#             if other_url.startswith(url) and len(other_url) > len(url):
#                 is_prefix = True
#                 break
#         if not is_prefix:
#             filtered_urls.append(url)
#     return filtered_urls


# if __name__ == "__main__":
#     import sys
#     pdf_path = r"D:/data_mining/ICLR-spotlight-part2/l6QnSQizmN.pdf"

#     # 读取 PDF 文件为 bytes
#     try:
#         with open(pdf_path, "rb") as f:
#             pdf_bytes = f.read()
#     except Exception as e:
#         print(f"无法读取文件 {pdf_path}: {e}")
#         sys.exit(1)

#     # 调用函数并打印结果
#     full_text, links = extract_text_and_links(pdf_bytes)

#     print("=== 提取到的文本 ===")
#     with open("test.txt", "w", encoding="utf-8", errors="ignore") as f:
#         f.write(full_text) # validate that all things are printed out

#     # print(len(full_text))
#     print("\n=== 提取到的链接 ===")
#     links.sort()
#     for url in links:
#         print(url)
#     filtered_urls = remove_prefix_urls(links)
#     print("\n删除无意义的网址后剩下的网址")
#     filtered_urls.sort()
#     for url in filtered_urls:
#         print(url)



# parser.py

import os
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

def remove_prefix_urls(url_list):
    url_list = sorted(set(url_list), key=len)
    filtered_urls = []
    for i, url in enumerate(url_list):
        is_prefix = False
        for other_url in url_list[i+1:]:
            if other_url.startswith(url) and len(other_url) > len(url):
                is_prefix = True
                break
        if not is_prefix:
            filtered_urls.append(url)
    return filtered_urls

def process_folder(folder_path, output_file_path):
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_path = os.path.join(root, file)
                    try:
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                    except Exception as e:
                        print(f"[错误] 无法读取 {pdf_path}: {e}")
                        continue

                    print(f"[处理] {file}")
                    _, links = extract_text_and_links(pdf_bytes)
                    filtered_urls = remove_prefix_urls(links)
                    filtered_urls.sort()
                    output_file.write(f"{file}:\n")
                    for url in filtered_urls:
                        output_file.write(f"  {url}\n")
                    output_file.write("\n")

if __name__ == "__main__":
    folder_path = r"D:/data_mining/ICLR-spotlight-part2"
    output_file_path = "extracted_urls.txt"
    process_folder(folder_path, output_file_path)
    print(f"\n完成，所有结果保存在 {output_file_path}")
