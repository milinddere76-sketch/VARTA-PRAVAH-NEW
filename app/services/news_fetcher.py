import requests
from app import config

class NewsFetcher:
    def __init__(self):
        self.api_key = config.NEWS_API_KEY

    def fetch_category_headlines(self, query, rss_query):
        """Fetches headlines for a specific category using NewsAPI with Google News RSS fallback."""
        headlines = []
        # 1. Primary: NewsAPI
        if self.api_key:
            try:
                url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&apiKey={self.api_key}"
                res = requests.get(url, timeout=10)
                articles = res.json().get("articles", [])[:5]
                for a in articles:
                    title = a.get("title", "")
                    if " - " in title:
                        title = title.split(" - ")[0]
                    if title:
                        headlines.append(title)
            except Exception:
                pass
        
        # 2. Fallback: Google News RSS (returns pre-translated clean Marathi)
        try:
            rss_url = f"https://news.google.com/rss/search?q={rss_query}&hl=mr&gl=IN&ceid=IN:mr"
            res_rss = requests.get(rss_url, timeout=10)
            titles = res_rss.text.split("<title>")[2:12]
            for t in titles:
                clean_t = t.split("</title>")[0]
                if clean_t:
                    headlines.append(clean_t)
        except Exception:
            pass
            
        return list(set(headlines))[:6]

    def fetch_all_categories(self):
        """Fetches news across all required domains: Regional, National, World, and Sports."""
        print("📰 [NEWS-FETCHER] Gathering Regional, National, World, and Sports headlines...")
        all_headlines = []
        
        # Category 1: Regional (Maharashtra)
        all_headlines.extend(self.fetch_category_headlines("Maharashtra", "Maharashtra"))
        
        # Category 2: National (India)
        all_headlines.extend(self.fetch_category_headlines("India National News", "India National"))
        
        # Category 3: World (International)
        all_headlines.extend(self.fetch_category_headlines("World News International", "World International"))
        
        # Category 4: Sports (India & World)
        all_headlines.extend(self.fetch_category_headlines("Sports Khel Cricket", "sports khel cricket"))
        
        # De-duplicate while preserving order
        unique_headlines = []
        for h in all_headlines:
            if h not in unique_headlines:
                unique_headlines.append(h)
                
        print(f"✅ [NEWS-FETCHER] Retrieved total pool of {len(unique_headlines)} headlines across all categories.")
        return unique_headlines[:25]

def fetch_news():
    fetcher = NewsFetcher()
    return fetcher.fetch_all_categories()
