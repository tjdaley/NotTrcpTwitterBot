"""
keys.py - Our Twitter Keys

Make sure this is NOT synced to GitHub or published in any way.
"""
_KEYS = {
    "CONSUMER_KEY": "hTfejeS6bcou0wxamLhVPNP0a",
    "CONSUMER_SECRET": "rS062erFuzrQ1XnhcFgLa7Q1DetMPFPDOauf9SwV34KGR2ZYZ4",
    "ACCESS_TOKEN_KEY": "1108248262409101312-nwmWrgMeZjJ3bbButOrbrfgzRGAro0",
    "ACCESS_TOKEN_SECRET": "ZCIv5ZXrwq4V2CjH1fCES5BZC4XHFkrv17Eug3w7RXlbj"
}

class Keys(object):
    @staticmethod
    def consumer_key():
        return _KEYS["CONSUMER_KEY"]

    @staticmethod
    def consumer_secret()->str:
        return _KEYS["CONSUMER_SECRET"]
    
    @staticmethod
    def access_token_key()->str:
        return _KEYS["ACCESS_TOKEN_KEY"]
    
    @staticmethod
    def access_token_secret()->str:
        return _KEYS["ACCESS_TOKEN_SECRET"]
