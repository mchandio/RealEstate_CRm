# UNO macro to attempt automatic form creation inside a LibreOffice Base document.
# Run this macro from Tools -> Macros -> Organize Macros -> Python while the .odb is open.
# It attempts to create simple forms for a small set of tables and attach validation macros.

__all__ = ["create_basic_forms"]

try:
    from com.sun.star.beans import PropertyValue
    from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK
    from com.sun.star.awt.MessageBoxType import MESSAGEBOX
    XSCRIPTCONTEXT
except Exception:
    XSCRIPTCONTEXT = None


def _msgbox(parent, message, title="generate_forms"):
    try:
        toolkit = parent.getToolkit()
        window = parent
        box = toolkit.createMessageBox(window, MESSAGEBOX, BUTTONS_OK, title, str(message))
        box.execute()
    except Exception:
        print(title + ": " + str(message))


def create_basic_forms():
    """Attempt to create simple forms for core tables.

    This function is best-effort: UNO APIs differ across versions and creating complex
    form controls programmatically can require adjustments. If automatic creation fails,
    follow manual instructions in README and forms_plan.md.
    """
    if XSCRIPTCONTEXT is None:
        print("This macro must be run inside LibreOffice (Tools → Macros → Python).")
        return

    doc = XSCRIPTCONTEXT.getDocument()
    try:
        # Database document exposes FormDocuments container in many LibreOffice versions
        form_docs = getattr(doc, 'FormDocuments', None)
        if form_docs is None:
            _msgbox(doc.CurrentController.Frame.getContainerWindow(),
                    "Could not find FormDocuments container on this document. Make sure you've connected to the SQLite DB and opened the .odb.")
            return

        tables_to_create = [
            ('rent_requirements', 'RentRequirementsForm'),
            ('rent_availability', 'RentAvailabilityForm'),
            ('sale_requirements', 'SaleRequirementsForm'),
            ('sale_availability', 'SaleAvailabilityForm'),
            ('broker_contacts', 'BrokerContactsForm'),
            ('properties', 'PropertiesForm'),
        ]

        for table_name, form_name in tables_to_create:
            try:
                # If a form with this name already exists, skip
                if form_name in form_docs.getElementNames():
                    print('Form', form_name, 'already exists — skipping')
                    continue
                # create new empty form document bound to table
                form_doc = form_docs.createInstanceByName(form_name)
                # Some versions require creating by service; try to set the DataSourceName/TableName properties
                try:
                    design = form_doc.getForms()[0]
                except Exception:
                    design = None
                # Attempt to set a registered data table for the form if possible
                try:
                    # Many Base APIs allow setting the Command (SQL) or TableName on the form's data source
                    if hasattr(form_doc, 'setDataSourceName'):
                        form_doc.setDataSourceName(table_name)
                except Exception:
                    pass

                print('Created form', form_name, 'for table', table_name)
            except Exception as e:
                print('Failed to create form for', table_name, ':', e)

        _msgbox(doc.CurrentController.Frame.getContainerWindow(), 'Form creation attempt finished. Review forms and attach controls manually as needed.')
    except Exception as e:
        _msgbox(doc.CurrentController.Frame.getContainerWindow(), 'Error while creating forms: ' + str(e))
        raise


def create_and_save_odb(target_path=None):
    """Create forms and save the current Base document as a .odb file at target_path.

    If run as a macro inside an open Base document that is connected to a SQLite DB,
    this will attempt to create forms (call `create_basic_forms`) and then save the
    document to `target_path` (default: ./crm_base.odb in the export folder).
    """
    if XSCRIPTCONTEXT is None:
        print("This macro must be run inside LibreOffice (Tools → Macros → Python).")
        return
    doc = XSCRIPTCONTEXT.getDocument()
    # attempt to create forms first
    try:
        create_basic_forms()
    except Exception as e:
        print('Warning: form creation failed:', e)

    # Determine default target path
    if not target_path:
        import os
        target_path = os.path.join(os.path.dirname(__file__), '..', 'crm_base.odb')
        target_path = os.path.abspath(target_path)

    # Convert to file URL
    from urllib.parse import quote
    file_url = 'file://' + quote(target_path)
    try:
        # storeToURL may be available on the document
        if hasattr(doc, 'storeToURL'):
            props = ()
            doc.storeToURL(file_url, props)
            print('Saved .odb to', target_path)
        else:
            # Fallback: try to use current component window to save
            print('Document does not support storeToURL; saving may not be supported programmatically here.')
    except Exception as e:
        print('Failed to save .odb:', e)


def xs_create_and_save_odb(event=None):
    # XSCRIPT wrapper for UI invocation
    create_and_save_odb()
