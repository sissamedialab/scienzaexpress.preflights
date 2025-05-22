from dataclasses import dataclass
from datetime import datetime
from lxml import etree
from plone import api
from plone.dexterity.interfaces import IDexterityItem
from plone.namedfile.file import NamedBlobFile
from Products.Five.browser import BrowserView
from scienzaexpress.preflights.views.validate_pdf_metadata import (
    missing_metadata_message,
)
from scienzaexpress.preflights.views.validate_pdf_metadata import ValidatePdfMetadata
from zope.interface import implementer
from zope.interface import Interface
from zope.lifecycleevent import modified


# TODO: transfer to Plone registry
SEND_NAME: str = "Scienza Express"
SEND_MAIL: str = "info@scienzaexpress.it"
RCRD_CODE: str = "it.scienzaexpress."
RCRD_NAME: str = "Scienza Express"
ISBN_TYPE: str = "15"
ISSN_TYPE: str = "02"
PRNT_STAT: str = "IT"
DFLT_FORM: str = "BA"
MEAS_UNIT: str = "mm"
LANG_CODE: str = "ita"
PUBL_NAME: str = "Scienza Express"
PUBL_STAT: str = "IT"
SUPL_NAME: str = "Scienza Express"
SUPL_CURR: str = "EUR"


@dataclass
class BookMetadata:
    # P.1, P.2
    isbn: str
    # P.3
    type: str
    measures: list[str]  # H x L x T (mm)
    # P.5
    collection_title: str
    collection_issn: str
    # P.6
    title: str
    orig_title: str
    subtitle: str
    # P.7
    authors: list[str]
    bios: list[str]
    illustrators: list[str]
    translators: list[str]
    curators: list[str]
    # P.9
    ed_number: str
    # P.10
    orig_lang: str
    # P.11
    pages: str
    # P.12
    thema_keys: list[str]
    # P.14
    abstract: str
    # P.20
    pub_city: str
    pub_date: str
    # P.26
    price: str
    price_tax: str

    def validate_translation(self) -> tuple[bool, list[str] | None]:
        if len(self.translators) > 0:
            if self.orig_lang and self.orig_title:
                return (True, None)
            return (
                False,
                [
                    f"Sono stati definiti dei traduttori ({self.translators})."
                    ' Assicurarsi che "lingua originale" e "titolo originale" siano definiti.',
                ],
            )
        return (True, None)

    def validate_collection(self) -> tuple[bool, list[str] | None]:
        """Check if all collection data are present."""
        if self.collection_title:
            if self.collection_issn:
                return (True, None)
            return (False, ['Assicurarsi che "titolo collana" e "issn collana" siano definiti'])
        return (True, None)

    def validate_pages(self) -> tuple[bool, list[str] | None]:
        """Check if pages are number."""
        if not self.pages.isdigit():
            return (False, [f"Assicurarsi che il numero di pagine ({self.pages}) sia un intero."])
        if self.pages[0] == "0":
            return (False, [f"Assicurarsi che il numero di pagine ({self.pages}) sia maggiore di zero."])
        return (True, None)

    def validate_isbn(self) -> tuple[bool, list[str] | None]:
        """Check ISBN 15 format."""
        length = 13
        if len(self.isbn) != length:
            return (False, [f"Assicurarsi che l'ISBN ({self.isbn}) abbia {length} caratteri."])
        if not self.isbn.isdigit():
            return (False, [f"Assicurarsi che l'ISBN ({self.isbn}) sia un intero (no trattini!)."])
        return (True, None)

    def validate_measures(self) -> tuple[bool, list[str] | None]:
        """
        Check if all measures are valid.

        Raises:
            ValueError if there are not exacly 3 measures.

        """
        h_l_t = 3
        if len(self.measures) != h_l_t:
            msg = "Misure scombinate: {self.measures=}. Please check your code!"
            raise ValueError(msg)

        failures = []
        msgs = {
            0: "Assicurarsi che l'altezza ({measure}) sia un intero.",
            1: "Assicurarsi che la larghezza ({measure}) sia un intero.",
            2: "Assicurarsi che lo spessore ({measure}) sia un intero",
        }
        for i, measure in enumerate(self.measures):
            if not measure.isdigit():
                failures.append(msgs[i])
        if failures:
            return (False, "; ".join(failures))
        return (True, None)

    def validate_authors(self) -> tuple[bool, list[str] | None]:
        """Check authors and biographies."""
        if len(self.authors) < 1:
            return (False, [f"Assicurarsi che almeno un autore sia presente ({self.autors})."])
        elif len(self.authors) != len(self.bios):
            return (
                False,
                [
                    f"Assicurarsi che il numero di autori ({len(self.authors)}) e il numero di biografie ({len(self.bios)}) sia uguale."
                ],
            )
        else:
            return (True, None)

    def validate_pubdate(self) -> tuple[bool, list[str] | None]:
        """Check pubdate format."""
        # 🤔 poor-man date validation???
        yyyymm = 6
        december = 12
        if len(self.pub_date) != yyyymm:
            # TODO: I think YYYYMMDD is also ok...
            return (False, [f"Assicurarsi che la data di pubblicazione ({self.pub_date}) abbia il formato YYYYMM."])
        if not self.pub_date.isdigit():
            return (False, [f"Assicurarsi che la data di pubblicazione ({self.pub_date}) sia composta da sole cifre."])
        if int(self.pub_date[-2:]) > december:
            return (
                False,
                [
                    f"Assicurarsi che il mese della data di pubblicazione (ultime due cifre di {self.pub_date})"
                    f" sia minore o uguale a {december}."
                ],
            )
        return (True, None)

    def validate(self) -> tuple[bool, list[str] | None]:
        """
        Validate the metadata.

        Single field values must be of the correct type/format, and the metada must also be coherent as a whole.
        """
        all_valid, reasons_failed = True, []
        for validator in (
            "validate_authors",
            "validate_measures",
            "validate_pubdate",
            "validate_isbn",
            "validate_pages",
            "validate_translation",
            "validate_collection",
        ):
            valid, reason_failed = getattr(self, validator)()
            if not valid:
                all_valid = False
                reasons_failed.extend(reason_failed)
        if not reasons_failed:  # we should return None if there are no failure reasons
            reasons_failed = None
        return (all_valid, reasons_failed)


def generate_onix_message(  # noqa: C901, PLR0912, PLR0914, PLR0915
    book_meta: BookMetadata,
    *,
    is_for_ISBN: bool = True,  # noqa: N803
) -> etree.Element:
    """
    Arrange metadta into an XML tree.

    Args:
        book_meta: the metadata to work with;

        is_for_ISBN: when Ture, the generated tree is suitable to be
        sent to RISE's web app; otherwise the tree is suitable to te
        sent to Onix-related services;

    """
    if is_for_ISBN:
        root = etree.Element(
            "ONIXISBNMessage",
            attrib={"release": "3.1"},
            nsmap={
                None: "http://ns.editeur.org/onix/3.1/reference",
            },
        )
    else:
        root = etree.Element(
            "ONIXMessage",
            attrib={"release": "3.1"},
            nsmap={
                None: "http://ns.editeur.org/onix/3.1/reference",
            },
        )

    # HEADER
    header = etree.SubElement(root, "Header")
    sender = etree.SubElement(header, "Sender")
    etree.SubElement(sender, "SenderName").text = SEND_NAME
    etree.SubElement(sender, "ContactName").text = SEND_NAME
    etree.SubElement(sender, "EmailAddress").text = SEND_MAIL
    etree.SubElement(header, "SentDateTime").text = datetime.utcnow().strftime("%Y%m%d")

    # PRODUCT
    product = etree.SubElement(root, "Product")

    # BLOCK 0: Preamble
    # P.1
    etree.SubElement(product, "RecordReference").text = RCRD_CODE + book_meta.isbn
    etree.SubElement(product, "NotificationType").text = "03"  # List 1
    etree.SubElement(product, "RecordSourceType").text = "01"  # List 44
    etree.SubElement(product, "RecordSourceName").text = RCRD_NAME

    # P.2
    product_id = etree.SubElement(product, "ProductIdentifier")
    etree.SubElement(product_id, "ProductIDType").text = ISBN_TYPE
    etree.SubElement(product_id, "IDValue").text = book_meta.isbn

    # BLOCK 1: Decriptive detail
    # P.3
    descriptive_detail = etree.SubElement(product, "DescriptiveDetail")
    etree.SubElement(descriptive_detail, "ProductComposition").text = "00"  # List 2
    if book_meta.type in {"BB", "BC"}:
        etree.SubElement(descriptive_detail, "ProductForm").text = book_meta.type  # List 150
    else:
        # TO DO Raise warning
        etree.SubElement(descriptive_detail, "ProductForm").text = DFLT_FORM
    for i, m in enumerate(book_meta.measures, start=1):
        measure = etree.Element("Measure")
        etree.SubElement(measure, "MeasureType").text = f"0{i}"
        etree.SubElement(measure, "Measurement").text = m
        etree.SubElement(measure, "MeasureUnitCode").text = MEAS_UNIT
        descriptive_detail.append(measure)
    etree.SubElement(descriptive_detail, "CountryOfManufacture").text = PRNT_STAT

    # P.4
    # Not relevant

    # P.5
    if book_meta.collection_title:
        collection = etree.SubElement(descriptive_detail, "Collection")
        etree.SubElement(collection, "CollectionType").text = "10"  # List 148
        collection_id = etree.SubElement(collection, "CollectionIdentifier")
        etree.SubElement(collection_id, "CollectionIDType").text = "02"
        etree.SubElement(collection_id, "IDValue").text = book_meta.collection_issn
        collection_title = etree.SubElement(collection, "TitleDetail")
        etree.SubElement(collection_title, "TitleType").text = "01"  # List 15
        collection_title_element = etree.SubElement(collection_title, "TitleElement")
        etree.SubElement(collection_title_element, "TitleElementLevel").text = "02"
        etree.SubElement(collection_title_element, "TitleText").text = book_meta.collection_title
    else:
        etree.SubElement(descriptive_detail, "NoCollection")

    # P.6
    title_detail = etree.SubElement(descriptive_detail, "TitleDetail")
    etree.SubElement(title_detail, "TitleType").text = "01"  # List 15
    title_element = etree.SubElement(title_detail, "TitleElement")
    etree.SubElement(title_element, "TitleElementLevel").text = "01"
    etree.SubElement(title_element, "TitleText").text = book_meta.title
    if book_meta.subtitle:
        etree.SubElement(title_element, "Subtitle").text = book_meta.subtitle
    if book_meta.orig_title:
        etree.SubElement(title_detail, "TitleType").text = "16"  # List 15
        title_element = etree.SubElement(title_detail, "TitleElement")
        etree.SubElement(title_element, "TitleElementLevel").text = "01"
        etree.SubElement(title_element, "TitleText").text = book_meta.orig_title

    # P.7
    count_contrib: int = 0
    for i, author in enumerate(book_meta.authors):
        count_contrib = +1
        contributor = etree.Element("Contributor")
        etree.SubElement(contributor, "SequenceNumber").text = f"{count_contrib:02d}"
        etree.SubElement(contributor, "ContributorRole").text = "A01"  # List 17
        etree.SubElement(contributor, "PersonName").text = author
        try:
            bio = book_meta.bios[i]
            if bio:
                etree.SubElement(contributor, "BiographicalNote", attrib={"textformat": "05"}).text = bio
        except IndexError:
            pass
        descriptive_detail.append(contributor)
    for illustrator in book_meta.illustrators:
        count_contrib = +1
        contributor = etree.Element("Contributor")
        etree.SubElement(contributor, "SequenceNumber").text = f"{count_contrib:02d}"
        etree.SubElement(contributor, "ContributorRole").text = "A12"  # List 17
        etree.SubElement(contributor, "PersonName").text = illustrator
        descriptive_detail.append(contributor)
    for translator in book_meta.translators:
        count_contrib = +1
        contributor = etree.Element("Contributor")
        etree.SubElement(contributor, "SequenceNumber").text = f"{count_contrib:02d}"
        etree.SubElement(contributor, "ContributorRole").text = "B06"  # List 17
        etree.SubElement(contributor, "PersonName").text = translator
        descriptive_detail.append(contributor)
    for curator in book_meta.curators:
        count_contrib = +1
        contributor = etree.Element("Contributor")
        etree.SubElement(contributor, "SequenceNumber").text = f"{count_contrib:02d}"
        etree.SubElement(contributor, "ContributorRole").text = "C04"  # List 17
        etree.SubElement(contributor, "PersonName").text = curator
        descriptive_detail.append(contributor)

    # P.8
    # Not relevant

    # P.9
    if book_meta.ed_number:
        etree.SubElement(descriptive_detail, "EditionNumber").text = book_meta.ed_number
    else:
        etree.SubElement(descriptive_detail, "EditionNumber").text = "1"

    # P.10
    language = etree.SubElement(descriptive_detail, "Language")
    etree.SubElement(language, "LanguageRole").text = "01"  # List 22
    etree.SubElement(language, "LanguageCode").text = LANG_CODE
    if book_meta.translators:
        original = etree.SubElement(descriptive_detail, "Language")
        etree.SubElement(original, "LanguageRole").text = "02"  # List 22
        etree.SubElement(original, "LanguageCode").text = book_meta.orig_lang

    # P.11
    extent = etree.SubElement(descriptive_detail, "Extent")
    etree.SubElement(extent, "ExtentType").text = "06"  # List 23
    etree.SubElement(extent, "ExtentValue").text = book_meta.pages
    etree.SubElement(extent, "ExtentUnit").text = "03"  # List 24

    # P.12
    for item in book_meta.thema_keys:
        subject = etree.Element("Subject")
        etree.SubElement(subject, "SubjectSchemeIdentifier").text = "93"  # List 27
        etree.SubElement(subject, "SubjectSchemeVersion").text = "1.1"  # Current version
        etree.SubElement(subject, "SubjectCode").text = item
        descriptive_detail.append(subject)

    # P.13
    # Not relevant (at the moment)

    # BLOCK 2: Collateral detail
    collateral_detail = etree.SubElement(product, "CollateralDetail")

    # P.14
    text_content = etree.SubElement(collateral_detail, "TextContent")
    etree.SubElement(text_content, "TextType").text = "30"  # List 153
    etree.SubElement(text_content, "ContentAudience").text = "00"  # List 153
    etree.SubElement(text_content, "Text", attrib={"textformat": "05"}).text = book_meta.abstract

    # P.15
    # Not relevant

    # P.16
    # Not relevant

    # P.17
    # Not relevant

    # BLOCK 3: Content detail
    # P.18
    # Not relevant

    # BLOCK 4: Publishing detail
    publishing_detail = etree.SubElement(product, "PublishingDetail")

    # P.19
    publisher = etree.SubElement(publishing_detail, "Publisher")
    etree.SubElement(publisher, "PublishingRole").text = "01"  # List 45
    etree.SubElement(publisher, "PublisherName").text = PUBL_NAME
    etree.SubElement(publishing_detail, "CityOfPublication").text = book_meta.pub_city
    etree.SubElement(publishing_detail, "CountryOfPublication").text = PUBL_STAT

    # P.20
    publication_date = etree.SubElement(publishing_detail, "PublishingDate")
    etree.SubElement(publication_date, "PublishingDateRole").text = "01"  # For ISBN purposes
    etree.SubElement(publication_date, "Date").text = book_meta.pub_date  # Format "YYYYMM"

    # P.21
    # Not relevant

    # BLOCK 5: Related material
    # P.22
    # Not relevant

    # P.23
    # Not relevant

    # BLOCK 6: Product supply
    # For ISBN registration must be excluded
    if is_for_ISBN:
        return root

    product_supply = etree.SubElement(product, "ProductSupply")

    # P.24
    # Not relevant

    # P.25
    # Not relevant

    # P.26
    # Not relevant
    supply_detail = etree.SubElement(product_supply, "SupplyDetail")
    supplier_element = etree.SubElement(supply_detail, "Supplier")
    etree.SubElement(supplier_element, "SupplierRole").text = "01"  # List 93
    etree.SubElement(supplier_element, "SupplierName").text = SUPL_NAME
    etree.SubElement(supply_detail, "ProductAvailability").text = "20"
    price_element = etree.SubElement(supply_detail, "Price")
    etree.SubElement(price_element, "PriceType").text = "01"  # List 58
    etree.SubElement(price_element, "PriceAmount").text = book_meta.price
    etree.SubElement(price_element, "CurrencyCode").text = SUPL_CURR
    price_tax_element = etree.SubElement(supply_detail, "Price")
    etree.SubElement(price_tax_element, "PriceType").text = "02"  # List 58
    etree.SubElement(price_tax_element, "PriceAmount").text = book_meta.price_tax
    etree.SubElement(price_tax_element, "CurrencyCode").text = SUPL_CURR

    # TODO: validate the whole tree wrt Onix XSD
    # e.g. #  xmlschema_doc = etree.parse("schemas/ONIX_BookProduct_3.1_reference.xsd")
    # e.g. #  xmlschema = etree.XMLSchema(xmlschema_doc)
    # e.g. #  print(xmlschema.validate(etree.fromstring(xml)))

    return root


class IOnixGenerator(Interface):
    """Marker Interface for IOnixGenerator."""


def ssplit(s: str, separator: str = ";") -> tuple | None:
    """Split a string. Deal with None values."""
    if s is None:
        return []
    return s.split(separator)


@implementer(IOnixGenerator)
class BaseGenerator(BrowserView):
    def __call__(self):
        raise NotImplementedError

    def get_metadata(self) -> tuple[bool, BookMetadata | list[str]]:
        """Return metadata suitable to build an Onix-like or App-ready XML."""
        if pmo := ValidatePdfMetadata.find_metadata_object(self.context):
            # TODO: review this setup: validation functions don't like None-values
            #       maybe I should use empty-strings in the publication-metadata obj?
            #       or maybe I should add a method to publication-metadata class
            book_meta = BookMetadata(
                isbn=pmo.isbn or "",
                measures=[pmo.altezza or "", pmo.larghezza or "", pmo.spessore or ""],
                collection_issn=pmo.collana_issn or "",
                collection_title=pmo.collana or "",
                title=pmo.title or "",
                type=pmo.rilegatura or "",
                subtitle=pmo.sottotitolo or "",
                ed_number=pmo.edizione or "",
                orig_lang=pmo.lingua_originale or "",
                orig_title=pmo.titolo_originale or "",
                authors=ssplit(pmo.autori),
                illustrators=ssplit(pmo.illustratori),
                curators=ssplit(pmo.curatori),
                translators=ssplit(pmo.traduttori),
                bios=ssplit(pmo.biografie, ";;"),
                pages=pmo.pagine or "",
                thema_keys=ssplit(pmo.classificazione),
                abstract=pmo.abstract or "",
                pub_city=pmo.luogo_di_pubblicazione or "",
                pub_date=pmo.data_pubblicazione or "",
                price=pmo.prezzo or "",
                price_tax=pmo.prezzo_con_iva or "",
            )

            validate, reasons_failed = book_meta.validate()
            if validate:
                return (True, book_meta)
            return (False, reasons_failed)
        return (False, [missing_metadata_message])

    def save_xml_file(
        self,
        /,
        xml_tree: etree,
        file_id: str,
        title: str,
        description: str,
        message_warning: str,
        message_success: str,
    ) -> IDexterityItem:
        if file_id in self.context:
            api.content.delete(self.context.get(file_id))
            api.portal.show_message(
                message=message_warning,
                request=self.request,
                type="warning",
            )

        file_obj = api.content.create(
            container=self.context,
            type="File",
            id=file_id,
            title=title,
        )
        file_obj.setDescription(description)
        filename = f"{file_id}.xml"
        data = etree.tostring(xml_tree, encoding="unicode")
        file_obj.file = NamedBlobFile(data=data, filename=filename)
        modified(file_obj)

        api.portal.show_message(
            message=message_success,
            request=self.request,
            type="success",
        )

        return file_obj


class OnixGenerator(BaseGenerator):
    def __call__(self):
        validate, other = self.get_metadata()
        if not validate:
            reasons_failed = other  # 🤮 please refactor me!!!
            api.portal.show_message(
                message="\n".join(reasons_failed),
                request=self.request,
                type="error",
            )
            return self.index()

        book_meta = other  # 🤮 please refactor me!!!
        xml_tree = generate_onix_message(book_meta, is_for_ISBN=False)
        self.xml_obj = self.save_xml_file(
            file_id="xml_isbn",
            title="XML per ISBN",
            xml_tree=xml_tree,
            description="Metadata in formato Onix per ISBN",
            message_warning="XML per ISBN file sovrascritto!",
            message_success="XML per ISBN file generato.",
        )

        return self.context.REQUEST.RESPONSE.redirect(
            # redirect to file causes the file to be downloaded: self.xml_obj.absolute_url(),
            self.context.absolute_url(),
        )


class AppGenerator(BaseGenerator):
    def __call__(self):
        validate, other = self.get_metadata()
        if not validate:
            reasons_failed = other  # 🤮 please refactor me!!!
            api.portal.show_message(
                message="\n".join(reasons_failed),
                request=self.request,
                type="error",
            )
            return self.index()

        book_meta = other  # 🤮 please refactor me!!!
        xml_tree = generate_onix_message(book_meta, is_for_ISBN=True)
        self.xml_obj = self.save_xml_file(
            file_id="xml_app",
            title="App-ready XML",
            xml_tree=xml_tree,
            description="Metadata in formato App-ready",
            message_warning="XML-APP file sovrascritto!",
            message_success="XML-APP file generato.",
        )

        return self.context.REQUEST.RESPONSE.redirect(
            # redirect to file causes the file to be downloaded: self.xml_obj.absolute_url(),
            self.context.absolute_url(),
        )
