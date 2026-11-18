"""Lab 16: print an access token for a user, to use with curl.

Lab 87: it signs in at SB_API_URL when that is set (see auth_helper.py).
"""

import sys

from auth_helper import API_URL, login

if __name__ == "__main__":
    print(login(API_URL, sys.argv[1] if len(sys.argv) > 1 else "amina"))
