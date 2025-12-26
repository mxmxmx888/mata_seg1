from django import forms


class MultiFileInput(forms.ClearableFileInput):
    """File input widget that allows multiple file selection."""

    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        """Return a list of uploaded files for this field name."""
        return files.getlist(name)

    def __init__(self, attrs=None):
        """Ensure the widget allows selecting multiple files."""
        attrs = attrs or {}
        attrs.setdefault("multiple", True)
        super().__init__(attrs)


class MultiFileField(forms.FileField):
    """Form field for multiple file uploads using MultiFileInput."""

    widget = MultiFileInput

    def clean(self, data, initial=None):
        """Validate and clean multiple uploaded files."""
        files = data or []
        if not isinstance(files, (list, tuple)):
            files = [files] if files else []

        cleaned = []
        for f in files:
            file_obj = super().to_python(f)
            if file_obj is None:
                continue
            super().validate(file_obj)
            super().run_validators(file_obj)
            cleaned.append(file_obj)

        if self.required and not cleaned and not initial:
            raise forms.ValidationError(self.error_messages["required"], code="required")

        return cleaned
