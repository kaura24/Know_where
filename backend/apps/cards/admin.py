from django.contrib import admin

from .models import Card, CardTag, Tag

admin.site.register(Card)
admin.site.register(Tag)
admin.site.register(CardTag)
