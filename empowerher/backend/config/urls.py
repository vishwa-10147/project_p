
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render


def home(request):
    return render(request, "home.html")


def login_page(request):
    return render(request, "login.html")


def register_page(request):
    return render(request, "register.html")


def about_page(request):
    return render(request, "about.html")


def dashboard_page(request):
    return render(request, "dashboard.html")


def business_validation_page(request):
    return render(request, "business_validation.html")


urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # Website pages
    path("", home, name="home"),
    path("login/", login_page, name="login-page"),
    path("register/", register_page, name="register-page"),
    path("about/", about_page, name="about-page"),
    path("dashboard/", dashboard_page, name="dashboard-page"),

    path(
        "business/validation/",
        business_validation_page,
        name="business-validation-page",
    ),

    # Existing APIs
    path("api/users/", include("users.urls")),
    path("api/business/", include("business.urls")),

    # New Idea Vault API
    path("api/ideas/", include("idea_vault.urls")),
]
