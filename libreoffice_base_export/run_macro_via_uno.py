"""Connect to a running LibreOffice instance via UNO and invoke the user macro
`generate_forms.create_and_save_odb`.

Usage: python3 run_macro_via_uno.py

This script assumes LibreOffice is started with an UNO listener on port 2002.
"""
import time
import sys

try:
    import uno
except Exception as e:
    print('python-uno is required to run this script (package: libreoffice-python or python-uno).', e)
    sys.exit(2)

from unohelper import Base

# Resolve a UNO context via the socket listener
local_ctx = uno.getComponentContext()
resolver = local_ctx.ServiceManager.createInstanceWithContext(
    "com.sun.star.bridge.UnoUrlResolver", local_ctx)

try:
    ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
except Exception as e:
    print('Could not connect to LibreOffice UNO listener on port 2002:', e)
    sys.exit(3)

smgr = ctx.ServiceManager
try:
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
except Exception as e:
    print('Failed to create Desktop:', e)
    sys.exit(4)

# Give LibreOffice a moment to open the DB document if still loading
time.sleep(1)

doc = None
try:
    doc = desktop.getCurrentComponent()
except Exception:
    doc = None

if not doc:
    print('No current document detected. Ensure the DB (.odb) window is open in LibreOffice.')
    # continue: try to invoke script via master script provider
    # Attempt to explicitly load the database document from the export folder
    try:
        import os
        db_path = os.path.abspath('crm_base.db')
        file_url = 'file://' + db_path
        # load the document as a database document
        load_props = ()
        doc = desktop.loadComponentFromURL(file_url, '_blank', 0, load_props)
        print('Loaded document from', db_path)
    except Exception as e:
        print('Could not load document:', e)

try:
    # Try to invoke the macro through the document script provider if available
    if doc is not None and hasattr(doc, 'getScriptProvider'):
        provider = doc.getScriptProvider()
        script = provider.getScript('vnd.sun.star.script:generate_forms.create_and_save_odb?language=Python&location=user')
        script.invoke((), (), ())
        print('Invoked script via document script provider')
    else:
        # fallback: use master script provider factory
        factory = smgr.createInstanceWithContext('com.sun.star.script.provider.MasterScriptProviderFactory', ctx)
        mprovider = factory.createScriptProvider('')
        script = mprovider.getScript('vnd.sun.star.script:generate_forms.create_and_save_odb?language=Python&location=user')
        script.invoke((), (), ())
        print('Invoked script via master script provider')
except Exception as e:
    print('Failed to invoke macro:', e)
    sys.exit(5)

print('Macro invocation complete')
