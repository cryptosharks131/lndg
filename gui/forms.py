from django import forms
from .models import Channels

class OpenChannelForm(forms.Form):
    peer_pubkey = forms.CharField(label='peer_pubkey', max_length=66)
    local_amt = forms.IntegerField(label='local_amt')
    sat_per_byte = forms.IntegerField(label='sat_per_btye')

class CloseChannelForm(forms.Form):
    chan_id = forms.CharField(label='chan_id')
    target_fee = forms.IntegerField(label='target_fee', required=False)
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
    outgoing_chan_ids = forms.ModelMultipleChoiceField(queryset=Channels.objects.filter(is_open=1, is_active=1), required=False)
    last_hop_pubkey = forms.CharField(label='funding_txid', max_length=66, required=False)
    duration = forms.IntegerField(label='duration')

class AutoRebalanceForm(forms.Form):	
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
    workers = forms.IntegerField(label='workers', required=False)
    update_channels = forms.BooleanField(widget=forms.CheckboxSelectMultiple, required=False)

class AutoFeesForm(AutoRebalanceForm):	
    af_enabled = forms.IntegerField(label='af_enabled', required=False)	
    af_maxRate = forms.IntegerField(label='af_maxRate', required=False)	
    af_minRate = forms.IntegerField(label='af_minRate', required=False)	
    af_increment = forms.IntegerField(label='af_increment', required=False)	
    af_multiplier = forms.IntegerField(label='af_multiplier', required=False)	
    af_failedHTLCs = forms.IntegerField(label='af_failedHTLCs', required=False)	
    af_updateHours = forms.IntegerField(label='af_updateHours', required=False)
    af_lowliq = forms.IntegerField(label='af_lowliq', required=False)
    af_excess = forms.IntegerField(label='af_excess', required=False)

class GUIForm(AutoFeesForm):	
    gui_graphLinks = forms.CharField(label='gui_graphLinks', required=False)	
    gui_netLinks = forms.CharField(label='gui_netLinks', required=False)	

class LocalSettingsForm(GUIForm):	
    lnd_cleanPayments = forms.IntegerField(label='lnd_cleanPayments', required=False)	
    lnd_retentionDays = forms.IntegerField(label='lnd_retentionDays', required=False)	

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
