from pathlib import Path
import re

# 1. Make situsnap-ui.css the LAST stylesheet in <head>, so it wins legacy inline !important rules.
p = Path("index.html")
s = p.read_text(encoding="utf-8")
s = re.sub(r'\s*<link rel="stylesheet" href="situsnap-ui\.css\?v=[^"]+">', "", s, count=1)
s = s.replace("</head>", '<link rel="stylesheet" href="situsnap-ui.css?v=108-dark-final">\n</head>', 1)
s = s.replace("serviceWorker.register('./sw.js')", "serviceWorker.register('./sw.js?v=20')")
p.write_text(s, encoding="utf-8")

# 2. Add final authoritative dark overrides.
p = Path("situsnap-ui.css")
s = p.read_text(encoding="utf-8")
marker = "/* V1.0.8 FINAL DARK AUTHORITY"
if marker not in s:
    s += '''
/* V1.0.8 FINAL DARK AUTHORITY - deliberately last in cascade. */
html body{background:linear-gradient(180deg,#041b25,#031923)!important;color:#f7fbff!important}
body .ss-home-shell,body .ss-find-card{background:linear-gradient(145deg,#0b2a38,#082433)!important;color:#fff!important}
body .ss-find-card{background:transparent!important}
body .ss-find-card input#huntPostcode,body .ss-find-card input#doorNumber,body .ss-find-card input#manualAddress{background:#0a2438!important;background-color:#0a2438!important;color:#fff!important;-webkit-text-fill-color:#fff!important;border-color:#6f8ba0!important;color-scheme:dark!important}
body .ss-find-card input::placeholder{color:#aebdca!important;-webkit-text-fill-color:#aebdca!important}
body #verifiedFirstPanel{background:#0a3028!important;background-color:#0a3028!important;border-color:#287b59!important;color:#fff!important}
body #verifiedFirstPanel>div:first-child{color:#31df68!important}
body #ssFindResult{background:#0a3028!important;background-color:#0a3028!important;border-color:#287b59!important;color:#fff!important}
body #ssFindResultKicker{color:#31df68!important}
body #ssNavigateBtn{background:#00a75e!important;color:#fff!important}
body #recordsCard,body #recordsCard .record{color:#fff!important}
'''
p.write_text(s, encoding="utf-8")

# 3. Refresh service worker cache and make HTML/CSS network-first.
Path("sw.js").write_text('''const CACHE='situsnap-shell-v20';
const SHELL=['./','./index.html','./manifest.webmanifest','./situsnap-background.png','./situsnap-ui.css'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET') return;
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin) return;
  if(event.request.mode==='navigate'||url.pathname.endsWith('/situsnap-ui.css')){
    event.respondWith(fetch(event.request).then(r=>{
      if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(event.request,copy));}
      return r;
    }).catch(()=>caches.match(event.request).then(x=>x||caches.match('./index.html'))));
    return;
  }
  event.respondWith(caches.match(event.request).then(hit=>hit||fetch(event.request).then(r=>{
    if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(event.request,copy));}
    return r;
  })));
});''', encoding="utf-8")

print("SituSnap surgery complete: final CSS authority + cache v20.")
