/**
 * Real Estate CRM - Service Worker
 * =================================
 * Provides offline support, caching, and PWA functionality.
 * 
 * Features:
 * - Cache-first strategy for static assets
 * - Network-first strategy for API calls
 * - Offline fallback page
 * - Background sync for pending operations
 */

const CACHE_NAME = 'crm-v1.0.0';
const STATIC_CACHE = 'crm-static-v1.0.0';
const API_CACHE = 'crm-api-v1.0.0';

// Static assets to pre-cache
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

// API endpoints that should use network-first strategy
const API_PATHS = ['/api/'];

// Install event - pre-cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Pre-caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== STATIC_CACHE && name !== API_CACHE)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // API requests: network-first strategy
  if (API_PATHS.some(path => url.pathname.startsWith(path))) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets: cache-first strategy
  event.respondWith(cacheFirst(request));
});

// Cache-first strategy (for static assets)
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] Fetch failed:', error);
    return caches.match('/index.html');
  }
}

// Network-first strategy (for API calls)
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] Network failed, trying cache:', error);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    // Return offline response for API calls
    return new Response(
      JSON.stringify({ error: 'Offline', message: 'No network connection' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Background sync for pending operations
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-pending-changes') {
    console.log('[SW] Syncing pending changes...');
    event.waitUntil(syncPendingChanges());
  }
});

async function syncPendingChanges() {
  // Get pending changes from IndexedDB
  const pendingChanges = await getPendingChanges();
  for (const change of pendingChanges) {
    try {
      await fetch(change.url, {
        method: change.method,
        headers: change.headers,
        body: change.body
      });
      await removePendingChange(change.id);
    } catch (error) {
      console.error('[SW] Sync failed for change:', change.id, error);
    }
  }
}

// Placeholder functions for IndexedDB operations
async function getPendingChanges() {
  return [];
}

async function removePendingChange(id) {
  // Implementation would use IndexedDB
}

// Push notification handling
self.addEventListener('push', (event) => {
  if (!event.data) {
    return;
  }

  const data = event.data.json();
  const options = {
    body: data.body || 'New notification',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: data.primaryKey || 1,
      url: data.url || '/'
    },
    actions: [
      { action: 'open', title: 'Open', icon: '/icons/icon-96x96.png' },
      { action: 'close', title: 'Close', icon: '/icons/icon-96x96.png' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'Real Estate CRM', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  const action = event.action;
  const notification = event.notification;

  if (action === 'close') {
    notification.close();
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window' })
      .then((clientList) => {
        for (const client of clientList) {
          if (client.url.includes('/') && 'focus' in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(notification.data?.url || '/');
        }
      })
  );
});
