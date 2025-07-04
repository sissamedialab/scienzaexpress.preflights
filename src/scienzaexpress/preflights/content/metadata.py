from plone.dexterity.content import Item
from plone.supermodel import model
from z3c.form.validator import SimpleFieldValidator
from zope.interface import implementer
from zope.interface import Invalid

import logging
import re


logger = logging.getLogger(__name__)


class ValidateISBN(SimpleFieldValidator):
    """
    Validate ISBN.

    Accept only ISBN-13 values starting with Scienza Express' 979-12-80068
    - ...                 979-12-80068-56-9
    - Raccontare il meteo 978-88-96973-04-2
    """

    def validate(self, value: str) -> None:
        super().validate(value)

        isbn = value.replace("-", "").replace(" ", "")  # remove hyphens and spaces

        if not re.fullmatch(r"\d{13}", isbn):
            msg = "L'ISBN dovrebbe avere 13 caratteri ed iniziare con 978 o 979."
            raise Invalid(msg)

        # ISBN-13 validation
        total = sum((int(x) * (1 if i % 2 == 0 else 3)) for i, x in enumerate(isbn))
        if total % 10 != 0:
            msg = "Verfifica ISBN-13 fallita."
            raise Invalid(msg)

        good_ones = {"97912", "97888"}
        if not isbn[:6] not in good_ones:
            msg = f"Gli ISBN di SE iniziano con {'o '.join(good_ones)}"
            raise Invalid(msg)

        return True


class ValidateEven(SimpleFieldValidator):
    """
    Validate even numbers.

    Used, for instance, to validate the number of pages.
    """

    def validate(self, value: int) -> None:
        super().validate(value)

        if value % 2 != 0:
            msg = "Il numero deve essere pari."
            raise Invalid(msg)

        return True


class IMetadata(model.Schema):
    """Marker interface for Metadata."""

    model.load("metadata.xml")


@implementer(IMetadata)
class Metadata(Item):
    """Metadata for RISE types."""


# constraint=future_date,
