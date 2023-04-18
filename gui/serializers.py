from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField
from .models import LocalSettings, Payments, PaymentHops, Invoices, Forwards, Channels, Rebalancer, Peers, Onchain, PendingHTLCs, FailedHTLCs, Closures, Resolutions

##FUTURE UPDATE 'exclude' TO 'fields'

class PaymentSerializer(serializers.HyperlinkedModelSerializer):
    payment_hash = serializers.ReadOnlyField()
    class Meta:
        model = Payments
        exclude = []

class InvoiceSerializer(serializers.HyperlinkedModelSerializer):
    r_hash = serializers.ReadOnlyField()
    creation_date = serializers.ReadOnlyField()
    settle_date = serializers.ReadOnlyField()
    value = serializers.ReadOnlyField()
    amt_paid = serializers.ReadOnlyField()
    state = serializers.ReadOnlyField()
    chan_in = serializers.ReadOnlyField()
    chan_in_alias = serializers.ReadOnlyField()
    keysend_preimage = serializers.ReadOnlyField()
    message = serializers.ReadOnlyField()
    sender = serializers.ReadOnlyField()
    sender_alias = serializers.ReadOnlyField()
    index = serializers.ReadOnlyField()
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
    num_updates = serializers.ReadOnlyField()
    local_disabled = serializers.ReadOnlyField()
    remote_disabled = serializers.ReadOnlyField()
    last_update = serializers.ReadOnlyField()
    short_chan_id = serializers.ReadOnlyField()
    total_sent = serializers.ReadOnlyField()
    total_received = serializers.ReadOnlyField()
    private = serializers.ReadOnlyField()
    pending_outbound = serializers.ReadOnlyField()
    pending_inbound = serializers.ReadOnlyField()
    htlc_count = serializers.ReadOnlyField()
    local_cltv = serializers.ReadOnlyField()
    local_min_htlc_msat = serializers.ReadOnlyField()
    local_max_htlc_msat = serializers.ReadOnlyField()
    remote_cltv = serializers.ReadOnlyField()
    remote_min_htlc_msat = serializers.ReadOnlyField()
    remote_max_htlc_msat = serializers.ReadOnlyField()
    alias = serializers.ReadOnlyField()
    fees_updated = serializers.ReadOnlyField()
    ar_max_cost = serializers.IntegerField(required=False)
    ar_amt_target = serializers.IntegerField(required=False)
    ar_out_target = serializers.IntegerField(required=False)
    ar_in_target = serializers.IntegerField(required=False)
    auto_fees = serializers.BooleanField(required=False)
    class Meta:
        model = Channels
        exclude = []

class RebalancerSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    requested = serializers.ReadOnlyField()
    start = serializers.ReadOnlyField()
    stop = serializers.ReadOnlyField()
    fees_paid = serializers.ReadOnlyField()
    payment_hash = serializers.ReadOnlyField()
    class Meta:
        model = Rebalancer
        exclude = []

class ConnectPeerSerializer(serializers.Serializer):
    peer_id = serializers.CharField(label='peer_pubkey', max_length=200)

class OpenChannelSerializer(serializers.Serializer):
    peer_pubkey = serializers.CharField(label='peer_pubkey', max_length=66)
    local_amt = serializers.IntegerField(label='local_amt')
    sat_per_byte = serializers.IntegerField(label='sat_per_btye')

class CloseChannelSerializer(serializers.Serializer):
    chan_id = serializers.CharField(label='chan_id')
    target_fee = serializers.IntegerField(label='target_fee')
    force = serializers.BooleanField(default=False)

class BumpFeeSerializer(serializers.Serializer):
    txid = serializers.CharField(label='txid')
    index = serializers.IntegerField(label='index')
    target_fee = serializers.IntegerField(label='target_fee')
    force = serializers.BooleanField(default=False)

class BroadcastTXSerializer(serializers.Serializer):
    raw_tx = serializers.CharField(label='raw_tx')

class AddInvoiceSerializer(serializers.Serializer):
    value = serializers.IntegerField(label='value')

class UpdateAliasSerializer(serializers.Serializer):
    peer_pubkey = serializers.CharField(label='peer_pubkey', max_length=66)

class UpdateChanPolicy(serializers.Serializer):
    chan_id = serializers.CharField(max_length=20)
    base_fee = serializers.IntegerField(required=False, default=None)
    fee_rate = serializers.IntegerField(required=False, default=None)
    disabled = serializers.IntegerField(required=False, default=None)
    cltv = serializers.IntegerField(required=False, default=None)
    min_htlc = serializers.FloatField(required=False, default=None)
    max_htlc = serializers.FloatField(required=False, default=None)

class NewAddressSerializer(serializers.Serializer):
    legacy = serializers.BooleanField(required=False, default=False)

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

class ClosuresSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = Closures
        exclude = []

class ResolutionsSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = Resolutions
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