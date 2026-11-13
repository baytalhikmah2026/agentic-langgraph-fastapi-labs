"""Lab 16: print an access token for a user, to use with curl."""

import sys

from auth_helper import login

if __name__ == "__main__":
    print(login("http://127.0.0.1:8000", sys.argv[1] if len(sys.argv) > 1 else "amina"))
