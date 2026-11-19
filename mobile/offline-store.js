/** Offline-first persistence. This is a mobile foundation, not a packaged app. */
const request = (r) => new Promise((resolve, reject) => {
  r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error);
});
const committed = (tx) => new Promise((resolve, reject) => {
  tx.oncomplete = resolve;
  tx.onabort = () => reject(tx.error || new Error('Não foi possível salvar no aparelho.'));
  tx.onerror = () => {}; // onabort reports the failed transaction exactly once.
});

export class OfflineStore {
  static async open(account, transport, database = 'coach-chess-mobile-v1') {
    if (typeof account !== 'string' || !account) throw new Error('Identifique a conta primeiro.');
    const opening = indexedDB.open(database, 1);
    opening.onupgradeneeded = () => {
      opening.result.createObjectStore('meta', {keyPath: 'key'});
      opening.result.createObjectStore('events', {keyPath: ['account', 'sequence']});
    };
    const db = await request(opening);
    const tx = db.transaction('meta', 'readwrite'), done = committed(tx);
    const meta = tx.objectStore('meta');
    let installation = await request(meta.get('installation'));
    if (!installation) {
      installation = {key: 'installation', device: crypto.randomUUID()}; meta.put(installation);
    }
    if (!await request(meta.get(account))) {
      meta.put({key: account, sequence: 0, acknowledged: 0, checkpoint: null});
    }
    await done;
    return new OfflineStore(db, account, installation.device, transport);
  }

  constructor(db, account, device, transport) {
    this.db = db; this.account = account; this.device = device; this.transport = transport;
    this.inflight = null;
    this.online = () => { this.sync().catch(() => {}); };
    globalThis.addEventListener('online', this.online);
  }

  async current() {
    return request(this.db.transaction('meta').objectStore('meta').get(this.account));
  }

  async save(checkpoint, activity = {}) {
    if (!checkpoint || typeof checkpoint !== 'object' || Array.isArray(checkpoint)) {
      throw new Error('Ponto atual inválido.');
    }
    const body = JSON.stringify({checkpoint, activity});
    if (new TextEncoder().encode(body).length > 1024 * 1024) throw new Error('Registro excede 1 MB.');
    const payload = JSON.parse(body);
    const tx = this.db.transaction(['meta', 'events'], 'readwrite'), done = committed(tx);
    const meta = tx.objectStore('meta'), previous = await request(meta.get(this.account));
    const sequence = previous.sequence + 1;
    tx.objectStore('events').add({account: this.account, id: crypto.randomUUID(), sequence, payload});
    meta.put({...previous, sequence, checkpoint: payload.checkpoint});
    await done; // Both the event and resume point are durable before returning.
    if (globalThis.navigator?.onLine !== false) this.online();
    return sequence;
  }

  async pending() {
    const range = IDBKeyRange.bound([this.account, 0], [this.account, Number.MAX_SAFE_INTEGER]);
    return request(this.db.transaction('events').objectStore('events').getAll(range, 100));
  }

  async acknowledge(sequence) {
    const tx = this.db.transaction(['meta', 'events'], 'readwrite'), done = committed(tx);
    const meta = tx.objectStore('meta'), previous = await request(meta.get(this.account));
    if (!Number.isSafeInteger(sequence) || sequence < previous.acknowledged || sequence > previous.sequence) {
      tx.abort(); await done.catch(() => {}); throw new Error('Confirmação de sincronização inválida.');
    }
    // Never replace the local checkpoint: the user may have played while uploading.
    meta.put({...previous, acknowledged: sequence});
    tx.objectStore('events').delete(IDBKeyRange.bound([this.account, 0], [this.account, sequence]));
    await done;
  }

  sync() {
    if (!this.transport) return Promise.resolve();
    if (this.inflight) return this.inflight;
    this.inflight = this.upload().finally(() => { this.inflight = null; });
    return this.inflight;
  }

  async upload() {
    for (let batch = 0; batch < 10; batch++) {
      let events = await this.pending();
      if (!events.length) return;
      let bytes = 0;
      events = events.filter((event) => {
        bytes += new TextEncoder().encode(JSON.stringify(event)).length;
        return bytes < 1800 * 1024;
      });
      // The transport must reject network failures, expired login and access blocks.
      // No local deletion is made until the server acknowledges a committed batch.
      const result = await this.transport({device: this.device,
        events: events.map(({id, sequence, payload}) => ({id, sequence, payload}))});
      // An acknowledgement cannot discard changes made after this batch was sent.
      if (result.acknowledged !== events[events.length - 1].sequence) {
        throw new Error('Confirmação não corresponde ao lote enviado; fila preservada.');
      }
      await this.acknowledge(result.acknowledged);
    }
  }

  close() {
    globalThis.removeEventListener('online', this.online); this.db.close();
  }
}

export function syncTransport(baseURL, getToken, platform, version) {
  const url = new URL(baseURL);
  if (url.username || url.password || (url.protocol !== 'https:' &&
      !(url.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(url.hostname)))) {
    throw new Error('A sincronização exige um endereço HTTPS.');
  }
  return async (batch) => {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(new URL('/v1/sync', url), {method: 'POST', signal: controller.signal,
        redirect: 'error', credentials: 'omit', cache: 'no-store',
        headers: {'Content-Type': 'application/json', Authorization: `Bearer ${await getToken()}`},
        body: JSON.stringify({...batch, platform, version})});
      if (!response.ok) throw new Error(`Sincronização não concluída (${response.status}); dados locais preservados.`);
      return await response.json();
    } finally { clearTimeout(timeout); }
  };
}
