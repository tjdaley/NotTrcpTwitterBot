"""
publish.py - publish tweets.
"""
__author__ = "Thomas J. Daley, J.D."
__version__ = ".0.0.1"

import argparse
from datetime import datetime, timedelta
import re
import time
import twitter
import pandas as pd

from lib.keys import Keys
from lib.logger import Logger
from lib.progress_bar import ProgressBar

TWEET_FILE  = "../data/nottrcp_tweets.csv"

class Publisher(object):
    """
    Encapsulates our Twitter publisher functions.
    """
    def __init__(self):
        self.last_trcp = None
        self.last_tweet = None
        self.screen_name = None
        self.logger = Logger.get_logger()
        self.api = self.connect()

    def connect(self):
        """
        Connect our API to the servers.
        """
        api = twitter.Api(consumer_key=Keys.consumer_key(),
                        consumer_secret=Keys.consumer_secret(),
                        access_token_key=Keys.access_token_key(),
                        access_token_secret=Keys.access_token_secret(),
                        sleep_on_rate_limit=True)

        verified_credentials = api.VerifyCredentials()
        self.screen_name = verified_credentials.screen_name
        self.last_tweet = verified_credentials.status.text
        self.logger.debug("%s last said '%s'", self.screen_name, self.last_tweet)
        return api

    def get_last_trcp(self)-> str:
        """
        Get our history so that we can see the last Tweet we sent.

        Returns (str) Last TRCP tweeted or None
        """
        regexp = r"^TRCP (.*):"
        statuses = self.api.GetUserTimeline(screen_name=self.screen_name)
        for status in statuses:
            match = re.search(regexp, status.text)
            if match:
                last_trcp = match.groups()[0]
                return last_trcp

        return None

    def get_next_trcp(self, last_trcp:str)->str:
        """
        Get the next TRCP to tweet, based on the last TRCP tweeted.
        """
        df = pd.read_csv(TWEET_FILE)
        row_interator = df.iterrows()
        for i, row in row_interator:
            self.logger.debug("row['trcp_num'] = '%s' vs '%s'", row['trcp_num'], last_trcp)
            if row['trcp_num'] == last_trcp:
                break
        self.logger.debug("i = %s; last_trcp = %s", i, last_trcp)
        try:
            next_trcp = df.iloc[[i+1]]
            trcp_text = clean(next_trcp.get("trcp_text").item())
            trcp_num = next_trcp["trcp_num"].item()
            result = "TRCP %s: %s" % (trcp_num, trcp_text)
            return result
        except IndexError as e:
            self.logger.error("No more Tweets to Tweet: %s", e)
        except Exception as e:
            self.logger.error("Error: %s", e)
            self.logger.exception(e)
        
        return None

    def post_status(self, status_text:str):
        """
        Find and transmit the next TRCP.

        Args:
            status_text (str):
                status_text to post.      
        """
        if status_text:
            self.api.PostUpdate(status_text)
            self.logger.info("Posted: %s", status_text)
        else:
            self.logger.info("No status text given.")

def clean(in_str:str)->str:
    """
    Remove or replace characters that may not tweet well.

    See: https://en.wikipedia.org/wiki/List_of_Unicode_characters#Basic_Latin
    """
    replacements = [
        {"search": u'\u2018', "replace": "'"}, 
        {"search": u'\u2019', "replace": "'"},
        {"search": u'\u201B', "replace": "'"},
        {"search": u'\u201C', "replace": '"'},
        {"search": u'\u201D', "replace": '"'},
        {"search": u'\u2032', "replace": "'"},
        {"search": u'\u2033', "replace": '"'},
        {"search": u'\ufffd', "replace": ""}
    ]

    result = "%s" % in_str
    for replacement in replacements:
        result = result.replace(replacement["search"], replacement["replace"])

    return result

def minutes_until_time(future_time:str)->int:
    """
    How many minutes until the given time?

    Args:
        future_time (str): Future time

    Returns:
        (int) Seconds until the time specified.
    """
    # Regex for 24-hour time
    regex = r'^(([0-2]?\d)|(2[0-3])):?([0-5]\d)$'
    matches = re.search(regex, future_time)

    if not matches:
        print("Invalid time (1). Must be 00:00 - 23:59")
        return None

    if matches.lastindex != 4:
        print("Invalid time (2). Must in the format HH:MM using a 24-hour clock. [%s]" % matches.lastindex)
        return None

    hour = int(matches.group(1))
    minute = int(matches.group(4))

    now = datetime.now()
    result = int((timedelta(hours=24) - (now - now.replace(hour=hour, minute=minute, second=0, microsecond=0))).total_seconds() % (24*60*60))
    result = int(result / 60)
    return result

def get_options()->dict:
    """
    Read command line options.
    """
    parser = argparse.ArgumentParser(description="Publish tweets.")
    parser.add_argument('--time', '-t', action='store', help='The 24-hour clock time that SUBSEQUENT tweets should go out.')
    args = parser.parse_args()
    next_time = minutes_until_time(args.time or '09:00')
    return {"time": next_time}

def main():
    """
    main routine for this app.
    """
    options = get_options()
    if not options["time"]:
        exit()

    progress_bar = ProgressBar(24*60 , "Remaining")
    publisher = Publisher()
    next_tweet = (publisher.get_next_trcp(publisher.get_last_trcp()))
    remaining_minutes = options["time"]

    try:
        while next_tweet:
            publisher.post_status(next_tweet)
            while remaining_minutes > 0:
                progress_bar.update(remaining_minutes, "%s min" % str(remaining_minutes))
                time.sleep(60) # Tweet again in 24 hours
                remaining_minutes -= 1
            next_tweet = publisher.get_next_trcp(next_tweet)
            remaining_minutes = 24*60
    except KeyboardInterrupt:
        print("\nGood bye")
        exit()

if __name__ == "__main__":
    main()