from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField
from .models import LocalSettings, Payments, PaymentHops, Invoices, Forwards, Channels, Rebalancer, Peers, Onchain, PendingHTLCs, FailedHTLCs

##FUTURE UPDATE 'exclude' TO 'fields'

class PaymentSerializer(serializers.HyperlinkedModelSerializer):
    payment_hash = serializers.ReadOnlyField()
    class Meta:
        model = Payments
        exclude = []

class InvoiceSerializer(serializers.HyperlinkedModelSerializer):
    r_hash = serializers.ReadOnlyField()
    class Meta:
        model = Invoices
        exclude = []

class ForwardSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = Forwards
        exclude = []

class ChannelSerializer(serializers.HyperlinkedModelSerializer):
    chan_id = serializers.ReadOnlyField()
    remote_pubkey = serializers.ReadOnlyField()
    funding_txid = serializers.ReadOnlyField()
    output_index = serializers.ReadOnlyField()
    capacity = serializers.ReadOnlyField()
    local_balance = serializers.ReadOnlyField()
    remote_balance = serializers.ReadOnlyField()
    unsettled_balance = serializers.ReadOnlyField()
    local_commit = serializers.ReadOnlyField()
    local_chan_reserve = serializers.ReadOnlyField()
    initiator = serializers.ReadOnlyField()
    local_base_fee = serializers.ReadOnlyField()
    local_fee_rate = serializers.ReadOnlyField()
    remote_base_fee = serializers.ReadOnlyField()
    remote_fee_rate = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    is_open = serializers.ReadOnlyField()
    class Meta:
        model = Channels
        exclude = []

class RebalancerSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    requested = serializers.ReadOnlyField()
    start = serializers.ReadOnlyField()
    stop = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()
    class Meta:
        model = Rebalancer
        exclude = []

class ConnectPeerSerializer(serializers.Serializer):
    peer_pubkey = serializers.CharField(label='peer_pubkey', max_length=66)
    host = serializers.CharField(label='host', max_length=120)

class OpenChannelSerializer(serializers.Serializer):
    peer_pubkey = serializers.CharField(label='peer_pubkey', max_length=66)
    local_amt = serializers.IntegerField(label='local_amt')
    sat_per_byte = serializers.IntegerField(label='sat_per_btye')

class CloseChannelSerializer(serializers.Serializer):
    chan_id = serializers.IntegerField(label='chan_id')
    target_fee = serializers.IntegerField(label='target_fee')
    force = serializers.BooleanField(default=False)

class AddInvoiceSerializer(serializers.Serializer):
    value = serializers.IntegerField(label='value')

class UpdateAliasSerializer(serializers.Serializer):
    peer_pubkey = serializers.CharField(label='peer_pubkey', max_length=66)

class PeerSerializer(serializers.HyperlinkedModelSerializer):
    pubkey = serializers.ReadOnlyField()
    class Meta:
        model = Peers
        exclude = []

class OnchainSerializer(serializers.HyperlinkedModelSerializer):
    tx_hash = serializers.ReadOnlyField()
    class Meta:
        model = Onchain
        exclude = []

class PaymentHopsSerializer(serializers.HyperlinkedModelSerializer):
    payment_hash = PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = PaymentHops
        exclude = []

class LocalSettingsSerializer(serializers.HyperlinkedModelSerializer):
    key = serializers.ReadOnlyField()
    class Meta:
        model = LocalSettings
        exclude = []

class PendingHTLCSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = PendingHTLCs
        exclude = []

class FailedHTLCSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = FailedHTLCs
        exclude = []