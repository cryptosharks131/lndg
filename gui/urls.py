from django.urls import path, include
from rest_framework import routers
from django.contrib import admin
from . import views

router = routers.DefaultRouter()
router.register(r'payments', views.PaymentsViewSet)
router.register(r'paymenthops', views.PaymentHopsViewSet)
router.register(r'invoices', views.InvoicesViewSet)
router.register(r'forwards', views.ForwardsViewSet)
router.register(r'onchain', views.OnchainViewSet)
router.register(r'closures', views.ClosuresViewSet)
router.register(r'resolutions', views.ResolutionsViewSet)
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
    path('closures', views.closures, name='closures'),
    path('towers', views.towers, name='towers'),
    path('batch', views.batch, name='batch'),
    path('batchopen/', views.batch_open, name='batch-open'),
    path('resolutions', views.resolutions, name='resolutions'),
    path('channel', views.channel, name='channel'),
    path('pending_htlcs', views.pending_htlcs, name='pending-htlcs'),
    path('failed_htlcs', views.failed_htlcs, name='failed-htlcs'),
    path('payments', views.payments, name='payments'),
    path('invoices', views.invoices, name='invoices'),
    path('forwards', views.forwards, name='forwards'),
    path('rebalancing', views.rebalancing, name='rebalancing'),
    path('openchannel/', views.open_channel_form, name='open-channel-form'),
    path('closechannel/', views.close_channel_form, name='close-channel-form'),
    path('connectpeer/', views.connect_peer_form, name='connect-peer-form'),
    path('addtower/', views.add_tower_form, name='add-tower-form'),
    path('deletetower/', views.delete_tower_form, name='delete-tower-form'),
    path('removetower/', views.remove_tower_form, name='remove-tower-form'),
    path('newaddress/', views.new_address_form, name='new-address-form'),
    path('createinvoice/', views.add_invoice_form, name='add-invoice-form'),
    path('rebalancer/', views.rebalance, name='rebalancer'),
    path('updatechanpolicy/', views.update_chan_policy, name='updatechanpolicy'),
    path('autorebalance/', views.auto_rebalance, name='auto-rebalance'),
    path('update_channel/', views.update_channel, name='update-channel'),
    path('update_setting/', views.update_setting, name='update-setting'),
    path('opens/', views.opens, name='opens'),
    path('actions/', views.actions, name='actions'),
    path('fees/', views.fees, name='fees'),
    path('keysends/', views.keysends, name='keysends'),
    path('channels/', views.channels, name='channels'),
    path('autopilot/', views.autopilot, name='autopilot'),
    path('autofees/', views.autofees, name='autofees'),
    path('advanced/', views.advanced, name='advanced'),
    path('api/', include(router.urls), name='api-root'),
    path('api-auth/', include('rest_framework.urls'), name='api-auth'),
    path('api/connectpeer/', views.connect_peer, name='connect-peer'),
    path('api/openchannel/', views.open_channel, name='open-channel'),
    path('api/closechannel/', views.close_channel, name='close-channel'),
    path('api/createinvoice/', views.add_invoice, name='add-invoice'),
    path('api/newaddress/', views.new_address, name='new-address'),
    path('api/updatealias/', views.update_alias, name='update-alias'),
    path('api/getinfo/', views.get_info, name='get-info'),
    path('api/balances/', views.api_balances, name='api-balances'),
    path('api/pendingchannels/', views.pending_channels, name='pending-channels'),
    path('lndg-admin/', admin.site.urls),
]