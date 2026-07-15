import uno
import pathlib

from pathlib import Path

OUTPUT = Path(__file__).with_name('doc_methods.txt')

local_ctx = uno.getComponentContext()
resolver = local_ctx.ServiceManager.createInstanceWithContext(
    'com.sun.star.bridge.UnoUrlResolver', local_ctx)
ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
smgr = ctx.ServiceManager

desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
doc = desktop.loadComponentFromURL('private:factory/sdatabase', '_blank', 0, ())

with OUTPUT.open('w', encoding='utf-8') as out:
    out.write('supported_services:\n')
    for s in doc.getSupportedServiceNames():
        out.write(f'  {s}\n')
    out.write('\nmethods:\n')
    names = sorted(set(name for name in dir(doc) if any(sub in name.lower() for sub in ['data','source','db','database','location','url','store','load','script','form','document','connection','context','control','provider','registry'])))
    for name in names:
        out.write(name + '\n')
    out.write('\nall methods count: ' + str(len(names)) + '\n')

print('wrote', OUTPUT)
