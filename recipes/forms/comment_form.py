from django import forms
from recipes.models import Comment

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 1, 
                'placeholder': 'Add a comment...', 
                'class': 'form-control rounded-pill px-3',
                'style': 'resize: none; overflow: hidden; min-height: 40px;'
            }),
        }