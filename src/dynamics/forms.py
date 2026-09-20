from django import forms
from django.utils.translation import gettext_lazy as _


class ToggleSpringForm(forms.Form):
    p_length = forms.FloatField(label=_('P length [mm]'))
    p_angle_deg = forms.FloatField(label=_('P angle [deg]'))

    w_length = forms.FloatField(label=_('W length [mm]'))
    w_angle_deg = forms.FloatField(label=_('W angle [deg]'))
    weight_force = forms.FloatField(label=_('Weight [N]'))

    t_length = forms.FloatField(label=_('T length [mm]'))
    t_angle_deg = forms.FloatField(label=_('T angle [deg]'))
    u_length = forms.FloatField(label=_('U length [mm]'))
    u_angle_deg = forms.FloatField(label=_('U angle [deg]'))
    spring_rate_1 = forms.FloatField(label=_('Spring rate K1 [N/mm]'))
    free_length = forms.FloatField(label=_('Spring free length [mm]'))
    spring_rate_2 = forms.FloatField(label=_('Spring rate K2 [N/mm]'), required=False, initial=0)
    spring_rate_3 = forms.FloatField(label=_('Spring rate K3 [N/mm]'), required=False, initial=0)
    block_length_1 = forms.FloatField(label=_('Stage 1 length [mm]'), required=False)
    block_length_2 = forms.FloatField(label=_('Stage 2 length [mm]'), required=False)

    friction_force = forms.FloatField(label=_('Friction force [N]'), required=False, initial=0)
    damping_force = forms.FloatField(label=_('Damping force [N]'), required=False, initial=0)
    damping_arm = forms.FloatField(label=_('Damping arm [mm]'), required=False, initial=0)

    reaction_rate = forms.FloatField(label=_('Reaction rate [N/mm]'), required=False, initial=0)
    reaction_preload = forms.FloatField(label=_('Reaction preload [N]'), required=False, initial=0)
    reaction_arm = forms.FloatField(label=_('Reaction arm [mm]'), required=False, initial=0)

    total_travel_deg = forms.FloatField(label=_('Total travel [deg]'))
    steps = forms.IntegerField(label=_('Steps'), required=False, initial=20)

    _zero_default_fields = (
        'spring_rate_2', 'spring_rate_3', 'friction_force',
        'damping_force', 'damping_arm', 'reaction_rate',
        'reaction_preload', 'reaction_arm',
    )

    def clean(self):
        cleaned_data = super().clean()
        for name in self._zero_default_fields:
            if cleaned_data.get(name) is None:
                cleaned_data[name] = 0.0
        return cleaned_data

    def clean_block_length_1(self):
        return self.cleaned_data.get('block_length_1') or -1e9

    def clean_block_length_2(self):
        return self.cleaned_data.get('block_length_2') or -1e9

    def clean_steps(self):
        return self.cleaned_data.get('steps') or 20
