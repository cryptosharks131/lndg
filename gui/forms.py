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
                (str(obj.chan_id) + ' | ' + obj.alias + ' | ' + str(obj.local_base_fee) + ' | ' + str(obj.local_fee_rate) + ' | ' + str(obj.local_cltv)))

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
    chan_id = forms.IntegerField(label='chan_id')
    target_fee = forms.IntegerField(label='target_fee')
    force = forms.BooleanField(widget=forms.CheckboxSelectMultiple, required=False)

class ConnectPeerForm(forms.Form):
    peer_id = forms.CharField(label='peer_pubkey', max_length=200)

class AddTowerForm(forms.Form):
    tower = forms.CharField(label='tower_pubkey', max_length=200)

class DeleteTowerForm(forms.Form):
    pubkey = forms.CharField(label='tower_pubkey', max_length=66)
    address = forms.CharField(label='tower_address', max_length=134)

class RemoveTowerForm(forms.Form):
    pubkey = forms.CharField(label='tower_pubkey', max_length=66)

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
    new_base_fee = forms.IntegerField(label='new_base_fee', required=False)
    new_fee_rate = forms.IntegerField(label='new_fee_rate', required=False)
    new_cltv = forms.IntegerField(label='new_cltv', required=False)
    target_chans = ChanPolicyModelChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Channels.objects.filter(is_open=1).order_by('-alias'), required=False)
    target_all = forms.BooleanField(widget=forms.CheckboxSelectMultiple, required=False)

class AutoRebalanceForm(forms.Form):
    chan_id = forms.IntegerField(label='chan_id', required=False)
    enabled = forms.IntegerField(label='enabled', required=False)
    target_percent = forms.FloatField(label='target_percent', required=False)
    target_time = forms.IntegerField(label='target_time', required=False)
    fee_rate = forms.IntegerField(label='fee_rate', required=False)
    outbound_percent = forms.FloatField(label='outbound_percent', required=False)
    inbound_percent = forms.FloatField(label='inbound_percent', required=False)
    max_cost = forms.FloatField(label='max_cost', required=False)
    variance = forms.IntegerField(label='variance', required=False)
    wait_period = forms.IntegerField(label='wait_period', required=False)
    autopilot = forms.IntegerField(label='autopilot', required=False)
    autopilotdays = forms.IntegerField(label='autopilotdays', required=False)
    targetallchannels = forms.BooleanField(widget=forms.CheckboxSelectMultiple, required=False)

updates_channel_codes = [
    (0, 'base_fee'),
    (1, 'fee_rate'),
    (2, 'ar_amt_target'),
    (3, 'ar_in_target'),
    (4, 'ar_out_target'),
    (5, 'ar_enabled'),
    (6, 'ar_max_cost'),
    (7, 'channel_state'),
    (8, 'auto_fees'),
    (9, 'cltv'),
    (10, 'min_htlc'),
    (11, 'max_htlc'),
]

class UpdateChannel(forms.Form):
    chan_id = forms.IntegerField(label='chan_id')
    target = forms.IntegerField(label='target')
    update_target = forms.ChoiceField(label='update_target', choices=updates_channel_codes)

class UpdateClosing(forms.Form):
    funding_txid = forms.CharField(label='funding_txid', max_length=64)
    funding_index = forms.IntegerField(label='funding_index')
    target = forms.IntegerField(label='target')

class UpdateKeysend(forms.Form):
    r_hash = forms.CharField(label='r_hash', max_length=64)

class AddAvoid(forms.Form):
    pubkey = forms.CharField(label='avoid_pubkey', max_length=66)
    notes = forms.CharField(label='avoid_notes', max_length=1000, required=False)

class RemoveAvoid(forms.Form):
    pubkey = forms.CharField(label='avoid_pubkey', max_length=66)

class UpdatePending(forms.Form):
    funding_txid = forms.CharField(label='funding_txid', max_length=64)
    output_index = forms.IntegerField(label='output_index')
    target = forms.IntegerField(label='target')
    update_target = forms.ChoiceField(label='update_target', choices=updates_channel_codes)

class UpdateSetting(forms.Form):
    key = forms.CharField(label='setting', max_length=20)
    value = forms.CharField(label='value', max_length=50)

class BatchOpenForm(forms.Form):
    pubkey1 = forms.CharField(label='pubkey1', max_length=66, required=False)
    amt1 = forms.IntegerField(label='amt1', required=False)
    pubkey2 = forms.CharField(label='pubkey2', max_length=66, required=False)
    amt2 = forms.IntegerField(label='amt2', required=False)
    pubkey3 = forms.CharField(label='pubkey3', max_length=66, required=False)
    amt3 = forms.IntegerField(label='amt3', required=False)
    pubkey4 = forms.CharField(label='pubkey4', max_length=66, required=False)
    amt4 = forms.IntegerField(label='amt4', required=False)
    pubkey5 = forms.CharField(label='pubkey5', max_length=66, required=False)
    amt5 = forms.IntegerField(label='amt5', required=False)
    pubkey6 = forms.CharField(label='pubkey6', max_length=66, required=False)
    amt6 = forms.IntegerField(label='amt6', required=False)
    pubkey7 = forms.CharField(label='pubkey7', max_length=66, required=False)
    amt7 = forms.IntegerField(label='amt7', required=False)
    pubkey8 = forms.CharField(label='pubkey8', max_length=66, required=False)
    amt8 = forms.IntegerField(label='amt8', required=False)
    pubkey9 = forms.CharField(label='pubkey9', max_length=66, required=False)
    amt9 = forms.IntegerField(label='amt9', required=False)
    pubkey10 = forms.CharField(label='pubkey10', max_length=66, required=False)
    amt10 = forms.IntegerField(label='amt10', required=False)
    fee_rate = forms.IntegerField(label='fee_rate')
