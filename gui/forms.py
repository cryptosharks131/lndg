from django import forms
from .models import Channels

class RebalancerModelChoiceIterator(forms.models.ModelChoiceIterator):
    def choice(self, obj):
        return (self.field.prepare_value(obj),
                (str(obj.chan_id) + ' | ' + obj.alias + ' | ' + "{:,}".format(obj.local_balance) + ' | ' + obj.remote_pubkey))

class RebalancerModelChoiceField(forms.models.ModelMultipleChoiceField):
    def _get_choices(self):
        if hasattr(self, '_choices'):
            return self._choices
        return RebalancerModelChoiceIterator(self)
    choices = property(_get_choices,  
                       forms.MultipleChoiceField._set_choices)

class ChanPolicyModelChoiceIterator(forms.models.ModelChoiceIterator):
    def choice(self, obj):
        return (self.field.prepare_value(obj),
                (str(obj.chan_id) + ' | ' + obj.alias + ' | ' + str(obj.local_base_fee) + ' | ' + str(obj.local_fee_rate)))

class ChanPolicyModelChoiceField(forms.models.ModelMultipleChoiceField):
    def _get_choices(self):
        if hasattr(self, '_choices'):
            return self._choices
        return ChanPolicyModelChoiceIterator(self)
    choices = property(_get_choices,  
                       forms.MultipleChoiceField._set_choices)

class OpenChannelForm(forms.Form):
    peer_pubkey = forms.CharField(label='peer_pubkey', max_length=66)
    local_amt = forms.IntegerField(label='local_amt')
    sat_per_byte = forms.IntegerField(label='sat_per_btye')

class CloseChannelForm(forms.Form):
    funding_txid = forms.CharField(label='funding_txid', max_length=64)
    output_index = forms.IntegerField(label='output_index')
    target_fee = forms.IntegerField(label='target_fee')
    force = forms.BooleanField(widget=forms.CheckboxSelectMultiple, required=False)

class ConnectPeerForm(forms.Form):
    peer_pubkey = forms.CharField(label='peer_pubkey', max_length=66)
    host = forms.CharField(label='host', max_length=120)

class AddInvoiceForm(forms.Form):
    value = forms.IntegerField(label='value')

class RebalancerForm(forms.ModelForm):
    class Meta:
        model = Channels
        fields = []
    value = forms.IntegerField(label='value')
    fee_limit = forms.IntegerField(label='fee_limit')
    outgoing_chan_ids = RebalancerModelChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Channels.objects.filter(is_open=1, is_active=1).order_by('-local_balance'), required=False)
    last_hop_pubkey = forms.CharField(label='funding_txid', max_length=66, required=False)
    duration = forms.IntegerField(label='duration')

class ChanPolicyForm(forms.ModelForm):
    class Meta:
        model = Channels
        fields = []
    new_base_fee = forms.IntegerField(label='new_base_fee')
    new_fee_rate = forms.IntegerField(label='new_fee_rate')
    target_chans = ChanPolicyModelChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Channels.objects.filter(is_open=1, is_active=1).order_by('-alias'), required=False)
    target_all = forms.BooleanField(widget=forms.CheckboxSelectMultiple, required=False)

class AutoRebalanceForm(forms.Form):
    chan_id = forms.IntegerField(label='chan_id', required=False)
    enabled = forms.IntegerField(label='enabled', required=False)
    target_percent = forms.FloatField(label='target_percent', required=False)
    target_time = forms.IntegerField(label='target_time', required=False)
    fee_rate = forms.IntegerField(label='fee_rate', required=False)
    outbound_percent = forms.FloatField(label='outbound_percent', required=False)
    max_cost = forms.FloatField(label='max_cost', required=False)

class ARTarget(forms.Form):
    chan_id = forms.IntegerField(label='chan_id')
    ar_target = forms.IntegerField(label='ar_target')