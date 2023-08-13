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
    chan_id = forms.CharField(label='chan_id')
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

class AutoRebalanceForm(forms.Form):
    group_id = forms.IntegerField(label="group_id", required=True)
    group_name = forms.CharField(label="group_name", min_length=1, max_length=20, required=False)
    ar_enabled = forms.IntegerField(label='ar_enabled', required=False)	
    ar_target_percent = forms.FloatField(label='ar_target_percent', required=False)	
    ar_time = forms.IntegerField(label='ar_time', required=False)	
    ar_maxfeerate = forms.IntegerField(label='ar_maxfeerate', required=False)	
    ar_outbound_percent = forms.FloatField(label='ar_outbound_percent', required=False)	
    ar_inbound_percent = forms.FloatField(label='ar_inbound_percent', required=False)	
    ar_maxcost_percent = forms.FloatField(label='ar_maxcost_percent', required=False)	
    ar_variance = forms.IntegerField(label='ar_variance', required=False)	
    ar_waitperiod = forms.IntegerField(label='ar_waitperiod', required=False)	
    ar_autopilot = forms.IntegerField(label='ar_autopilot', required=False)	
    ar_apdays = forms.IntegerField(label='ar_apdays', required=False)
    ar_workers = forms.IntegerField(label='ar_workers', required=False)
    ar_update_channels = forms.BooleanField(widget=forms.CheckboxSelectMultiple, required=False)

class AutoFeesForm(AutoRebalanceForm):	
    af_enabled = forms.IntegerField(label='af_enabled', required=False)	
    af_maxrate = forms.IntegerField(label='af_maxrate', required=False)	
    af_minrate = forms.IntegerField(label='af_minrate', required=False)	
    af_increment = forms.IntegerField(label='af_increment', required=False)	
    af_multiplier = forms.IntegerField(label='af_multiplier', required=False)	
    af_failedhtlcs = forms.IntegerField(label='af_failedhtlcs', required=False)	
    af_updatehours = forms.IntegerField(label='af_updatehours', required=False)
    af_lowliqlimit = forms.IntegerField(label='af_lowliqlimit', required=False)
    af_excesslimit = forms.IntegerField(label='af_excesslimit', required=False)

class GUIForm(AutoFeesForm):	
    gui_graphlinks = forms.CharField(label='gui_graphlinks', required=False)	
    gui_netlinks = forms.CharField(label='gui_netlinks', required=False)	

class SettingsForm(GUIForm):	
    lnd_cleanpayments = forms.IntegerField(label='lnd_cleanpayments', required=False)	
    lnd_retentiondays = forms.IntegerField(label='lnd_retentiondays', required=False)	

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
