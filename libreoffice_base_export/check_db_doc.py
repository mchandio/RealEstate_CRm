import uno
import sys

local_ctx = uno.getComponentContext()
resolver = local_ctx.ServiceManager.createInstanceWithContext(
    'com.sun.star.bridge.UnoUrlResolver', local_ctx)
try:
    ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
except Exception as e:
    print('resolve error', e)
    sys.exit(1)
smgr = ctx.ServiceManager
try:
    desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
except Exception as e:
    print('desktop error', e)
    sys.exit(2)
print('desktop loaded')
try:
    doc = desktop.loadComponentFromURL('private:factory/sdatabase', '_blank', 0, ())
    print('doc loaded', doc)
except Exception as e:
    print('load doc error', e)
    sys.exit(3)
print('supported services:')
for s in doc.getSupportedServiceNames():
    print('  service:', s)
print('interfaces:')
# print first 200 attr names
attrs = [a for a in dir(doc) if a[0].islower()][:200]
print(attrs)
print('has storeToURL', hasattr(doc, 'storeToURL'))
try:
    print('URL property', doc.URL)
except Exception as e:
    print('URL error', e)
try:
    print('Title property', doc.Title)
except Exception as e:
    print('Title error', e)
try:
    print('Supports XStorable?', doc.supportsService('com.sun.star.frame.XStorable'))
except Exception as e:
    print('supportsService error', e)
try:
    sp = doc.getScriptProvider()
    print('scriptProvider', sp)
except Exception as e:
    print('scriptProvider error', e)
print('done')
