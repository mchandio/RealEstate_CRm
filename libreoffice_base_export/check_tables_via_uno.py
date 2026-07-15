import uno, pathlib
from com.sun.star.connection import NoConnectException

local_ctx = uno.getComponentContext()
resolver = local_ctx.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local_ctx)
ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
smgr = ctx.ServiceManager

desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
odb = pathlib.Path.cwd() / 'crm_base_sdbc_attached.odb'
if not odb.exists():
    print('odb not found:', odb)
    raise SystemExit(1)

url = odb.as_uri()
print('loading', url)
doc = desktop.loadComponentFromURL(url, '_blank', 0, ())
print('doc loaded')

ds = None
try:
    ds = doc.DataSource
    print('DataSource object:', ds)
    print('DataSource.URL property:', ds.URL)
except Exception as e:
    print('No DataSource?', e)

try:
    conn = ds.getConnection('', '')
    print('got connection', conn)
    meta = conn.getMetaData()
    rs = meta.getTables('', '', '%', ())
    print('tables result set object:', rs)
    count = 0
    while rs.hasMoreElements():
        t = rs.nextElement()
        try:
            print('TABLE:', t.getName(), 'TYPE:', t.getType())
        except Exception:
            print('TABLE obj', t)
        count += 1
    print('total tables:', count)
    try:
        conn.close()
    except Exception:
        pass
except Exception as e:
    print('getConnection failed:', e)

try:
    doc.close(True)
except Exception:
    pass
