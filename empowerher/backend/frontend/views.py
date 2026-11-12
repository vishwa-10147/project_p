"""
Page views. Each one just renders an HTML template; the page then loads
its data from the backend API (/api/...) in the browser.
"""

from django.shortcuts import render


def page(template):
    """Return a view that renders `template`."""

    def view(request):
        return render(request, template)

    view.__name__ = template.replace(".html", "") + "_page"
    return view
