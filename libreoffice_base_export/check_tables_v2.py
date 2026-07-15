import uno, pathlib

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

ds = doc.DataSource
print('DataSource.URL property:', ds.URL)

try:
    conn = ds.getConnection('', '')
    print('got connection', conn)
    meta = conn.getMetaData()
    rs = meta.getTables('', '', '%', ('TABLE',))
    md = rs.getMetaData()
    cols = md.getColumnCount()
    colnames = []
    for i in range(1, cols+1):
        try:
            colnames.append(md.getColumnName(i))
        except Exception:
            colnames.append(f'col{i}')
    print('columns:', colnames)
    tables = []
    while rs.next():
        row = []
        for i in range(1, cols+1):
            try:
                row.append(rs.getString(i))
            except Exception:
                try:
                    row.append(str(rs.getObject(i)))
                except Exception:
                    row.append(None)
        tables.append(row)
    print('found', len(tables), 'rows')
    for r in tables[:50]:
        print(r)
    try:
        conn.close()
    except Exception:
        pass
except Exception as e:
    print('connection/tables failed:', e)

try:
    doc.close(True)
except Exception:
    pass
