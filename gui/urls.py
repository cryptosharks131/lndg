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
router.register(r'peerevents', views.PeerEventsViewSet)
router.register(r'trades', views.TradeSalesViewSet)
router.register(r'feelog', views.FeeLogViewSet)

urlpatterns = [
    path('', views.home, name='home'),
    path('route', views.route, name='route'),
    path('routes', views.routes, name='routes'),
    path('peers', views.peers, name='peers'),
    path('balances', views.balances, name='balances'),
    path('closures', views.closures, name='closures'),
    path('towers', views.towers, name='towers'),
    path('batch', views.batch, name='batch'),
    path('trades', views.trades, name='trades'),
    path('batchopen/', views.batch_open, name='batch-open'),
    path('resolutions', views.resolutions, name='resolutions'),
    path('channel', views.channel, name='channel'),
    path('pending_htlcs', views.pending_htlcs, name='pending-htlcs'),
    path('failed_htlcs', views.failed_htlcs, name='failed-htlcs'),
    path('payments', views.payments, name='payments'),
    path('invoices', views.invoices, name='invoices'),
    path('forwards', views.forwards, name='forwards'),
    path('income', views.income, name='income'),
    path('rebalances', views.rebalances, name='rebalances'),
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
    path('update_settings/', views.update_settings, name='update-settings'),
    path('update_channel/', views.update_channel, name='update-channel'),
    path('update_pending/', views.update_pending, name='update-pending'),
    path('update_setting/', views.update_setting, name='update-setting'),
    path('update_closing/', views.update_closing, name='update-closing'),
    path('update_keysend/', views.update_keysend, name='update-keysend'),
    path('add_avoid/', views.add_avoid, name='add-avoid'),
    path('remove_avoid/', views.remove_avoid, name='remove-avoid'),
    path('get_fees/', views.get_fees, name='get-fees'),
    path('opens/', views.opens, name='opens'),
    path('actions/', views.actions, name='actions'),
    path('fees/', views.fees, name='fees'),
    path('keysends/', views.keysends, name='keysends'),
    path('channels/', views.channels, name='channels'),
    path('autopilot/', views.autopilot, name='autopilot'),
    path('autofees/', views.autofees, name='autofees'),
    path('peerevents', views.peerevents, name='peerevents'),
    path('advanced/', views.advanced, name='advanced'),
    path('logs/', views.logs, name='logs'),
    path('addresses/', views.addresses, name='addresses'),
    path('reset/', views.reset, name='reset'),
    path('api/', include(router.urls), name='api-root'),
    path('api-auth/', include('rest_framework.urls'), name='api-auth'),
    path('api/connectpeer/', views.connect_peer, name='connect-peer'),
    path('api/disconnectpeer/', views.disconnect_peer, name='disconnect-peer'),
    path('api/rebalance_stats/', views.rebalance_stats, name='rebalance-stats'),
    path('api/openchannel/', views.open_channel, name='open-channel'),
    path('api/closechannel/', views.close_channel, name='close-channel'),
    path('api/createinvoice/', views.add_invoice, name='add-invoice'),
    path('api/newaddress/', views.new_address, name='new-address'),
    path('api/updatealias/', views.update_alias, name='update-alias'),
    path('api/getinfo/', views.get_info, name='get-info'),
    path('api/balances/', views.api_balances, name='api-balances'),
    path('api/income/', views.api_income, name='api-income'),
    path('api/pendingchannels/', views.pending_channels, name='pending-channels'),
    path('api/bumpfee/', views.bump_fee, name='bump-fee'),
    path('api/chart/', views.chart, name='chart'),
    path('api/chanpolicy/', views.chan_policy, name='chan-policy'),
    path('api/broadcast_tx/', views.broadcast_tx, name='broadcast-tx'),
    path('api/node_info/', views.node_info, name='node-info'),
    path('api/createtrade/', views.create_trade, name='create-trade'),
    path('api/forwards_summary/', views.forwards_summary, name='forwards-summary'),
    path('api/sign_message/', views.sign_message, name='sign-message'),
    path('api/reset/', views.reset_api, name='reset-api'),
    path('lndg-admin/', admin.site.urls),
]
