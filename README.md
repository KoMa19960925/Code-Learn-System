# Code-Learn-System
Code Learn System is a comprehensive learning platform designed specifically for software engineers at all stages of their careers. Our mission is to provide structured, high-quality educational content that covers the essential topics every developer should master.

## Run locally

Run `python server.py` from this folder, then open http://127.0.0.1:8000.

Home and About are public. Create an account and log in to access Coding Topics and the included lesson pages. The server stores accounts and sessions in a local SQLite database. Linked external learning sites are public.

## GitHub Pages

The static site shows Home and About. Registration, login, and protected lessons are available through the Python server above. The GitHub Pages Jekyll build excludes lesson files and the server-side coding template.

For public login, run the Python app on an HTTPS host. Set the start command to `python server.py`, set `CODE_LEARN_HOST=0.0.0.0`, and set `CODE_LEARN_DATABASE` to the SQLite file path on a persistent disk. The app reads the host-provided `PORT` and uses secure session cookies in hosted mode.

Put the deployed HTTPS origin in the `learning-server` meta tag in `index.html` and publish the updated GitHub Pages site. Login and Register open their forms on that host. Coding Topics opens there too, where the server checks the login session before serving lessons.
