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

# create a new empty Base document
print('creating empty database document')
doc = desktop.loadComponentFromURL('private:factory/sdatabase', '_blank', 0, ())
print('document created:', doc)

# set the connection to the existing sqlite file via a new data source binder if possible
# The Base document itself is an OfficeDatabaseDocument and should support XStorable
print('supports XStorable', doc.supportsService('com.sun.star.frame.XStorable'))
print('has storeToURL', hasattr(doc, 'storeToURL'))

# Save as .odb first so we can inspect the document content.
odb_path = pathlib.Path(os.getcwd()) / 'crm_base_saved.odb'
odb_url = odb_path.as_uri()
print('saving .odb to', odb_url)
doc.storeToURL(odb_url, ())
print('saved .odb')

# Optionally close doc
try:
    doc.close(True)
    print('closed document')
except Exception as e:
    print('close failed', e)
