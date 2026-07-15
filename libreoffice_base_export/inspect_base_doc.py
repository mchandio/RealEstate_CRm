import uno
import pathlib

OUTPUT = pathlib.Path(__file__).with_name('inspect_base_doc.txt')
local_ctx = uno.getComponentContext()
resolver = local_ctx.ServiceManager.createInstanceWithContext(
    'com.sun.star.bridge.UnoUrlResolver', local_ctx)
ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
smgr = ctx.ServiceManager

desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
doc = desktop.loadComponentFromURL('private:factory/sdatabase', '_blank', 0, ())

with OUTPUT.open('w', encoding='utf-8') as out:
    out.write('doc supported services:\n')
    for s in doc.getSupportedServiceNames():
        out.write(f'  {s}\n')
    out.write('\nproperties:\n')
    try:
        psi = doc.getPropertySetInfo()
        props = psi.getProperties()
        out.write(f'prop count: {len(props)}\n')
        for p in props:
            out.write(f'  {p.Name} {p.Type}\n')
    except Exception as e:
        out.write('getPropertySetInfo failed: ' + str(e) + '\n')
    out.write('\nDataSource\n')
    try:
        ds = doc.DataSource
        out.write(f'DataSource type: {type(ds)}\n')
        out.write('DataSource supports: ' + str(ds.getSupportedServiceNames()) + '\n')
        for name in ['Name','URL','DatabaseDocument','ImplementationName','SupportedServiceNames','DataSource','Location']:
            try:
                out.write(f'  {name} = {getattr(ds, name)}\n')
            except Exception as e:
                out.write(f'  {name} err: {e}\n')
        out.write('DataSource attrs:\n')
        for n in sorted([n for n in dir(ds) if n[0].isalpha()]):
            if any(sub in n.lower() for sub in ['name','url','database','data','source','doc','property','get','set']):
                out.write(f'    {n}\n')
    except Exception as e:
        out.write('DataSource retrieval failed: ' + str(e) + '\n')
    out.write('\nscript provider support:\n')
    try:
        out.write('has ScriptProvider: ' + str(doc.supportsService('com.sun.star.script.provider.XScriptProvider')) + '\n')
    except Exception as e:
        out.write('supportsService script provider err: ' + str(e) + '\n')
    try:
        sp = doc.getScriptProvider()
        out.write('script provider object: ' + str(sp) + '\n')
    except Exception as e:
        out.write('getScriptProvider failed: ' + str(e) + '\n')
    out.write('\ndone\n')

print('wrote', OUTPUT)
