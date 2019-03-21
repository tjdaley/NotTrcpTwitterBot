"""
trackfollowers.py - Track who follows and unfollows a screen_name
"""
__author__ = "Thomas J. Daley, J.D."
__version__ = "0.0.1"

import argparse
from datetime import datetime
import json
import twitter
import uuid

from lib.clients_db import ClientDb
from lib.keysa import Keys
from lib.logger import Logger
from lib.progress_bar import ProgressBar

FOLLOWER_FILE  = "../data/{}_followers.json"
REPORT_FILE = "../data/{}_report.json"
CLIENT_FILE = "../data/clients.json"
DATE_FORMAT  = "%Y-%m-%d %X"

class FollowerTracker(object):
    """
    Encapsulates our Twitter publisher functions.
    """
    def __init__(self, clients:list):
        """
        Class initializer.

        Args:
            clients (list): List of client screen_names.
        """
        self.my_screen_name = None
        self.logger = Logger.get_logger("nottrcp.tracker")
        self.api = self.connect()
        self.clients = clients

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
        self.my_screen_name = verified_credentials.screen_name
        return api

    def get_followers(self, screen_name:str)-> list:
        """
        Get our follower list.

        Returns:
            (list) List of followers
        """
        followers = self.api.GetFollowerIDs(screen_name=screen_name)

        return followers

    def compare_followers(self, cur_followers:list, old_followers:list)->dict:
        """
        Compare the follower list to our last-saved list of followers. Produces
        a dict with two keys: "added" and "deleted". The value of each key is a list
        of Twitter user_ids.

        Args:
            cur_followers (list): List of current follower user_ids
            old_followers (list): List of follower user_ids from last time we ran.
        
        Returns:
            (dict): Containing two lists of "added" and "deleted" user_ids
        """

        if old_followers is None:
            return None

        added_followers = []
        for follower in cur_followers:
            if follower not in old_followers:
                added_followers.append(follower)
        
        deleted_followers = []
        for follower in old_followers:
            if follower not in cur_followers:
                deleted_followers.append(follower)

        result = {"added": added_followers, "deleted": deleted_followers, "uuid": uuid.uuid3(uuid.NAMESPACE_DNS, "analyzemytweets.com")}
        return result

    def list_followers(self, followers:list, description:str, screen_name:str)->None:
        """
        Print a list of followers to the debug console.

        Args:
            followers (list): List of follower ids from get_followers().
            description (str): Description for this follower list, e.g. "Added", "Unfollowed by"

        Returns:
            None.
        """
        self.logger.info("%s: %s (%s)", screen_name, description, len(followers))
        try:
            for follower in followers:
                user = self.api.GetUser(user_id=follower)
                self.logger.info("%s - %s", user.screen_name, user.name)
        except UnicodeEncodeError as e:
            #self.logger.error(e)
            self.logger.info("%s - %s", user.screen_name, "<UNICODE ENCODE ERROR>")
        except Exception as e:
            self.logger.error(e)
            self.logger.info("%s - %s", user.screen_name, "<UNICODE ENCODE ERROR>")

def get_options()->dict:
    """
    Read command line options.

    Args:
        None.

    Returns:
        (dict): Contains one entry for each command line option.
    """

    parser = argparse.ArgumentParser(description="Track followers.")
    parser.add_argument('--status', '-s', action='store_true', default=False,
                        help='Indicates you want a status bar on the screen. Default is no.')
    parser.add_argument("--nowait", action="store_true", default=False,
                        help='Whether to wait if another process has locked the client database. Default is to wait.')
    args = parser.parse_args()
    return args

def main():
    """
    main routine for this app.

    Will get followers, compare them to the last list of followers, update the followers list and create
    a change list.
    """
    options = get_options()

    client_db = ClientDb(wait=(not options.nowait), process_name=__file__)
    screen_names = client_db.active_clients(client_db.load_clients())
    tracker = FollowerTracker(screen_names)
    tracker.logger.info("Started.")

    if options.status:
        progress_bar = ProgressBar(len(screen_names))
        progress_counter = 0

    for screen_name in screen_names:

        if options.status:
            progress_counter += 1
            progress_bar.update(progress_counter, f'{screen_name:10}')

        cur_followers = tracker.get_followers(screen_name)
        old_followers  = client_db.load_followers(screen_name)
        changes = tracker.compare_followers(cur_followers, old_followers)
        client_db.save_followers(cur_followers, screen_name)
        client_db.save_compare_report(changes, screen_name)

        if not options.status:
            tracker.list_followers(changes["added"], "New Followers", screen_name)
            tracker.list_followers(changes["deleted"], "Unfollowed by", screen_name)

    tracker.logger.info("Complete.")

if __name__ == "__main__":
    main()