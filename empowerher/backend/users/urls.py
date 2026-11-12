from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    ProfileView,
    LogoutView,
    ChangePasswordView,
    DataExportView,
    DeleteAccountView,
)


urlpatterns = [

    path(
        "register/",
        RegisterView.as_view(),
        name="register"
    ),

    path(
        "login/",
        LoginView.as_view(),
        name="login"
    ),

    path(
        "profile/",
        ProfileView.as_view(),
        name="profile"
    ),

    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password"
    ),

    path(
        "export/",
        DataExportView.as_view(),
        name="data-export"
    ),

    path(
        "delete-account/",
        DeleteAccountView.as_view(),
        name="delete-account"
    ),

    path(
        "logout/",
        LogoutView.as_view(),
        name="logout"
    ),
]