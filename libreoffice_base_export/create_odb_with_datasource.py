import uno
import os
import pathlib

# This script tries to create a Base .odb and use a DataSource object to register the SQLite DB.
# It may or may not work depending on the available UNO services in LibreOffice.

local_ctx = uno.getComponentContext()
resolver = local_ctx.ServiceManager.createInstanceWithContext(
    'com.sun.star.bridge.UnoUrlResolver', local_ctx)
ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
smgr = ctx.ServiceManager

desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
print('desktop', desktop)

odb_dir = pathlib.Path(os.getcwd())
db_path = odb_dir / 'crm_base.db'
if not db_path.exists():
    raise FileNotFoundError(db_path)

# create a blank database document
print('creating blank Base document')
doc = desktop.loadComponentFromURL('private:factory/sdatabase', '_blank', 0, ())
print('doc', doc)
print('DataSource available?', hasattr(doc, 'DataSource'))

# Try to create a data source from the ServiceManager if available
try:
    ds = smgr.createInstanceWithContext('com.sun.star.sdb.DataSource', ctx)
    print('created DataSource', ds)
    print('datasource methods:', [m for m in dir(ds) if 'name' in m.lower() or 'url' in m.lower() or 'data' in m.lower() or 'driver' in m.lower()])
except Exception as e:
    print('DataSource creation failed', e)

# Save the blank document to inspect
odb_path = odb_dir / 'crm_base_datasource.odb'
odb_url = odb_path.as_uri()
print('saving blank .odb to', odb_url)
try:
    doc.storeToURL(odb_url, ())
    print('saved .odb', odb_path)
except Exception as e:
    print('store failed', e)

try:
    doc.close(True)
    print('closed document')
except Exception as e:
    print('close failed', e)
