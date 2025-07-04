from pathlib import Path
from plone.dexterity.interfaces import IDexterityItem
from Products.CMFCore.interfaces import ISiteRoot
from Products.Five.browser import BrowserView
from scienzaexpress.preflights.content.metadata import IMetadata
from zope.interface import implementer
from zope.interface import Interface
from zope.schema import getFieldsInOrder

import dataclasses
import plone.api
import string
import subprocess  # noqa: S404
import tempfile


# Unexpected!!!
# Plone's Italian localization does not include the months names,
# i.e. January doesn't translate automagically to Gennaio
# (or, at least, I wasn't able to make it working...).
# I'm not sure how to approach this best, so I'm going with an ugly
# workaround 😢
IT_MONTHS = {
    "January": "Gennaio",
    "February": "Febbraio",
    "March": "Marzo",
    "April": "Aprile",
    "May": "Maggio",
    "June": "Giugno",
    "July": "Luglio",
    "August": "Agosto",
    "September": "Settembre",
    "October": "Ottobre",
    "November": "Novembre",
    "December": "Dicembre",
}


missing_metadata_message = """Metadata non trovati.
Prego assicurarsi che esista un (unico) oggetto di tipo Metadata
in una cartella denominata "XML"
"""


@dataclasses.dataclass(frozen=True)
class Check:
    """
    A check that should be done on a PDF.

    Consists on a page number
    and a (format-ready) string.

    The checker should format the string using a Metadata object as
    "context".

    See examples in ValidatePdfMetadata.checks

    Please also note that string formatting should allow for date-formatting:
    "{:%B}".format(datetime.datetime.now())
    --> "March"
    but I wasn't able to correctly leverage i18n.
    Please see ValidatePdfMetadata._enrich_pmo()
    """

    page: int
    target: str


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """The result of a check."""

    file_obj: IDexterityItem
    target: str
    check: Check
    good: bool = False
    warning: str = ""
    """If any field used in the check was empty, here we should find a warning string."""

    def __str__(self):
        warning_message = f"🟡 {self.warning.replace('\n', '; ')} - " if self.warning else ""
        if self.good:
            return f'{warning_message}🟢 {self.file_obj.file.filename} - found "{self.target}" on page {self.check.page} (searched "{self.check.target}")'
        else:
            return f'{warning_message}🔴 {self.file_obj.file.filename} - no "{self.target}" on page {self.check.page} (searched "{self.check.target}")'


class IValidatePdfMetadata(Interface):
    """Marker Interface for IValidatePdfMetadata"""


@implementer(IValidatePdfMetadata)
class ValidatePdfMetadata(BrowserView):
    """
    Validate a PDF with respect to its metadata.

    We expect to find some strings (targets) on some pages.
    These targets can be parametric wrt a Metadata object.

    See the definition of Check() for details.
    """

    checks = (
        # pg. 1
        Check(page=1, target="{m.collana}"),
        # pg. 3
        Check(page=3, target="{m.autori}"),
        Check(page=3, target="{m.title}"),
        Check(page=3, target="{m.sottotitolo}"),
        # pg. 4
        Check(
            page=4,
            target="Prima edizione in {m.collana} {m.data_pubblicazione__B} {m.data_pubblicazione__Y}",
        ),
        Check(page=4, target="{m.autori}"),
        Check(page=4, target="{m.title}"),
        Check(page=4, target="{m.sottotitolo}"),
        Check(page=4, target="ISBN: {m.isbn}"),
        Check(page=4, target="Traduzione di {m.traduttori},"),
        # Skip Check(page=4, target="Supervisione editoriale di {m.supervisor},"),
        # Skip Check(page=4, target="Copertina di {m.nome_copertina},"),
        Check(page=4, target="Illustrazioni di {m.illustratori},"),
        Check(page=4, target="Editing di {m.curatori},"),
        Check(
            page=4,
            target="Adattamento disegni tecnici originali di {m.illustratori},",
        ),
        # Skip Check(page=4, target="Impaginazione di {m.nome_impaginatore}"),
        Check(
            page=4,
            target="Puoi trovare i nostri libri anche su www.scienzaexpress.it",
        ),
        # last page TODO: check me!!!
        Check(
            page=-1,
            target="Finito di stampare nel mese di {m.data_stampa__B} {m.data_stampa__Y}",
        ),
        Check(page=-1, target="da {m.tipografia}"),
        Check(page=-1, target="per conto di Scienza Express edizioni"),
    )

    def __call__(self):
        if obj := ValidatePdfMetadata.find_metadata_object(self.context):
            self.metadata_object = obj
            self.results = self.check_all_pdfs()
        else:
            plone.api.portal.show_message(
                message=missing_metadata_message,
                request=self.request,
                type="error",
            )
            self.results = []

        return self.index()

    @staticmethod
    def find_metadata_object(context) -> IDexterityItem | None:
        """
        Find the publication-metadata object related to this folder.

        We'll look for a Metadata object inside a folder named "XML",
        walking back from the current folder up to the site root,
        and descending into all folders.

        The first such object that we find "wins".
        """
        # TODO: should we just drop the constraint about having a container folder named "XML"?
        catalog = plone.api.portal.get_tool("portal_catalog")
        xml_folder = None
        for parent in context.aq_chain:
            if xml_folder := parent.get("XML", None):
                break
            if ISiteRoot.providedBy(parent):
                break
            path = "/".join(parent.getPhysicalPath())
            results = catalog(
                portal_type="Folder",
                id="XML",
                path={"query": path},
            )
            if results:
                xml_folder = results[0].getObject()
                break

        if not xml_folder:
            return None

        metadata_objects = xml_folder.listFolderContents(
            # NB: use the human-friendly type name (with the space in name)!
            contentFilter={"portal_type": "Metadata"},
        )
        if len(metadata_objects) > 1:
            # TODO: issue a warning!
            metadata_object = metadata_objects[0]
        elif len(metadata_objects) == 0:
            # let callee deal with this problem 😈
            return None
        else:
            metadata_object = metadata_objects[0]

        ValidatePdfMetadata._enrich_pmo(metadata_object)

        return metadata_object

    @staticmethod
    def _enrich_pmo(pmo: IDexterityItem) -> None:
        """
        Add computed attributes to the metadata object.

        For each date field, we will also attach an attribute with
        only the year and one with only the month.

        We recognize date fields because they start with "data_";
        e.g. data_pubblicazione

        Raises:
            ValueError: if a date field is not in the expected format.

        """
        for name, _ in getFieldsInOrder(IMetadata):
            if name.startswith("data_"):
                value = getattr(pmo, name)
                if not value:
                    month_l = None
                    year_l = None
                else:
                    month_l = plone.api.portal.translate(
                        value.strftime("%B"),
                        lang=plone.api.portal.get_current_language(),
                    )
                    month_l = IT_MONTHS.get(month_l, month_l)
                    year_l = value.strftime("%Y")

                setattr(pmo, f"{name}__B", month_l)
                setattr(pmo, f"{name}__Y", year_l)

    def check_all_pdfs(self) -> list[list[CheckResult]]:
        """
        Apply all checks to all PDF files in this folder.

        Returns:
        the list of list of all checks performed on all PDF files.

        """
        # see rise#16

        # TODO: refactor with pdf_prefligh.PdfPreflight
        results = []
        pdf_files = self._get_all_pdf_objects()
        for file_obj in pdf_files:
            temp_path = self._temp_copy(file_obj)
            file_results = self._process_filepath(file_obj, temp_path)
            results.append(file_results)
            temp_path.unlink()
        return results

    def _process_filepath(
        self,
        file_obj: IDexterityItem,
        temp_path: Path,
    ) -> list[CheckResult]:
        """Process one file."""
        file_results = []
        for check in self.checks:
            proc = subprocess.run(
                [
                    "pdftotext",
                    temp_path,
                    "-f",
                    str(check.page),
                    "-l",
                    str(check.page + 1),
                    "-",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            check_result = self._parse_output(file_obj, check, proc)
            file_results.append(check_result)
        return file_results

    def _parse_output(self, file_obj, check, proc) -> CheckResult:
        """
        Look for a ""check-target" in the PDF page that is provided as text.

        Returns:
            the result of the check.

        """
        stdout = proc.stdout.strip()
        # TODO: do something with the stderr?

        # Sanity check: some field of the metadata-object might be
        # empty; looking for an empty string doesn't make sense, so we
        # report the check result with a warning.
        formatter = string.Formatter()
        field_names = [_[1] for _ in formatter.parse(check.target) if _[1] is not None]

        # The precision of the python implementation of
        # the method formatter_field_name_split()
        # (Objects/stringlib/unicode_format.h l.1245) is not necessary
        # here: we can assume that our fields will always refer to the
        # metadata object via a field named "m." (as in "m.title").
        warning = ""
        for name in field_names:
            if not name.startswith("m."):
                msg = f'Badly defined check {check}. Field names should start with "m."'
                raise ValueError(msg)
            field_name = name.replace("m.", "")
            value = getattr(self.metadata_object, field_name, None)
            if not value:
                # We could have a missing field or an empty value for an existing field.
                # ATM we don't need to be aware of the difference.
                warning += f"Empty field {name}. Result is undefined."

        target = check.target.format(m=self.metadata_object)
        good = target in stdout
        if not good:
            # try harder: ignore newlines and case
            good = target.lower() in stdout.replace("\n", " ").lower()

        check_result = CheckResult(
            file_obj=file_obj,
            target=target,
            check=check,
            good=good,
            warning=warning,
        )
        return check_result

    def _get_all_pdf_objects(self) -> list[IDexterityItem]:
        """Collect all Files that have .pdf extension."""
        file_objs = []
        pdf_types = ("application/pdf",)
        for obj in self.context.listFolderContents(contentFilter={"mime_type": "application/pdf"}):
            if obj.file.contentType in pdf_types:
                file_objs.append(obj)
        return file_objs

    def _temp_copy(self, file_obj) -> Path:
        """Do a temporary copy of the file obj."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_obj.file.data)
            tmp_file.flush()
            temp_path = tmp_file.name
        return Path(temp_path)
