from django import forms
from recipes.models.favourite import Favourite


class FavouriteForm(forms.ModelForm):
    """Form for creating/updating a Favourite collection name."""
    name = forms.CharField(
        required=False,
        error_messages={"required": "Title is required."},
        widget=forms.TextInput(
            attrs={
                "class": "form-control save-modal-input",
                "id": "edit-collection-title",
                "required": True,
            }
        ),
    )

    class Meta:
        """Model and field config for favourite collections."""
        model = Favourite
        fields = ["name"]

    def clean_name(self):
        """Normalise and validate the collection title."""
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Title is required.")
        return name

    @classmethod
    def _for_tests(cls, name):
        """Factory to aid testing validation paths without view plumbing."""
        return cls(data={"name": name})
