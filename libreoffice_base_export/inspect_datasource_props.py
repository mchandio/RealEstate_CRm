import uno
import pathlib

OUTPUT = pathlib.Path(__file__).with_name('inspect_datasource_props.txt')
local_ctx = uno.getComponentContext()
resolver = local_ctx.ServiceManager.createInstanceWithContext(
    'com.sun.star.bridge.UnoUrlResolver', local_ctx)
ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
smgr = ctx.ServiceManager

desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
doc = desktop.loadComponentFromURL('private:factory/sdatabase', '_blank', 0, ())
ds = doc.DataSource
with OUTPUT.open('w', encoding='utf-8') as out:
    out.write('DataSource supported services:\n')
    out.write(str(ds.getSupportedServiceNames()) + '\n')
    out.write('DataSource implementation\n')
    try:
        out.write('  ImplementationName=' + ds.ImplementationName + '\n')
    except Exception as e:
        out.write('  ImplementationName err ' + str(e) + '\n')
    out.write('PropertySetInfo\n')
    try:
        psi = ds.getPropertySetInfo()
        props = psi.getProperties()
        out.write('property count ' + str(len(props)) + '\n')
        for p in props:
            out.write(f'  {p.Name} {p.Type}\n')
    except Exception as e:
        out.write('getPropertySetInfo err ' + str(e) + '\n')
    out.write('Current property values\n')
    try:
        names = [p.Name for p in psi.getProperties()]
        for n in names:
            try:
                out.write(f'  {n} = {ds.getPropertyValue(n)}\n')
            except Exception as e:
                out.write(f'  {n} get err {e}\n')
    except Exception as e:
        out.write('property values err ' + str(e) + '\n')
print('wrote', OUTPUT)
