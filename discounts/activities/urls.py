from django.urls import path

from . import views

app_name = 'activities'

urlpatterns = [
    path('install/', views.install, name='install'),
    path('uninstall/', views.uninstall, name='uninstall'),
    path('discounts_send_to_db/', views.send_to_db, name='send_to_db'),
    path('discounts_calculation/', views.calculation, name='calculation'),
    path('discounts_get_from_db/', views.get_from_db, name='get_from_db'),
]
