import uno
import pathlib
import os

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

# Create a blank Base document
print('creating blank Base document')
doc = desktop.loadComponentFromURL('private:factory/sdatabase', '_blank', 0, ())
print('document created', doc)

# Access DataSource and configure URL for SQLite
try:
    ds = doc.DataSource
    print('DataSource object', ds)
    print('current URL:', ds.URL)
    ds.URL = 'jdbc:sqlite:' + str(db_path)
    print('new URL:', ds.URL)
    ds.Name = 'crm_base_sqlite'
    print('new Name:', ds.Name)
except Exception as e:
    print('DataSource configuration failed:', e)

# Save .odb
odb_path = pathlib.Path(os.getcwd()) / 'crm_base_bound.odb'
odb_url = odb_path.as_uri()
print('saving .odb to', odb_url)
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
