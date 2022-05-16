from django import forms

from .models import SettingsPortal


class SettingsPortalForm(forms.ModelForm):
    """Форма Настройки портала"""

    class Meta:
        model = SettingsPortal
        fields = '__all__'
        exclude = ('portal',)
