from django import forms

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

class AddInvoice(forms.Form):
    value = forms.IntegerField(label='value')