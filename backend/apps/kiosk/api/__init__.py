from apps.kiosk.api.configs import kiosk_configs_router
from apps.kiosk.api.pages import kiosk_pages_router

routers = [
    ("/kiosk/", kiosk_configs_router),
    ("/pages/kiosk/", kiosk_pages_router),
]
