"""Validate metadata fields."""
from plone.dexterity.interfaces import IDexterityItem
from Products.Five.browser import BrowserView
from zope.interface import implementer
from zope.interface import Interface

import dataclasses


class IMetadataValidator(Interface):
    """Marker interface for metadata validator view."""


@dataclasses.dataclass(frozen=True)
class FieldCheck:
    """Represent the result of checking a single field."""

    field_name: str
    field_label: str
    is_present: bool


@implementer(IMetadataValidator)
class MetadataValidator(BrowserView):
    """Validate that required metadata fields are present."""

    # Fields to check with their human-readable labels
    REQUIRED_FIELDS = {
        "isbn": "ISBN",
        "autori": "Autori",
        "data_pubblicazione": "Data Pubblicazione",
        "luogo_di_pubblicazione": "Luogo di Pubblicazione",
        "abstract": "Abstract",
        "altezza": "Altezza",
        "larghezza": "Larghezza",
        "spessore": "Spessore",
        "rilegatura": "Rilegatura",
        "prezzo_con_iva": "Prezzo di copertina",
    }

    def __call__(self):
        """Execute the view."""
        self.results = self.check_fields()
        return self.index()

    def check_fields(self) -> list[FieldCheck]:
        """Check all required fields and return results."""
        results = []

        for field_name, field_label in self.REQUIRED_FIELDS.items():
            is_present = self._is_field_present(field_name)
            results.append(
                FieldCheck(
                    field_name=field_name,
                    field_label=field_label,
                    is_present=is_present,
                )
            )

        return results

    def _is_field_present(self, field_name: str) -> bool:
        """Check if a field has a non-empty value."""
        if not hasattr(self.context, field_name):
            return False

        value = getattr(self.context, field_name, None)

        # Consider None, empty strings, and empty collections as missing
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False

        return True

    def all_fields_present(self) -> bool:
        """Return True if all required fields are present."""
        return all(check.is_present for check in self.results)
