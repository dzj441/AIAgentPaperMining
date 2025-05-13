# 文档
## mining pipeline  

OpenReviewScraper:
```python
def run(self, urls: list):
    """
    对传入的 OpenReview 页面 URL 列表依次执行：
    1. 抓取每个页面的论文论坛链接。
    2. 将每页抓到的链接按子目录写入 JSON 文件。
    3. （可选）下载对应的论文 PDF 并保存到指定目录。
    """
    ...
```
PdfLinkExtractor:
```python
def run(self):
    """
    遍历指定的 PDF 根目录，针对每个 .pdf 文件依次执行：
    
    1. 读取并提取该 PDF 中的所有外部链接。
    2. 去除那些严格作为其他链接前缀的冗余短链接。
    3. 过滤掉位于 skip_domains 列表中的不需要链接。
    4. 按照 replacements 映射，对剩余链接进行批量替换（如将 huggingface.co 替为 hf-mirror.com）。
    5. 根据 flatten 参数决定输出格式：
       - flatten=False：按文件分组，将每个文件的链接写入输出文件。
       - flatten=True：汇总所有链接，去重后扁平化写入输出文件。
    """
    ...
```

TODO：加入urlchecker的部分 有的太离谱的url可以加入skip_domains 里面，skip_domains 的内容也需要仔细验证 是否都需要skip 以及在什么情形下提取出来的。