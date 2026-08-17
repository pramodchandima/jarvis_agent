import urllib.request
import urllib.parse
import json
import sqlite3
import re

def clean_html(text):
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&#x27;', "'").replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
    return text.strip()

def run():
    query = ""
    try:
        # Connect to jarvis database to check the last user message
        conn = sqlite3.connect("jarvis.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM conversations WHERE role='user' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        user_msg = row[0] if row else ""
        if user_msg:
            # Strip common conversational phrases to form a clean search query
            cleaned = re.sub(r'[^\w\s]', '', user_msg).lower()
            words = cleaned.split()
            stop_words = {
                "jarvis", "sir", "search", "google", "web", "internet", "for", "about", 
                "tell", "me", "what", "is", "who", "was", "find", "lookup", "online",
                "can", "you", "please", "query", "do", "know", "anything", "information"
            }
            query_words = [w for w in words if w not in stop_words]
            if query_words:
                query = " ".join(query_words)
            else:
                query = user_msg # Fallback to original message
    except Exception:
        pass

    if not query:
        return "Error: Could not retrieve a valid search query from your request."

    try:
        # Perform DuckDuckGo Lite search request using POST data
        post_data = urllib.parse.urlencode({'q': query}).encode('utf-8')
        req = urllib.request.Request(
            'https://lite.duckduckgo.com/lite/', 
            data=post_data, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        )
        
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Extract links, titles and snippets
            links_and_titles = re.findall(r'<a[^>]+class=["\']result-link["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL)
            snippets = re.findall(r'<td[^>]+class=["\']result-snippet["\'][^>]*>(.*?)</td>', html, re.DOTALL)
            
            if not links_and_titles:
                return f"No search results found on the internet for query: '{query}'"
                
            search_results = []
            max_results = min(len(links_and_titles), len(snippets), 4) # Extract top 4 results
            
            for i in range(max_results):
                url, raw_title = links_and_titles[i]
                raw_snippet = snippets[i]
                
                title = clean_html(raw_title)
                snippet = clean_html(raw_snippet)
                
                # Unquote URL if needed (DuckDuckGo links are sometimes wrapped in redirects)
                if "/l/?kh=-1&uddg=" in url:
                    parsed_url = urllib.parse.urlparse(url)
                    qs = urllib.parse.parse_qs(parsed_url.query)
                    url = qs.get("uddg", [url])[0]
                
                search_results.append(f"[{i+1}] Title: {title}\nURL: {url}\nSnippet: {snippet}\n")
                
            return f"Web search results for '{query}':\n\n" + "\n".join(search_results)
            
    except Exception as e:
        return f"Failed to perform internet search for '{query}': {e}"
