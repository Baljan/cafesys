from .models import Asset, Booking, Theme


from ..baljan.admin import custom_admin_site

custom_admin_site.register(Asset)
custom_admin_site.register(Booking)
custom_admin_site.register(Theme)
