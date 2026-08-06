import time
from duckduckgo_search import DDGS
results = DDGS().text("삼성전자 채용", max_results=5)
print(results)
