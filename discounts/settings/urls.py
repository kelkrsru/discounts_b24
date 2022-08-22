from django.urls import path

from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.index, name='index'),
    # path('export/', views.export_volumes_2_excel)
]
