import time
from .models import SiteVisit

class SiteVisitMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        if request.path.startswith("/admin"):
            return response

        duration = time.time() - start_time

        SiteVisit.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            is_authenticated=request.user.is_authenticated,

            path=request.path,
            view_name=getattr(request.resolver_match, "view_name", ""),
            http_method=request.method,

            duration_seconds=duration,

            ip_address=self.get_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            referrer=request.META.get("HTTP_REFERER", ""),

            utm_source=request.GET.get("utm_source", ""),
            utm_medium=request.GET.get("utm_medium", ""),
            utm_campaign=request.GET.get("utm_campaign", ""),
        )

        return response

    def get_ip(self, request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0]
        return request.META.get("REMOTE_ADDR")