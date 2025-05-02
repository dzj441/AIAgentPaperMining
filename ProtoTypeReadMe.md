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

## scraper  

- get_paper_links_via_api
    通过API获取论文链接，因为无法百分百从网页url中提取出API格式。作为一个扩展功能，它可以配合 LLM/Agent 由LLM Agent 组装API 而由这个函数来执行pdf的下载。
- get_paper_links_via_selenium  
    通过selenium动态渲染网页，提取其中的paper_id，目前在iclr 25 poster oral spotlight上都测试过，翻页逻辑锚定页面上的右翻页符，对于只有一页的情况，直接当前页所有的paper_id，在`https://openreview.net/group?id=MICCAI.org/2024/Challenge/FLARE&referrer=%5BHomepage%5D(%2F)#tab-accept-with-minor-revisions`上测试过。会将 所有的paperid 保存到一个json文件中，以便与下载逻辑分离。
- scraper_main
    从命令行读取参数，主要是一个url列表，pdf输出目录 和 json保存目录。