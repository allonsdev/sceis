"""
URL configuration for SCEIS project.
"""
from django.contrib import admin
from django.urls import include, path


# Customize Django admin branding
admin.site.site_header = "SCEIS Admin"
admin.site.site_title = "SCEIS Admin Portal"
admin.site.index_title = "SCEIS Management Dashboard"


urlpatterns = [
    path("admin/", admin.site.urls),
    # Main application URLs
    path("", include("app.urls")),
]

