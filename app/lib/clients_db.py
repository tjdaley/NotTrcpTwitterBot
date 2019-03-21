"""
clients_db.py - Maintain a database of clients we gather information for.
"""
__author__ = "Thomas J. Daley, J.D."
__version__ = "0.0.1"

from datetime import datetime
import json
import socket
import time

from lib.lock import Lock
from lib.logger import Logger

FOLLOWER_FILE  = "../data/{}_followers.json"
REPORT_FILE = "../data/{}_report.json"
CLIENT_FILE = "../data/clients.json"
DATE_FORMAT  = "%Y-%m-%d %X"

class ClientDb(object):
    """
    Encapsulates our Twitter publisher functions.
    """
    def __init__(self, process_name="another process", wait=True):
        """
        Class initializer.

        Args:
            wait (bool): True if we should wait until we can lock the DB.
        """
        self.logger = Logger.get_logger("nottrcp.client_db")
        self.lock = Lock(wait=wait)
        self.lock.lock(process_name=process_name)

    def load_clients(self)->dict:
        """
        Load list of clients we are monitoring.

        Returns:
            (dict): Of clients.
        """
        client_db = {"clients": {}}
        try:
            with open(CLIENT_FILE, "r") as client_file:
                client_db = json.load(client_file)
        except FileNotFoundError:
            self.logger.error("Client file not found: %s", CLIENT_FILE)
        except Exception as e:
            self.logger.exception(e)
        
        return client_db["clients"]

    def merge_clients(self, clients:dict, new_clients:dict)->dict:
        """
        Merge new clients into current clients dict.

        Args:
            clients (dict): From load_clients()
            new_clients (dict): A list of our current followers.
        
        Returns:
            (dict): Merged list of clients with new ones added and un-followers removed.
        """
        merged_clients = {}

        for screen_name, client in clients:
            if screen_name in new_clients:
                merged_clients[screen_name] = client

        for screen_name, client in new_clients:
            if screen_name not in merged_clients:
                merged_clients[screen_name] = client
        
        return merged_clients

    def save_clients(self, clients:dict):
        """
        Save clients to the clients.json file.

        Args:
            clients (dict): key is screen name, value is description of client.
        """
        client_db = {"clients": clients}
        try:
            with open(CLIENT_FILE, "w") as client_file:
                json.dump(client_db, client_file, indent=3)
        except Exception as e:
            self.logger.error(e)
            return False

        return True

    def subscription_ended(self, end_date:str)->bool:
        """
        Determine whether a subscrption has ended based on the end_date given. If the
        end_date is prior to today's date, then the subscription has ended.

        Args:
            end_date (str): Ending date of subscription YYYY-MM-DD
        
        Returns:
            (bool): True if subscription has ended otherwise False
        """
        try:
            dt = datetime.strptime(end_date, "%Y-%m-%d")
            now = datetime.now()
            return dt < now
        except Exception as e:
            self.logger.exception(e)
        
        return False

    def active_clients(self, client_db: dict)-> list:
        """
        Filter out inactive or expired clients.

        Args:
            client_db (dict): Client DB loaded from clients.json
        
        Returns:
            (list): List of client Twitter screen_names.
        """
        clients = [screen_name for screen_name, client in client_db.items() \
                   if client["active"] and not self.subscription_ended(client["subscription_ends"])]
        return clients

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
            report["generated"] = datetime.now().strftime(DATE_FORMAT)
            with open(report_filename, "w") as report_file:
                json.dump(report, report_file)
        except Exception as e:
            self.logger.exception(e)
            return False

        return True
