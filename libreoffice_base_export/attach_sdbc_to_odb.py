import uno
import pathlib
import os
import time

# Connect to running LibreOffice UNO listener on localhost:2002
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

# create blank Base document
print('creating blank Base document')
doc = desktop.loadComponentFromURL('private:factory/sdatabase', '_blank', 0, ())
print('document created', type(doc))

# Attach DataSource via sdbc:odbc:crm_sqlite
try:
    ds = doc.DataSource
    print('DataSource object present:', ds)
    try:
        ds.URL = 'sdbc:odbc:crm_sqlite'
        print('Set ds.URL to', ds.URL)
    except Exception as e:
        print('Failed to set ds.URL directly:', e)
        try:
            # some implementations expose setURL
            ds.setURL('sdbc:odbc:crm_sqlite')
            print('Called setURL')
        except Exception as e2:
            print('setURL failed:', e2)
    try:
        ds.Name = 'crm_sqlite'
        print('Set ds.Name to', ds.Name)
    except Exception:
        pass
except Exception as e:
    print('No DataSource on document or attach failed:', e)

# Save to new file
odb_path = odb_dir / 'crm_base_sdbc_attached.odb'
odb_url = odb_path.as_uri()
print('saving .odb to', odb_url)
try:
    doc.storeToURL(odb_url, ())
    print('saved .odb', odb_path)
except Exception as e:
    print('store failed', e)

# close
try:
    doc.close(True)
    print('closed document')
except Exception as e:
    print('close failed', e)
