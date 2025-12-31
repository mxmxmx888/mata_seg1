from django.core.files.uploadedfile import SimpleUploadedFile

from recipes.forms.recipe_forms import MAX_IMAGE_UPLOAD_BYTES


def fake_image(name="img.jpg"):
    # Minimal bytes; enough for SimpleUploadedFile usage in tests
    return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/jpeg")


def oversized_image(name="big.jpg"):
    return SimpleUploadedFile(name, b"x" * (MAX_IMAGE_UPLOAD_BYTES + 1), content_type="image/jpeg")


def fake_non_image(name="doc.pdf", content_type="application/pdf"):
    return SimpleUploadedFile(name, b"fake-doc-bytes", content_type=content_type)
