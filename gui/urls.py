from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'payments', views.PaymentsViewSet)
router.register(r'paymenthops', views.PaymentHopsViewSet)
router.register(r'invoices', views.InvoicesViewSet)
router.register(r'forwards', views.ForwardsViewSet)
router.register(r'onchain', views.OnchainViewSet)
router.register(r'peers', views.PeersViewSet)
router.register(r'channels', views.ChannelsViewSet)
router.register(r'rebalancer', views.RebalancerViewSet)
router.register(r'settings', views.LocalSettingsViewSet)
router.register(r'pendinghtlcs', views.PendingHTLCViewSet)
router.register(r'failedhtlcs', views.FailedHTLCViewSet)

urlpatterns = [
    path('', views.home, name='home'),
    path('route', views.route, name='route'),
    path('peers', views.peers, name='peers'),
    path('balances', views.balances, name='balances'),
    path('pending_htlcs', views.pending_htlcs, name='pending-htlcs'),
    path('openchannel/', views.open_channel_form, name='open-channel-form'),
    path('closechannel/', views.close_channel_form, name='close-channel-form'),
    path('connectpeer/', views.connect_peer_form, name='connect-peer-form'),
    path('newaddress/', views.new_address_form, name='new-address-form'),
    path('createinvoice/', views.add_invoice_form, name='add-invoice-form'),
    path('rebalancer/', views.rebalance, name='rebalancer'),
    path('updatechanpolicy/', views.update_chan_policy, name='updatechanpolicy'),
    path('autorebalance/', views.auto_rebalance, name='auto-rebalance'),
    path('ar_target/', views.ar_target, name='ar-target'),
    path('suggested_opens/', views.suggested_opens, name='suggested-opens'),
    path('api/', include(router.urls), name='api-root'),
    path('api/connectpeer/', views.connect_peer, name='connect-peer'),
    path('api/openchannel/', views.open_channel, name='open-channel'),
    path('api/closechannel/', views.close_channel, name='close-channel'),
    path('api/createinvoice/', views.add_invoice, name='add-invoice'),
    path('api/newaddress/', views.new_address, name='new-address'),
    path('api/updatealias/', views.update_alias, name='update-alias'),
]
