from django import forms
from recipes.models import Report

class ReportForm(forms.ModelForm):
    """Form to submit a report about a recipe or comment."""
    class Meta:
        """Model/field config for reports."""
        model = Report
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Please provide details...'})
        }
