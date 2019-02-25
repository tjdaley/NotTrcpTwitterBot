"""
publish.py - publish tweets.
"""
__author__ = "Thomas J. Daley, J.D."
__version__ = "0.0.1"

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
        Get our history so that we can see the last TRCP-related Tweet we sent.

        This can be called two ways: with or without an argument. The idea is that
        the first time through, we will call this without the last_tweet
        argument. That will result in us searching our timeline to find out what
        we did last.

        Then, if we're processing in a loop (program invoked without the --once flag),
        on subsequent calls to this method, the processing loop will supply the last
        tweet that it sent, which will prevent us from having to search the timeline
        every time.

        NOTE: If you change the format of the text that is published, you may have to
        update the _regexp_ below so that it can parse the preamble of the Tweet properly.

        Returns (str) Last TRCP tweeted or None
        """
        regexp = r"^TRCP ([^:.]*):"

        # If invoked without an argument, go through our timeline, newest to oldest, until we find
        # a Tweet about TRCP, i.e. that matches our regexp.
        if not last_tweet:
            statuses = self.api.GetUserTimeline(screen_name=self.screen_name)
            for status in statuses:
                match = re.search(regexp, status.text)
                if match:
                    last_trcp = match.group(1)
                    return last_trcp

        # Otherwise, just process the argument text.
        match = re.search(regexp, last_tweet)
        if match:
            return match.group(1)

        return None

    def get_next_trcp(self, last_trcp:str)->str:
        """
        Get the next TRCP to tweet, based on the last TRCP tweeted. We reopen and reprocess
        the TWEET_FILE every time. This allows our Tweet generator to add tweets to the file
        or correct upcoming tweets.

        NOTE: If you change the format of the tweet, especially the "TRCP #:" pattern of the
        beginning of the tweet, you may need to change the _regexp_ in get_last_trcp().

        NOTE: This will not work properly for transmitting your first Tweet. I wrote this
        after I had already transmitted a tweet. If there is no last_trcp available, this
        method will fail to produce the FIRST tweet.

        Args:
            last_trcp (str): TRCP number associated with the last tweet we sent.

        Returns:
            (str): The next Tweet to post to Twitter.
        """
        # Read our list of possible tweets into a Pandas dataframe.
        try:
            df = pd.read_csv(TWEET_FILE)
        except UnicodeDecodeError as e:
            self.logger.error("Error reading %s: %s", TWEET_FILE, e)
            with open(TWEET_FILE, "r") as infile:
                text_content = infile.read()
                for i in range(len(text_content)):
                    if ord(text_content[i:i+1]) > 127:
                        self.logger.info("Suspect: %s", text_content[max(0, i-50):min(i+50, len(text_content)-1)])

        # Go through each row of the dataframe looking for a row having the same TRCP
        # number as the last one we posted to Twitter.
        row_interator = df.iterrows()
        for i, row in row_interator:
            if row['trcp_num'] == last_trcp:
                break

        # Now we have the row index of the last tweet we sent. Try to get the NEXT row
        # in the dataframe and use it as our next tweet.
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
        future_time (str): Future time in 24-hour HH:MM format.

    Returns:
        (int) Seconds until the time specified.
        (None) If future_time is in the wrong format.
    """
    # Regex for 24-hour time
    regexp = r'^(([0-2]?\d)|(2[0-3])):?([0-5]\d)$'

    # See if the future_time given to us satisfies the regular expression.
    matches = re.search(regexp, future_time)

    if not matches:
        print("Invalid time (1). Must be 00:00 - 23:59")
        return None

    if matches.lastindex != 4:
        print("Invalid time (2). Must in the format HH:MM using a 24-hour clock. [%s]" % matches.lastindex)
        return None

    # Extract the hour and minute fields.
    hour = int(matches.group(1))
    minute = int(matches.group(4))

    # Figure out how many minutes between now and future_time.
    now = datetime.now()
    seconds_remaining = int((timedelta(hours=24) - (now - now.replace(hour=hour, minute=minute, second=0, microsecond=0))).total_seconds() % (24*60*60))
    minutes_remaining = int(seconds_remaining / 60)
    return minutes_remaining

def get_options()->dict:
    """
    Read command line options.

    Args:
        None.

    Returns:
        (dict): Contains one entry for each command line option.
    """

    # Create an epilog that shows up at the bottom of the usage display, e.g. -h, that
    # shows how to use the command line options in different use cases.
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

    # If the user specifies --time and --once, we'll ignore the --time argument.
    if args.once:
        next_time = None
    
    # Construct and return dictionary of options.
    return {"time": next_time, "status_bar": args.status, "once": args.once, "notweet": args.notweet}


def main():
    """
    main routine for this app.

    Will publish a Tweet every 24 hours until there are no more tweets to tweet.
    Note that it reopens and reprocesses the tweet file every day, so it's possible for you to add
    tweets to the end of the file and have them picked up in the future without having to restart the
    program.

    Command line args:
        --notweet. . . . . . If specified, no tweets will be published. Use this for dry-run testing.

        --once . . . . . . . If specified, will send ONE Tweet and quit. Use this if you are going
                             run this from cron and control the schedule that way.

        --status . . . . . . If specified, causes a status bar to show how close we are to sending
                             out the next Tweet. Do not specify this flag if running from systemd or cron.

        --time HH:MM . . . . The time of day to post tweets in the future, using a 24-hour clock.
                             Default = 09:00.
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