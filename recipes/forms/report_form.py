from django import forms
from recipes.models import Report

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Please provide details...'})
        }