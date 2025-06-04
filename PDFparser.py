import os
import re
import pymupdf
from typing import List, Dict, Any

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
        self.skip_domains = skip_domains
        # 使用字典存储多对替换规则
        self.replacements = replacements

    @staticmethod
    def extract_paper_name_and_links(pdf_bytes: bytes, pdf_filename: str) -> Dict[str, Any]:
        """从 PDF 二进制中提取标题作为 paper_name 和所有外部 URL。"""
        links = []
        paper_name = ""
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

        # 尝试从元数据中获取标题
        if doc.metadata:
            paper_name = doc.metadata.get('title', '')
            if isinstance(paper_name, bytes): # 有时元数据中的标题是字节串
                try:
                    paper_name = paper_name.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        paper_name = paper_name.decode('latin-1') # 尝试其他编码
                    except UnicodeDecodeError:
                        paper_name = "" # 解码失败则留空

        # 如果元数据中没有标题，或者标题为空，则使用文件名（去除扩展名）
        if not paper_name:
            paper_name = os.path.splitext(pdf_filename)[0]
        
        # 清理 paper_name 中的换行符和多余空格
        paper_name = " ".join(paper_name.strip().split())

        for page in doc:
            # text_fragments.append(page.get_text()) # 文本提取暂时不需要了
            for link in page.get_links():
                uri = link.get("uri")
                if uri:
                    links.append(uri)
        doc.close()

        seen = set()
        unique_links = []
        for url in links:
            if url not in seen:
                seen.add(url)
                unique_links.append(url)
        
        return {"paper_name": paper_name, "extracted_links": unique_links}

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

        # regex
        # full_text = "".join(text_fragments).replace("\n", "").replace("\r", "")
        # tld_pattern = r"(?:com|org|net|io|ai|co|edu|gov|cn|uk|info|xyz|dev|app|tech|me|us|jp|de|fr|ru|it|nl|es|ca|au|ch|se|no|fi|in|br|kr|tw|hk|sg|tv|cc|id|my|vn|za|pl|tr|ir|gr|cz|ro|hu|sk|be|at|dk|pt|ar|cl|mx|nz|il|sa|ua|by|lt|lv|ee|bg|hr|si|rs|ba|ge|md|al|az|am|kz|kg|tj|tm|uz|mn|pk|bd|lk|np|af|kh|la|mm|th|sg|ph|my|id|vn|kr|jp|cn|tw|hk|mo|au|nz|pg|fj|sb|vu|nc|pf|ws|to|tv|ki|nr|fm|mh|pw|gu|mp|as|ck|nu|tk|wf|yt|re|pm|tf|bl|mf|gp|mq|gf|sr|an|cw|sx|bq|aw|ai|ag|dm|gd|lc|ms|kn|vc|bb|tt|jm|bs|ky|vg|bm|tc|ai|gi|im|je|gg|fo|gl|sj|bv|hm|tf|aq|io|sh|ac|cv|st|sc|sd|so|ss|tz|ug|zm|zw|ao|bj|bw|bf|bi|cm|cv|cf|td|km|cg|cd|dj|gq|er|et|ga|gm|gh|gn|gw|ci|ke|ls|lr|ly|mg|mw|ml|mr|mu|yt|ma|mz|na|ne|ng|rw|sh|st|sn|sc|sl|so|za|ss|sd|sz|tz|tg|tn|ug|eh|zm|zw)"
        # extra = re.findall(
        #     rf'(?:http[s]?://|www\.)[a-zA-Z0-9\./]+|[a-zA-Z0-9\./]+\.{tld_pattern}/[^\s，。；、,.;:!?()\[\]{{}}<>"]*',
        #     full_text
        # )
        # for url in extra:
        #     links.append(url.rstrip('；。；，,."\]'))

        seen = set()
        unique = []
        for url in links:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique

    @staticmethod
    def remove_prefix_urls(url_list: list) -> list:
        """删除那些严格作为其他 URL 前缀存在的"冗余"短链接。"""
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
        按照 replacements 字典，对 URL 进行子串替换，并打印替换日志；
        并清理末尾多余的右括号。
        """
        new_urls = []
        for url in urls:
            updated = url
            # 先做映射替换
            for src, tgt in self.replacements.items():
                if src in updated:
                    original = updated
                    updated = updated.replace(src, tgt)
                    # print(f"[替换] {original} -> {updated}")

            # 清理末尾多余的右括号
            if updated.endswith(")"):
                cleaned = updated.rstrip(")")
                # print(f"[清理] 去除末尾括号: {updated} -> {cleaned}")
                updated = cleaned

            new_urls.append(updated)
        return new_urls
    
    def run(self) -> List[Dict[str, Any]]:
        papers_data = []

        for root, _, files in os.walk(self.pdf_root_dir):
            for fn in files:
                if not fn.lower().endswith(".pdf"):
                    continue

                pdf_path = os.path.join(root, fn)
                try:
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                except Exception as e:
                    print(f"[错误] 读取 PDF 失败 {pdf_path}: {e}")
                    continue

                try:
                    # 从 PDF 中提取论文名和链接
                    # fn (文件名) 被传递给 extract_paper_name_and_links 用于备用 paper_name
                    paper_info = self.extract_paper_name_and_links(pdf_bytes, fn)
                    
                    # 对提取出的链接进行处理
                    processed_links = self.remove_prefix_urls(paper_info["extracted_links"])
                    processed_links = self.filter_urls(processed_links)
                    processed_links = self.apply_replacements(processed_links)
                    
                    if processed_links: # 只添加包含有效链接的论文条目
                        papers_data.append({
                            "paper_name": paper_info["paper_name"],
                            "extracted_links": processed_links
                        })
                        
                except Exception as proc_e:
                    print(f"[错误] 处理 PDF 时出错 {pdf_path}: {proc_e}")
                    continue
        
        if self.output_file: # 简单保留写入，但格式可能不符合预期
            try:
                output_dir = os.path.dirname(self.output_file)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                with open(self.output_file, "w", encoding="utf-8") as out_f:
                    if self.flatten: # 如果 flatten 仍然为 True，则展平所有链接并去重
                        all_links_flat = set()
                        for paper in papers_data:
                            all_links_flat.update(paper["extracted_links"])
                        for url in sorted(list(all_links_flat)):
                            out_f.write(f"{url}\\n")
                    else: # 否则，尝试写入一种结构化的表示（可能不是用户最终要的 JSON）
                        for paper in papers_data:
                            out_f.write(f"Paper: {paper['paper_name']}\\n")
                            for link in paper['extracted_links']:
                                out_f.write(f"  - {link}\\n")
                            out_f.write("\\n")
                print(f"[信息] PDFparser 提取（和可能的文本输出）已完成。输出文件: {self.output_file} (注意：此文件的格式可能与最终JSON不同)")
            except Exception as e:
                print(f"[错误] PDFparser 写入旧格式输出文件时出错: {e}")

        print(f"[信息] PdfLinkExtractor 完成，处理了 {len(papers_data)} 个包含链接的PDF文档。")
        return papers_data

if __name__ == "__main__":
    from utils import load_config
    config = load_config("config.yaml")

    extractor = PdfLinkExtractor(
        pdf_root_dir = config["scraper"]["pdf_dir"], 
        output_file = config["PDFparser"]["output_path"],
        flatten= config["PDFparser"]["flatten"],
        skip_domains=config["PDFparser"]["skip_domains"],
        replacements=config["PDFparser"]["replacements"]
    )
    extractor.run()

