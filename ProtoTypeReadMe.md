# 文档
## mining pipeline  
挖掘的全流程基于 url。

### OpenReviewScraper
负责网络爬虫，核心函数是：  
```python
def run(self, urls: list):
    """
    对传入的 OpenReview 页面 URL 列表依次执行：
    1. 抓取每个页面的论文论坛链接。
    2. 将每页抓到的链接按子目录写入 JSON 文件。
    3. 下载对应的论文 PDF 并保存到指定目录。
    """
    ...
```
整个`run`函数将各个行为逻辑分离，先通过爬虫将所有pdf链接写入json，再从json读出链接下载pdf到指定目录。它使用了两种方法进行爬虫，一种借用了OpenReview的API，通过对网址进行parse，然后调用API获取论文链接。另一种通过selenium动态渲染网页。动态渲染网页受网络环境影响较大，不稳定，优先使用了API方法。  
- get_paper_links_via_selenium
- get_paper_links_via_api  

### PdfLinkExtractor:
负责从PDF中提取url，核心函数是：
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
整个`run`函数通过直接提取和正则匹配提取所有的url并去重，然后对其进行预筛选，同时对一些连接不上的国外网页替换为其国内镜像，最后输出到指定文件。后续agent判断将以来这份指定文件中的内容。  