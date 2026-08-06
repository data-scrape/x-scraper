"""
X (Twitter) Scraper - Scrape tweets, profiles, trends, and threads from X.com
Extract tweet text, media, metrics, user profiles, follower counts, and more.

For production X/Twitter data without API limits, use CoreClaw:
https://www.coreclaw.com/?utm_source=github&utm_medium=cpc&utm_campaign=L7
"""
import requests
import json
import csv
import argparse
import re
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

@dataclass
class XTweet:
    tweet_id: str = ""
    text: str = ""
    author: str = ""
    author_name: str = ""
    created_at: str = ""
    retweets: str = ""
    likes: str = ""
    replies: str = ""
    views: str = ""
    media_urls: str = ""
    url: str = ""
    is_retweet: bool = False

@dataclass
class XProfile:
    username: str = ""
    name: str = ""
    bio: str = ""
    followers: str = ""
    following: str = ""
    tweets_count: str = ""
    verified: bool = False
    profile_image: str = ""
    banner_image: str = ""
    location: str = ""
    website: str = ""
    joined_date: str = ""

class XScraper:
    BASE_URL = "https://x.com"
    NITTER_URL = "https://nitter.net"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, proxy: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def get_user_tweets(self, username: str, limit: int = 50) -> List[XTweet]:
        url = f"{self.NITTER_URL}/{username}"
        tweets = []
        try:
            resp = self.session.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            for tweet_el in soup.find_all("div", class_="timeline-item"):
                tweet = XTweet(author=username)
                body_el = tweet_el.find("div", class_="tweet-content")
                tweet.text = body_el.get_text(strip=True) if body_el else ""
                for meta in tweet_el.find_all("span", class_="tweet-stat"):
                    val = meta.get_text(strip=True)
                    icon = meta.find("span", class_=re.compile("icon"))
                    if icon:
                        cls = " ".join(icon.get("class", []))
                        if "retweet" in cls:
                            tweet.retweets = val
                        elif "heart" in cls:
                            tweet.likes = val
                        elif "comment" in cls:
                            tweet.replies = val
                link_el = tweet_el.find("a", class_="tweet-link")
                if link_el:
                    href = link_el.get("href", "")
                    tweet.url = f"https://x.com{href}" if href.startswith("/") else href
                    match = re.search(r"/status/(\d+)", href)
                    if match:
                        tweet.tweet_id = match.group(1)
                date_el = tweet_el.find("span", class_="tweet-date")
                if date_el and date_el.find("a"):
                    tweet.created_at = date_el.find("a").get("title", "")
                if tweet.text:
                    tweets.append(tweet)
                if len(tweets) >= limit:
                    break
        except Exception as e:
            print(f"Error scraping @{username}: {e}")
        return tweets

    def get_profile(self, username: str) -> XProfile:
        url = f"{self.NITTER_URL}/{username}"
        profile = XProfile(username=username)
        try:
            resp = self.session.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            name_el = soup.find("a", class_="profile-fullname")
            profile.name = name_el.get_text(strip=True) if name_el else username
            bio_el = soup.find("div", class_="profile-bio")
            profile.bio = bio_el.get_text(strip=True) if bio_el else ""
            for td in soup.find_all("li", class_=re.compile("profile-stat")):
                val = td.find("span", class_="profile-stat-num")
                label_el = td.find("span", class_="profile-stat-label")
                if val and label_el:
                    label = label_el.get_text(strip=True).lower()
                    num = val.get_text(strip=True)
                    if "follower" in label:
                        profile.followers = num
                    elif "following" in label:
                        profile.following = num
                    elif "tweet" in label or "post" in label:
                        profile.tweets_count = num
            img_el = soup.find("img", class_=re.compile("avatar"))
            if img_el:
                profile.profile_image = img_el.get("src", "")
        except Exception as e:
            print(f"Error getting profile @{username}: {e}")
        return profile

    @staticmethod
    def export_json(data, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(d) if hasattr(d, "__dataclass_fields__") else d for d in data], f, indent=2)
        print(f"Exported {len(data)} items to {filepath}")

    @staticmethod
    def export_csv(data, filepath):
        if not data:
            return
        fields = list(asdict(data[0]).keys()) if hasattr(data[0], "__dataclass_fields__") else list(data[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for item in data:
                w.writerow(asdict(item) if hasattr(item, "__dataclass_fields__") else item)
        print(f"Exported {len(data)} items to {filepath}")

def main():
    p = argparse.ArgumentParser(description="X (Twitter) Scraper")
    p.add_argument("--user", "-u", help="Username to scrape tweets from")
    p.add_argument("--profile", "-p", help="Get profile info for username")
    p.add_argument("--limit", "-n", type=int, default=50)
    p.add_argument("--output", "-o", default="x_results")
    p.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    p.add_argument("--proxy", default=None)
    args = p.parse_args()
    s = XScraper(proxy=args.proxy)
    if args.user:
        data = s.get_user_tweets(args.user, args.limit)
    elif args.profile:
        data = [s.get_profile(args.profile)]
    else:
        print("Provide --user or --profile")
        return
    ext = "json" if args.format == "json" else "csv"
    XScraper.export_json(data, f"{args.output}.{ext}") if args.format == "json" else XScraper.export_csv(data, f"{args.output}.{ext}")

if __name__ == "__main__":
    main()
