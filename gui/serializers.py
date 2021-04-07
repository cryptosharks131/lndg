from rest_framework import serializers
from .models import Payments, Invoices, Forwards, Channels, Rebalancer

##FUTURE UPDATE 'exclude' TO 'fields'

class PaymentSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = Payments
        exclude = []

class InvoiceSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
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