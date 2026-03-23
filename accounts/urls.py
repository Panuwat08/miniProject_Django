from django.urls import path

from . import views


urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin-panel/users/", views.user_management, name="user_management"),
    path("admin-panel/users/create/", views.create_user_account, name="create_user_account"),
    path("admin-panel/users/<int:user_id>/role/", views.update_user_role, name="update_user_role"),
    path("admin-panel/users/<int:user_id>/toggle-active/", views.toggle_user_active, name="toggle_user_active"),
]
