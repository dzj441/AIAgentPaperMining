import os
import re
import pymupdf
from typing import List

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

        # # regex
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
    
    def run(self) -> List[str]:
        # 始终初始化一个集合来收集所有处理过的 URL，无论 flatten 如何设置
        processed_urls = set()

        # 文件写入逻辑保持不变
        try:
            # 尝试创建输出目录 (如果需要)
            output_dir = os.path.dirname(self.output_file)
            if output_dir:
                 os.makedirs(output_dir, exist_ok=True)
                 
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
                            print(f"[错误] 读取 PDF 失败 {pdf_path}: {e}")
                            continue

                        # 提取和处理链接
                        try:
                            links = self.extract_text_and_links(pdf_bytes)
                            links = self.remove_prefix_urls(links)
                            links = self.filter_urls(links)
                            links = self.apply_replacements(links)
                        except Exception as proc_e:
                             print(f"[错误] 处理 PDF 时出错 {pdf_path}: {proc_e}")
                             continue # 跳过处理失败的 PDF

                        # 将当前 PDF 处理后的链接添加到总集合中
                        processed_urls.update(links)

                        # 根据 flatten 选项写入文件
                        if not self.flatten:
                            out_f.write(f"{fn}:\n")
                            for url in links: # 写入当前文件的链接
                                out_f.write(f"  {url}\n")
                            out_f.write("\n")

                # 如果是 flatten 模式，在最后写入所有去重链接
                if self.flatten:
                    for url in sorted(processed_urls):
                        out_f.write(f"{url}\n")
            
            print(f"[信息] 提取的链接已写入文件: {self.output_file}")

        except OSError as e:
            print(f"[错误] 无法写入输出文件 {self.output_file}: {e}")
            # 即使写入失败，也尝试返回已处理的 URL
        except Exception as e_outer:
             print(f"[错误] PdfLinkExtractor 运行时发生意外错误: {e_outer}")
             # 返回空的或部分结果

        # 无论文件写入是否成功，都返回收集到的所有处理过的、去重的 URL 列表
        final_url_list = sorted(list(processed_urls))
        print(f"[信息] PdfLinkExtractor 完成，共找到 {len(final_url_list)} 个唯一链接。")
        return final_url_list

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

