# filter_links.py
import re
import os
os.environ["DASHSCOPE_API_KEY"] = 'sk-24c8be486fe54cb29d13b79cf1555450' # replaced with your own API
# Optional: import LLM chain if available
try:
    from langchain_community.chat_models.tongyi import ChatTongyi
    from langchain.chains.llm import LLMChain
    from langchain.prompts import PromptTemplate

    llm = ChatTongyi(model_name="qwen-turbo", streaming= False) # can have top_p sampling here by top_p = ?
    prompt = PromptTemplate(
        input_variables=["url"],
        template=(
            "The following URL comes from a research paper. "
            "Does it point to a dataset download page or an official code repository? "
            "Answer YES or NO.\nURL: {url}\nAnswer:"
        )
    )
    chain = prompt | llm
    print("LLM chain loaded successfully.")
except Exception as load_e:
    print(load_e)
    exit(0)
    chain = None

skip_domains = ["openreview.net/pdf", "arxiv.org", "doi.org", "ieee.org", 
                "aclweb.org", "springer.com", "dblp.org"]
# keep_domains = ["github.com", "gitlab.com", "bitbucket.org",
#                 "kaggle.com", "huggingface.co", "zenodo.org",
#                 "figshare.com", "drive.google.com", "dropbox.com",
#                 "paperswithcode.com"]
# needs modification keep_domains
keep_domains = []
keywords = ["dataset", "data", "benchmarks", "download"]
file_exts = [".zip", ".tar", ".gz", ".tgz"]

def is_dataset_or_code_link(url: str) -> bool:
    """Determine if URL likely points to a dataset or code repository."""
    low = url.lower()
    for dom in skip_domains:
        if dom in low:
            return False
    for dom in keep_domains:
        if dom in low:
            return True
    if chain:
        try:
            print(f"chain is dealing with {url} ")
            result = chain.invoke({"url": url})
            print(result)
            res = result.content.strip().lower()
            print("chain has the following answer")
            print(res)
            return res.startswith("yes")
        except Exception as e:
            print(f"chain failed with {e}")
    if any(ext in low for ext in file_exts):
        return True
    if any(kw in low for kw in keywords):
        return True
    return False

if __name__ == "__main__":

    test_urls = [
    "https://github.com/NVlabs/protcomposer",
    "https://github.com/jasonkyuyim/multiflow",
    "https://github.com/aqlaboratory/openfold",
    "https://arxiv.org/abs/2301.12485",
    "https://arxiv.org/",
    ]
    for u in test_urls:
        print(u, "=>", is_dataset_or_code_link(u))


