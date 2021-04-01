from django import forms
from .models import Channels

class CustomModelChoiceIterator(forms.models.ModelChoiceIterator):
    def choice(self, obj):
        return (self.field.prepare_value(obj),
                (str(obj.chan_id) + ' | ' + obj.alias + ' | ' + "{:,}".format(obj.local_balance)))

class CustomModelChoiceField(forms.models.ModelMultipleChoiceField):
    def _get_choices(self):
        if hasattr(self, '_choices'):
            return self._choices
        return CustomModelChoiceIterator(self)
    choices = property(_get_choices,  
                       forms.MultipleChoiceField._set_choices)

class OpenChannelForm(forms.Form):
    peer_pubkey = forms.CharField(label='peer_pubkey', max_length=66)
    local_amt = forms.IntegerField(label='local_amt')
    sat_per_byte = forms.IntegerField(label='sat_per_btye')

class CloseChannelForm(forms.Form):
    funding_txid = forms.CharField(label='funding_txid', max_length=64)
    output_index = forms.IntegerField(label='output_index')

class ConnectPeerForm(forms.Form):
    peer_pubkey = forms.CharField(label='funding_txid', max_length=66)
    host = forms.CharField(label='funding_txid', max_length=120)

class AddInvoiceForm(forms.Form):
    value = forms.IntegerField(label='value')

class RebalancerForm(forms.ModelForm):
    class Meta:
        model = Channels
        fields = []
    value = forms.IntegerField(label='value')
    fee_limit = forms.IntegerField(label='fee_limit')
    outgoing_chan_ids = CustomModelChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Channels.objects.filter(is_open=1, is_active=1).order_by('-alias'), blank=True, required=False)
    last_hop_pubkey = forms.CharField(label='funding_txid', max_length=66, required=False)