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
                articles = res.json().get("articles", [])[:10]
                from datetime import datetime
                for a in articles:
                    title = a.get("title", "")
                    published_at = a.get("publishedAt", "")
                    
                    # STRICT AGE LIMIT: Max 3 days old (259200 seconds)
                    if published_at:
                        try:
                            pub_date = datetime.strptime(published_at[:19], "%Y-%m-%dT%H:%M:%S")
                            if (datetime.now() - pub_date).days > 3:
                                print(f"⏳ [NEWS-FETCHER] Skipping stale article (>3 days old): {title[:50]}")
                                continue
                        except Exception:
                            pass

                    if " - " in title:
                        title = title.split(" - ")[0]
                    if title:
                        headlines.append(title)
            except Exception:
                pass
        
        # 2. Fallback: Google News RSS (returns pre-translated clean Hindi)
        try:
            rss_url = f"https://news.google.com/rss/search?q={rss_query}&hl=hi&gl=IN&ceid=IN:hi"
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
        """Fetches news across all required domains, including regional, opposition, national, world, and sports, interleaving them for a balanced mix."""
        print("📰 [NEWS-FETCHER] Gathering Regional, Opposition, National, World, and Sports headlines...")
        
        categories = {
            "regional": self.fetch_category_headlines("India regional news", "भारत प्रादेशिक"),
            "opposition": self.fetch_category_headlines("India opposition politics Congress Rahul Gandhi AAP", "भारत विपक्ष राजनीति कांग्रेस"),
            "national": self.fetch_category_headlines("India National News Government", "भारत राष्ट्रीय"),
            "world": self.fetch_category_headlines("World News International", "अंतरराष्ट्रीय"),
            "sports": self.fetch_category_headlines("Sports Khel Cricket", "खेल समाचार")
        }
        
        # Interleave the categories to ensure a balanced mix of news
        interleaved_headlines = []
        lists = [categories[k] for k in ["regional", "opposition", "national", "world", "sports"]]
        max_len = max(len(lst) for lst in lists) if lists else 0
        
        for i in range(max_len):
            for lst in lists:
                if i < len(lst):
                    headline = lst[i]
                    if headline not in interleaved_headlines:
                        interleaved_headlines.append(headline)
                        
        print(f"✅ [NEWS-FETCHER] Retrieved total pool of {len(interleaved_headlines)} headlines across all categories (interleaved).")
        return interleaved_headlines[:25]

def fetch_news():
    fetcher = NewsFetcher()
    return fetcher.fetch_all_categories()
