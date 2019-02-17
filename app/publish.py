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

    def get_last_trcp(self, last_tweet=None)-> str:
        """
        Get our history so that we can see the last Tweet we sent.

        Returns (str) Last TRCP tweeted or None
        """
        regexp = r"^TRCP (.*):"

        if not last_tweet:
            statuses = self.api.GetUserTimeline(screen_name=self.screen_name)
            for status in statuses:
                match = re.search(regexp, status.text)
                if match:
                    last_trcp = match.group(1)
                    return last_trcp
        else:
            match = re.search(regexp, last_tweet)
            if match:
                return match.group(1)

        return None

    def get_next_trcp(self, last_trcp:str)->str:
        """
        Get the next TRCP to tweet, based on the last TRCP tweeted.
        """
        df = pd.read_csv(TWEET_FILE)
        row_interator = df.iterrows()
        for i, row in row_interator:
            self.logger.debug("%s %s = %s", i, last_trcp, row['trcp_num'])
            if row['trcp_num'] == last_trcp:
                break

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
            #self.api.PostUpdate(status_text)
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
    epilog = """
    SOME USE CASES:

    1. Run interactively from a terminal session, publishing a tweet at 9:00 a.m. every day and displaying a status bar:\n\n
           $ python publish.py --status\n\n
    2. Run interactively from a terminal session for debugging purposes. Shows status bar, does not send Tweets:\n\n
           $ python publish.py --status --notweet\n\n
    3. Run from systemd, sending a tweet at 9:30 a.m. every day:\n\n
           $ /usr/bin/python publish.py --time 09:30\n\n
    4. Run from cron, where crontab will handle the scheduling of tweets (the only way to send more or less than one per day):\n\n
           $ /usr/bin/python publish.py --once\n\n
    """
    parser = argparse.ArgumentParser(description="Publish tweets.", epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--time', '-t', action='store', default="09:00", help='The 24-hour clock time that SUBSEQUENT tweets should go out.')
    parser.add_argument('--status', '-s', action='store_true', default=False, help='Indicates you want a status bar on the screen. Default is no.')
    parser.add_argument("--once", action="store_true", default=False, help="Indicates that we should send a Tweet and quit.")
    parser.add_argument("--notweet", action="store_true", default=False, help="Indicates that you want a dry-run...no actual tweeting.")
    args = parser.parse_args()
    next_time = minutes_until_time(args.time or '09:00')
    if args.once:
        next_time = None
    return {"time": next_time, "status_bar": args.status, "once": args.once, "notweet": args.notweet}


def main():
    """
    main routine for this app.

    Will publish a Tweet every 24 hours until there are no more tweets to tweet.
    Note that it reopens and reprocesses the tweet file every day, so it's possible for you to add
    tweets to the end of the file and have them picked up in the future without having to restart the
    program.

    Command line args:
        --time HH:MM . . . . The time of day to post tweets in the future, using a 24-hour clock.
                             Default = 09:00.

        --status . . . . . . If specified, causes a status bar to show how close we are to sending
                             out the next Tweet. Do not specify this flag if running from systemd.

        --once . . . . . . . If specified, will send ONE Tweet and quit. Use this if you are going
                             run this from cron and control the schedule that way.

        --notweet. . . . . . If specified, no tweets will be published. Use this for dry-run testing.
    """
    options = get_options()

    if options["status_bar"]:
        progress_bar = ProgressBar(24*60 , "Remaining")

    publisher = Publisher()
    next_tweet = (publisher.get_next_trcp(publisher.get_last_trcp()))
    remaining_minutes = options["time"] or 0

    try:
        while next_tweet:
            if not options["notweet"]:
                publisher.post_status(next_tweet)
            else:
                print("Would have tweeted:", next_tweet)

            while remaining_minutes > 0:
                if options["status_bar"]:
                    progress_bar.update(remaining_minutes, "%s min" % str(remaining_minutes))
                time.sleep(60) # Update the status bar each minute
                remaining_minutes -= 1
            
            if options["once"]:
                next_tweet = None
            else:
                next_tweet = publisher.get_next_trcp(publisher.get_last_trcp(next_tweet))

            remaining_minutes = 24*60
    except KeyboardInterrupt:
        print("\nGood bye")
        exit()

if __name__ == "__main__":
    main()