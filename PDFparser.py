import os
import re
import pymupdf

class PdfLinkExtractor:
    def __init__(self, pdf_root_dir: str, output_file: str, flatten: bool = False,
                 skip_domains=None, replacements=None):
        """
        :param pdf_sroot_dir:    要递归搜索 PDF 的根目录
        :param output_file: 结果写入的文本文件路径
        :param flatten:     如果为 True，则输出一个全局去重的 URL 列表（扁平化），
                            否则按文件分组输出。
        :param skip_domains: 要跳过的域名或 URL 片段列表
        :param replacements: 替换映射 dict，key 为待替换子串，value 为目标子串
        """
        self.pdf_root_dir = pdf_root_dir
        self.output_file = output_file
        self.flatten = flatten
        self.skip_domains = skip_domains or [
            "openreview.net/pdf",
            "arxiv.org",
            "doi.org",
            "ieee.org",
            "aclweb.org",
            "springer.com",
            "dblp.org"
        ]
        # 使用字典存储多对替换规则
        self.replacements = replacements or {
            "huggingface.co": "hf-mirror.com",
            # 可以继续添加其他替换对
        }

    @staticmethod
    def extract_text_and_links(pdf_bytes: bytes) -> list:
        """从 PDF 二进制中提取所有外部 URL 并去重（保留顺序）。"""
        text_fragments = []
        links = []
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text_fragments.append(page.get_text())
            for link in page.get_links():
                uri = link.get("uri")
                if uri:
                    links.append(uri)
        doc.close()

        full_text = "\n".join(text_fragments)
        extra = re.findall(r'(?:http[s]?://|www\.)\S+', full_text)
        for url in extra:
            links.append(url.rstrip('；。；，,."\]'))

        seen = set()
        unique = []
        for url in links:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique

    @staticmethod
    def remove_prefix_urls(url_list: list) -> list:
        """删除那些严格作为其他 URL 前缀存在的“冗余”短链接。"""
        url_list = sorted(set(url_list), key=len)
        result = []
        for i, u in enumerate(url_list):
            if not any(other.startswith(u) and len(other) > len(u)
                       for other in url_list[i+1:]):
                result.append(u)
        return result

    def filter_urls(self, urls: list) -> list:
        """
        按照 skip_domains 跳过不需要的 URL 片段。
        """
        filtered = []
        for url in urls:
            if any(skip in url for skip in self.skip_domains):
                continue
            filtered.append(url)
        return filtered

    def apply_replacements(self, urls: list) -> list:
        """
        按照 replacements 字典，对 URL 进行子串替换，并打印替换日志。
        """
        new_urls = []
        for url in urls:
            updated = url
            for src, tgt in self.replacements.items():
                if src in updated:
                    original = updated
                    updated = updated.replace(src, tgt)
                    # print(f"[替换] {original} -> {updated}")
            new_urls.append(updated)
        return new_urls

    def run(self):
        if self.flatten:
            global_urls = set()

        with open(self.output_file, "w", encoding="utf-8") as out_f:
            for root, _, files in os.walk(self.pdf_root_dir):
                for fn in files:
                    if not fn.lower().endswith(".pdf"):
                        continue

                    pdf_path = os.path.join(root, fn)
                    try:
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                    except Exception as e:
                        print(f"[错误] 读取失败 {pdf_path}: {e}")
                        continue

                    links = self.extract_text_and_links(pdf_bytes)
                    links = self.remove_prefix_urls(links)
                    links = self.filter_urls(links)
                    links = self.apply_replacements(links)

                    if self.flatten:
                        global_urls.update(links)
                    else:
                        out_f.write(f"{fn}:\n")
                        for url in links:
                            out_f.write(f"  {url}\n")
                        out_f.write("\n")

            if self.flatten:
                for url in sorted(global_urls):
                    out_f.write(f"{url}\n")

if __name__ == "__main__":
    from utils import load_config
    config = load_config("config.yaml")

    extractor = PdfLinkExtractor(
        pdf_root_dir = config["scraper"]["pdf_dir"], 
        output_file = config["PDFparser"]["output_path"],
        flatten= config["PDFparser"]["flatten"]
    )
    extractor.run()

