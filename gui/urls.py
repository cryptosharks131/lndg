
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('openchannel/', views.open_channel, name='open-channel'),
    path('closechannel/', views.close_channel, name='close-channel'),
    path('connectpeer/', views.connect_peer, name='connect-peer'),
    path('newaddress/', views.new_address, name='new-address'),
    path('createinvoice/', views.add_invoice, name='add-invoice'),
    path('rebalancer/', views.rebalance, name='rebalancer'),
]
