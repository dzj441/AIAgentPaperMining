# 文档
目前原型的pipeline流程如下:
1. 使用爬虫爬取pdf存到本地目录 args.pdf_dir
2. 读入pdf，使用pymupdf和正则表达式找到所有的链接，并去重
3. 通过启发式规则和AIAgent判断所有的链接是否为benchmark
4. 将所有结果写入json文件 args.output_path

目前将爬虫逻辑和agent逻辑分离开来了，agent默认会从一个能够爬取所有pdf的dir开始。
爬虫目前基于API 实现，不确定是否符合助教需求，这里可以添加一个亮点，我们可以用Agent来构造网址到API的格式  
目前正在做一个基于selenium的 动态爬虫实现以兼容  输入是conference page的情形，无论如何agent可以通过目前已经提取的pdf进行进一步优化。  
github上的release中有 爬取的ICLR 2025 oral 所有论文的压缩包。  


有关prompt 和 Agent的部分请看 getStarted.md，一些想法也在里面。  
现在需要阅读pdf考虑一下如何把agent的部分做的更细致 如何 找到benchmark。这部分可能涉及到prompt engineering 和 agent的挑选。目前使用的是通义千问。可以在这部分多做尝试

使用git基于分支开发

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