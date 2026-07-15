import uno
import os
import pathlib

local_ctx = uno.getComponentContext()
resolver = local_ctx.ServiceManager.createInstanceWithContext(
    'com.sun.star.bridge.UnoUrlResolver', local_ctx)
ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
smgr = ctx.ServiceManager

desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
print('desktop', desktop)

db_path = pathlib.Path(os.getcwd()) / 'crm_base.db'
if not db_path.exists():
    raise FileNotFoundError(f'{db_path} not found')

# Create a new empty Base database document
print('creating empty database document')
doc = desktop.loadComponentFromURL('private:factory/sdatabase', '_blank', 0, ())
print('document created:', doc)

# Attempt to set the database URL/connection path if supported
# Use script provider to access Python macros if necessary

# Determine if document supports XScriptProviderSupplier
try:
    print('supports XScriptProviderSupplier', doc.supportsService('com.sun.star.script.provider.XScriptProviderSupplier'))
except Exception as e:
    print('supportsService exception', e)

# Save the blank file first to inspect externally
odb_blank_path = pathlib.Path(os.getcwd()) / 'crm_base_attached_test.odb'
odb_blank_url = odb_blank_path.as_uri()
print('saving blank .odb to', odb_blank_url)
doc.storeToURL(odb_blank_url, ())
print('saved blank .odb')

try:
    doc.close(True)
    print('closed document')
except Exception as e:
    print('close failed', e)
