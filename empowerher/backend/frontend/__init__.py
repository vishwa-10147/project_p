"""
EmpowerHer frontend: the web pages people see.

- templates/   one HTML file per page (Django templates + plain JavaScript)
- static/      JavaScript and other files served as-is (e.g. paillier.js)
- urls.py      which URL shows which page
- views.py     renders the pages

Pages contain no business logic. Each page loads its data from the backend
REST API in ../apps/ with JavaScript (fetch), using the login token.
"""
