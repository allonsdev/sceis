from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('client/', views.client_alerts_view, name='client_alerts'),
    path("churn/", views.client_alerts_view, name="churn_alert_list"),
    path("churn-alerts/add/", views.add_churn_alert, name="add_churn_alert"),
    path("churn-alerts/edit/<int:pk>/", views.edit_churn_alert, name="edit_churn_alert"),
    path('communication/', views.communication_view, name='communication'),
    path('campaigns/', views.campaigns_view, name='campaigns'),
    path('competitors/', views.competitors_view, name='competitors'),
    path('organisation/', views.organisation_view, name='organisation'),
    path('site-visit/', views.site_visit_view, name='site_visit'),
    path('engagement/', views.engagement_view, name='engagement'),
    path('training/', views.training_view, name='training'),
    path('task/', views.task_view, name='task'),
    path("training/add/", views.add_training_program, name="add_training_program"),

    path(
        "training/edit/<int:pk>/",
        views.edit_training_program,
        name="edit_training_program",
    ),
    path("tasks/add/", views.add_task, name="add_task"),
    path("tasks/edit/<int:pk>/", views.edit_task, name="edit_task"),
    path("tasks/", views.task_view, name="tasks"),
    path('logout/', views.logout_view, name='logout'),
    path(
    "training-engagement/add/",
    views.add_training_engagement,
    name="add_training_engagement",
    ),

    path(
        "training-engagement/edit/<int:pk>/",
        views.edit_training_engagement,
        name="edit_training_engagement",
    ),
    path("organizations/add/", views.add_organization, name="add_organization"),

path(
    "organizations/edit/<int:pk>/",
    views.edit_organization,
    name="edit_organization"
)
    
]