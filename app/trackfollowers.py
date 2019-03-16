"""
trackfollowers.py - Track who follows and unfollows a screen_name
"""
__author__ = "Thomas J. Daley, J.D."
__version__ = "0.0.1"

import argparse
import datetime
import json
import twitter

from lib.keys import Keys
from lib.logger import Logger
from lib.progress_bar import ProgressBar

FOLLOWER_FILE  = "../data/{}_followers.json"
REPORT_FILE = "../data/{}_report.json"
CLIENT_FILE = "../data/clients.json"

class FollowerTracker(object):
    """
    Encapsulates our Twitter publisher functions.
    """
    def __init__(self, screen_name:str=None):
        self.my_screen_name = screen_name
        self.logger = Logger.get_logger("nottrcp.tracker")
        self.api = self.connect()
        self.clients = self.load_clients()

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

    def load_clients(self)->list:
        """
        Load list of clients we are monitoring.

        Args:
            None

        Returns:
            (list): List of clients' twitter screen_names.
        """
        client_db = {"clients": []}
        try:
            with open(CLIENT_FILE, "r") as client_file:
                client_db = json.load(client_file)
        except FileNotFoundError:
            self.logger.error("Client file not found: %s", CLIENT_FILE)
        except Exception as e:
            self.logger.exception(e)
        
        clients = self.filter_clients(client_db)

        return clients

    def filter_clients(self, client_db: dict)-> list:
        """
        Filter out inactive or expired clients.

        TODO: Perform screening. For now, just returns list of clients in DB file.

        Args:
            client_db (dict): Client DB loaded from clients.json
        
        Returns:
            (list): List of client Twitter screen_names.
        """
        clients = [client["screen_name"] for client in client_db["clients"]]
        return clients

    def get_followers(self, screen_name:str)-> list:
        """
        Get our follower list.

        Returns:
            (list) List of followers
        """
        followers = self.api.GetFollowerIDs(screen_name=screen_name)

        return followers

    def follower_filename(self, screen_name)->str:
        """
        Generate the name of the follower file for this screen_name.

        Returns:
            (str): Name of follower file.
        """
        return FOLLOWER_FILE.format(screen_name)

    def report_filename(self, screen_name:str)->str:
        """
        Generate the name of the report file for this screen_name.

        Args:
            screen_name (str): Screen name we are processing.

        Returns:
            (str): Name of the report file for this screen_name.
        """
        return REPORT_FILE.format(screen_name)

    def load_followers(self, screen_name)->list:
        """
        Load a list of follower user_ids from the followers file.

        Returns:
            (list): List of previously-saved follower user_ids
        """
        user_filename = self.follower_filename(screen_name)

        try:
            with open(user_filename, "r") as user_file:
                old_followers = json.load(user_file)
        except FileNotFoundError:
            return []
        except Exception as e:
            self.logger.exception(e)
            return None

        return old_followers


    def save_followers(self, followers:list, screen_name)->bool:
        """
        Save list of follower ids to json-encoded file.

        Args:
            followers (list): List of follower user_ids from get_followers()
        
        Returns:
            (bool): True if successful, othwerwise false.
        """
        user_filename = self.follower_filename(screen_name)
        try:
            with open(user_filename, "w") as user_file:
                json.dump(followers, user_file)
        except Exception as e:
            self.logger.exception(e)
            return False

        return True

    def save_compare_report(self, report, screen_name):
        """
        Save the comparison report to a json file for further processing.

        Args:
            report (dict): Contains "added" and "deleted" keys.
            screen_name (str): Screen name being processed.

        Returns:
            (bool): True if successful, otherwise False.
        """
        report_filename = self.report_filename(screen_name)
        try:
            report["screen_name"] = screen_name
            report["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %X")
            with open(report_filename, "w") as report_file:
                json.dump(report, report_file)
        except Exception as e:
            self.logger.exception(e)
            return False

        return True

    def compare_followers(self, followers:list, screen_name)->dict:
        """
        Compare the follower list to our last-saved list of followers. Produces
        a dict with two keys: "added" and "deleted". The value of each key is a list
        of Twitter user_ids.

        Args:
            followers (list): List of follower ids from get_followers()
        
        Returns:
            (dict): Containing two lists of "added" and "deleted" user_ids
        """

        old_followers = self.load_followers(screen_name)
        if old_followers is None:
            return None

        added_followers = []
        for follower in followers:
            if follower not in old_followers:
                added_followers.append(follower)
        
        deleted_followers = []
        for follower in old_followers:
            if follower not in followers:
                deleted_followers.append(follower)

        result = {"added": added_followers, "deleted": deleted_followers}
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
    parser.add_argument("--screen-name", action="store", help="Screen name to track. Default is @nottrcp.")
    parser.add_argument('--status', '-s', action='store_true', default=False, help='Indicates you want a status bar on the screen. Default is no.')
    args = parser.parse_args()
    return args

def main():
    """
    main routine for this app.

    Will get followers, compare them to the last list of followers, update the followers list and create
    a change list.
    """
    options = get_options()

    tracker = FollowerTracker(options.screen_name)
    tracker.logger.info("Started.")
    screen_names = tracker.clients

    if options.status:
        progress_bar = ProgressBar(len(screen_names))
        progress_counter = 0

    for screen_name in screen_names:

        if options.status:
            progress_counter += 1
            progress_bar.update(progress_counter, f'{screen_name:10}')

        followers = tracker.get_followers(screen_name)
        changes = tracker.compare_followers(followers, screen_name)
        tracker.save_followers(followers, screen_name)
        tracker.save_compare_report(changes, screen_name)

        if not options.status:
            tracker.list_followers(changes["added"], "New Followers", screen_name)
            tracker.list_followers(changes["deleted"], "Unfollowed by", screen_name)

    tracker.logger.info("Complete.")

if __name__ == "__main__":
    main()