# Code-Learn-System
Code Learn System is a comprehensive learning platform designed specifically for software engineers at all stages of their careers. Our mission is to provide structured, high-quality educational content that covers the essential topics every developer should master.

## Run locally

Run `python server.py` from this folder, then open http://127.0.0.1:8000.

Home and About are public. Create an account and log in to access Coding Topics and the included lesson pages. The server stores accounts and sessions in a local SQLite database. Linked external learning sites are public.

## GitHub Pages

The static site includes a browser-only portfolio demo. Register and log in with demo credentials to unlock Coding Topics in the interface. Accounts are stored in the current browser and lesson files published by GitHub Pages are public. The Python server enforces session checks on its own lesson URLs.

For public login, run the Python app on an HTTPS host. Set the start command to `python server.py`, set `CODE_LEARN_HOST=0.0.0.0`, and set `CODE_LEARN_DATABASE` to the SQLite file path on a persistent disk. The app reads the host-provided `PORT` and uses secure session cookies in hosted mode.

Put the deployed HTTPS origin in the `learning-server` meta tag in `index.html` and publish the updated GitHub Pages site. Login and Register open their forms on that host. Coding Topics opens there too, where the server checks the login session before serving lessons.

## Free PythonAnywhere hosting

Clone the repository into your PythonAnywhere home directory. In the Web tab, create a free web app with Manual configuration. Set its WSGI file to the following, using your PythonAnywhere username in the path.

```python
import os
import sys

sys.path.insert(0, "/home/YOUR_USERNAME/Code-Learn-System")
os.environ["CODE_LEARN_SECURE_COOKIES"] = "1"

from server import application, initialize
initialize()
```

Reload the web app, open its HTTPS URL, and test Register, Login, and Coding Topics. Use that HTTPS origin for the GitHub Pages configuration above. PythonAnywhere's free web app has a one-month expiry, so renew it from the Web dashboard as needed.
